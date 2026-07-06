"""
洛谷平台探索脚本（最终版）
验证题面和题解的获取方式

运行方式: uv run python explore_luogu.py
- 题面获取无需登录，headless 模式自动完成
- 题解获取需要登录，首次运行会打开浏览器等待用户登录，cookie 持久化后后续自动
"""

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent / "data" / "luogu_profile"
DATA_DIR.mkdir(parents=True, exist_ok=True)


async def extract_page_json(page, template: str):
    """从页面嵌入的 <script type='application/json'> 标签提取匹配 template 的数据"""
    return await page.evaluate(f"""
        () => {{
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {{
                try {{
                    const d = JSON.parse(s.textContent);
                    if (d.template === '{template}') return d;
                }} catch(e) {{}}
            }}
            return null;
        }}
    """)


async def ensure_login(context, page) -> bool:
    """确保已登录，未登录则打开浏览器等待用户操作"""
    await page.goto("https://www.luogu.com.cn", timeout=15000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(2)

    login_link = await page.query_selector('a[href="/auth/login"]')
    if not login_link:
        print("✓ 已登录洛谷")
        return True

    print("⚠️  未登录，请在浏览器中完成洛谷登录（扫码/账密）")
    await page.goto("https://www.luogu.com.cn/auth/login")
    print("   等待登录完成（最多 5 分钟）...")
    sys.stdout.flush()

    for i in range(150):
        await asyncio.sleep(2)
        try:
            if "/auth/login" not in page.url and "luogu" in page.url:
                print("✓ 登录成功！")
                return True
        except Exception:
            pass
        if i % 15 == 14:
            print(f"   ⏳ 等待中... ({(i+1)*2}s)")
            sys.stdout.flush()

    # 最后检查
    await page.goto("https://www.luogu.com.cn")
    await page.wait_for_load_state("domcontentloaded")
    login_link = await page.query_selector('a[href="/auth/login"]')
    if login_link:
        print("✗ 登录超时")
        return False
    print("✓ 登录成功！")
    return True


async def explore_statement(page, pid: str):
    """探索题面获取（无需登录）"""
    print(f"\n  [{pid}] ", end="")
    sys.stdout.flush()

    await page.goto(f"https://www.luogu.com.cn/problem/{pid}", timeout=30000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(2)

    data = await extract_page_json(page, "problem.show")
    if not data or data.get("status") != 200:
        print(f"✗ 失败")
        return None

    problem = data["data"]["problem"]
    content = problem["content"]
    samples = problem.get("samples", [])
    limits = problem.get("limits", {})

    print(f"✓ {content['name']}")
    print(f"        desc={len(content.get('description',''))}字符 "
          f"samples={len(samples)}组 "
          f"time={limits.get('time',[0])[0]}ms "
          f"mem={limits.get('memory',[0])[0]//1024}MB")
    return problem


async def explore_solution(page, pid: str):
    """探索题解获取（需要登录）"""
    print(f"\n  [{pid}] ", end="")
    sys.stdout.flush()

    await page.goto(
        f"https://www.luogu.com.cn/problem/solution/{pid}",
        wait_until="domcontentloaded",
        timeout=30000,
    )
    await asyncio.sleep(3)

    data = await extract_page_json(page, "problem.solution")
    if not data:
        print("✗ 未找到题解数据")
        return None

    solutions = data["data"]["solutions"]
    results = solutions.get("result", [])
    count = solutions.get("count", 0)

    if not results:
        print(f"✗ 无题解 (总数={count})")
        return None

    first = results[0]
    print(f"✓ {count} 条题解, 最高赞={first.get('upvote',0)}")
    print(f"        content={len(first.get('content',''))}字符 "
          f"author={first.get('author',{}).get('name','?')}")

    # 打印题解开头
    content = first.get("content", "")
    if content:
        preview = content[:200].replace('\n', ' ')
        print(f"        预览: {preview}...")

    return results


async def main():
    print("洛谷平台探索脚本")
    print("=" * 60)

    async with async_playwright() as p:
        # Phase 1: 题面（headless，无需登录）
        print("\n[Phase 1] 题面获取 (headless, 无需登录)")
        print("-" * 40)

        context = await p.chromium.launch_persistent_context(
            str(DATA_DIR),
            headless=True,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        page = context.pages[0] if context.pages else await context.new_page()

        for pid in ["P3413", "P4124", "P8820"]:
            await explore_statement(page, pid)

        await context.close()

        # Phase 2: 题解（headed，需要登录）
        print("\n\n[Phase 2] 题解获取 (headed, 需登录)")
        print("-" * 40)

        context = await p.chromium.launch_persistent_context(
            str(DATA_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        page = context.pages[0] if context.pages else await context.new_page()

        logged_in = await ensure_login(context, page)
        if logged_in:
            for pid in ["P3413", "P4124"]:
                await explore_solution(page, pid)

        await context.close()

    print(f"\n\n{'='*60}")
    print("探索完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
