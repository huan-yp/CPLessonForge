"""Problem fetcher CLI.

Usage:
    uv run python fetch.py P3413                        # Single problem
    uv run python fetch.py P3413 --editorial            # With editorial
    uv run python fetch.py P3413 P4124 --editorial      # Multiple problems
    uv run python fetch.py --output-dir ../动态规划/problems P3413 P4124
    uv run python fetch.py login luogu                  # Login to platform
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from lib.browser import StealthBrowser, NormalBrowser, LuoguBrowser, wait_for_cloudflare
from lib.platforms import luogu, atcoder, codeforces, qoj

DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "problems"

MAX_RETRIES = 2
RETRY_DELAY = 5


def is_interactive() -> bool:
    """Check if stdin is available for interactive input."""
    try:
        return os.isatty(sys.stdin.fileno())
    except (AttributeError, ValueError, OSError):
        return False


def detect_platform(problem_id: str) -> str:
    pid = problem_id.upper()
    if re.match(r"^[PB]\d+$", pid):
        return "luogu"
    if re.match(r"^(ABC|ARC|AGC)", pid):
        return "atcoder"
    if pid.startswith("CF"):
        return "codeforces"
    if pid.startswith("QOJ"):
        return "qoj"
    raise ValueError(f"Unknown platform for problem ID: {problem_id}")


async def do_login(platform: str):
    """Open browser for manual login."""
    if platform == "luogu":
        async with LuoguBrowser() as browser:
            ctx = await browser.get_context(headed=True)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.goto("https://www.luogu.com.cn/auth/login")
            print("请在浏览器中完成登录，完成后按 Enter...")
            input()
            print("✓ 登录状态已保存")
    elif platform in ("codeforces", "cf"):
        async with StealthBrowser("cf_profile") as browser:
            page = browser.page or await browser.new_page()
            await page.goto("https://codeforces.com")
            print("请等待 Cloudflare 通过（或手动完成验证），完成后按 Enter...")
            input()
            print("✓ Session 已保存")
    elif platform in ("qoj",):
        async with StealthBrowser("qoj_profile") as browser:
            page = browser.page or await browser.new_page()
            await page.goto("https://qoj.ac")
            print("请等待 Cloudflare 通过（或手动完成验证），完成后按 Enter...")
            input()
            print("✓ Session 已保存")
    else:
        print(f"Unknown platform: {platform}")


async def fetch_luogu_batch(problem_ids: list[str], output_dir: Path, with_editorial: bool):
    """Fetch multiple Luogu problems in one browser session."""
    async with LuoguBrowser() as browser:
        ctx = await browser.get_context(headed=False)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        skip_editorial = False
        if with_editorial:
            logged_in = await luogu.check_login(page)
            if not logged_in:
                if is_interactive():
                    print("  ⚠️  题解需要登录，切换到 headed 模式...")
                    ctx = await browser.get_context(headed=True)
                    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                    await page.goto("https://www.luogu.com.cn/auth/login")
                    print("  请在浏览器中完成登录，完成后按 Enter...")
                    input()
                else:
                    print("  ⚠️  题解需要登录但当前非交互模式，跳过题解获取")
                    print("     请先运行: uv run python fetch.py login luogu")
                    skip_editorial = True

        for pid in problem_ids:
            out_dir = output_dir / pid.upper()
            out_dir.mkdir(parents=True, exist_ok=True)
            try:
                statement = await luogu.fetch_statement(page, pid.upper())
                (out_dir / "statement.md").write_text(statement, encoding="utf-8")
                print(f"  ✓ {pid} statement.md")

                if with_editorial and not skip_editorial:
                    editorial = await luogu.fetch_editorial(page, pid.upper())
                    if editorial:
                        (out_dir / "editorial.md").write_text(editorial, encoding="utf-8")
                        print(f"  ✓ {pid} editorial.md")
                    else:
                        print(f"  - {pid} 无题解")
            except Exception as e:
                print(f"  ✗ {pid} 失败: {e}")


async def fetch_atcoder_batch(problem_ids: list[str], output_dir: Path, with_editorial: bool):
    """Fetch multiple AtCoder problems in one browser session."""
    async with NormalBrowser() as browser:
        page = await browser.new_page()

        for pid in problem_ids:
            out_dir = output_dir / pid.upper()
            out_dir.mkdir(parents=True, exist_ok=True)
            try:
                statement = await atcoder.fetch_statement(page, pid)
                (out_dir / "statement.md").write_text(statement, encoding="utf-8")
                print(f"  ✓ {pid} statement.md")

                if with_editorial:
                    editorial = await atcoder.fetch_editorial(page, pid)
                    if editorial:
                        (out_dir / "editorial.md").write_text(editorial, encoding="utf-8")
                        print(f"  ✓ {pid} editorial.md")
                    else:
                        print(f"  - {pid} 无 Editorial")
            except Exception as e:
                print(f"  ✗ {pid} 失败: {e}")


async def fetch_codeforces_batch(problem_ids: list[str], output_dir: Path, with_editorial: bool):
    """Fetch multiple Codeforces problems in one browser session."""
    async with StealthBrowser("cf_profile") as browser:
        page = browser.page or await browser.new_page()

        for pid in problem_ids:
            out_dir = output_dir / pid.upper()
            out_dir.mkdir(parents=True, exist_ok=True)

            for attempt in range(MAX_RETRIES):
                try:
                    statement = await codeforces.fetch_statement(page, pid)
                    (out_dir / "statement.md").write_text(statement, encoding="utf-8")
                    print(f"  ✓ {pid} statement.md")

                    if with_editorial:
                        editorial = await codeforces.fetch_editorial(page, pid)
                        if editorial:
                            (out_dir / "editorial.md").write_text(editorial, encoding="utf-8")
                            print(f"  ✓ {pid} editorial.md")
                        else:
                            print(f"  - {pid} 无 Editorial")
                    await asyncio.sleep(3)
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        print(f"  ⚠ {pid} 第 {attempt+1} 次失败，{RETRY_DELAY}s 后重试: {e}")
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        print(f"  ✗ {pid} 失败: {e}")


async def fetch_qoj_batch(problem_ids: list[str], output_dir: Path, with_editorial: bool):
    """Fetch multiple QOJ problems in one browser session."""
    async with StealthBrowser("qoj_profile") as browser:
        page = browser.page or await browser.new_page()

        for pid in problem_ids:
            out_dir = output_dir / pid.upper()
            out_dir.mkdir(parents=True, exist_ok=True)

            for attempt in range(MAX_RETRIES):
                try:
                    statement = await qoj.fetch_statement(page, pid, output_dir=out_dir)
                    (out_dir / "statement.md").write_text(statement, encoding="utf-8")
                    print(f"  ✓ {pid} statement.md")
                    await asyncio.sleep(3)
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        print(f"  ⚠ {pid} 第 {attempt+1} 次失败，{RETRY_DELAY}s 后重试: {e}")
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        print(f"  ✗ {pid} 失败: {e}")


async def fetch_batch(problem_ids: list[str], output_dir: Path, with_editorial: bool):
    """Fetch problems grouped by platform for efficiency."""
    groups: dict[str, list[str]] = {}
    for pid in problem_ids:
        platform = detect_platform(pid)
        groups.setdefault(platform, []).append(pid)

    for platform, pids in groups.items():
        print(f"\n[{platform}] {len(pids)} 题: {', '.join(pids)}")
        if platform == "luogu":
            await fetch_luogu_batch(pids, output_dir, with_editorial)
        elif platform == "atcoder":
            await fetch_atcoder_batch(pids, output_dir, with_editorial)
        elif platform == "codeforces":
            await fetch_codeforces_batch(pids, output_dir, with_editorial)
        elif platform == "qoj":
            await fetch_qoj_batch(pids, output_dir, with_editorial)


def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(1)

    if args[0] == "login":
        if len(args) < 2:
            print("Usage: fetch.py login <platform>")
            sys.exit(1)
        asyncio.run(do_login(args[1]))
        return

    # Parse flags
    with_editorial = "--editorial" in args
    args = [a for a in args if a != "--editorial"]

    output_dir = DEFAULT_OUTPUT_DIR
    if "--output-dir" in args:
        idx = args.index("--output-dir")
        output_dir = Path(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    problem_ids = args
    if not problem_ids:
        print("No problem IDs specified")
        sys.exit(1)

    asyncio.run(fetch_batch(problem_ids, output_dir, with_editorial))


if __name__ == "__main__":
    main()
