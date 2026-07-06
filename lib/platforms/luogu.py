"""Luogu (洛谷) problem fetcher.

Statement: extracted from embedded JSON in <script type="application/json"> (no login needed)
Editorial: from solution page embedded JSON (login needed)
"""

import asyncio
from playwright.async_api import Page


async def fetch_statement(page: Page, pid: str) -> str:
    """Fetch problem statement as Markdown. No login required."""
    await page.goto(f"https://www.luogu.com.cn/problem/{pid}", timeout=30000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(2)

    data = await page.evaluate("""
        () => {
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {
                try {
                    const d = JSON.parse(s.textContent);
                    if (d.template === 'problem.show') return d;
                } catch(e) {}
            }
            return null;
        }
    """)

    if not data:
        raise RuntimeError(f"Failed to extract problem data for {pid}")

    problem = data["data"]["problem"]
    content = problem["content"]

    time_limit = problem["limits"]["time"][0]
    memory_limit = problem["limits"]["memory"][0] // 1024

    parts = []
    parts.append(f"# {pid} - {content['name']}")
    parts.append(f"\n时间限制：{time_limit}ms | 内存限制：{memory_limit}MB\n")

    if content.get("background"):
        parts.append("## 题目背景\n")
        parts.append(content["background"])

    parts.append("\n## 题目描述\n")
    parts.append(content["description"])

    parts.append("\n## 输入格式\n")
    parts.append(content["formatI"])

    parts.append("\n## 输出格式\n")
    parts.append(content["formatO"])

    if problem.get("samples"):
        parts.append("\n## 样例\n")
        for i, (inp, out) in enumerate(problem["samples"], 1):
            parts.append(f"### 样例输入 {i}\n")
            parts.append(f"```\n{inp}\n```\n")
            parts.append(f"### 样例输出 {i}\n")
            parts.append(f"```\n{out}\n```\n")

    if content.get("hint"):
        parts.append("\n## 说明/提示\n")
        parts.append(content["hint"])

    return "\n".join(parts)


async def fetch_editorial(page: Page, pid: str) -> str | None:
    """Fetch top-voted editorial. Requires login (persistent context)."""
    await page.goto(
        f"https://www.luogu.com.cn/problem/solution/{pid}",
        wait_until="domcontentloaded",
    )
    await asyncio.sleep(3)

    data = await page.evaluate("""
        () => {
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {
                try {
                    const d = JSON.parse(s.textContent);
                    if (d.template === 'problem.solution') return d;
                } catch(e) {}
            }
            return null;
        }
    """)

    if not data:
        return None

    solutions = data["data"]["solutions"]["result"]
    if not solutions:
        return None

    sol = solutions[0]
    header = f"# {pid} 题解\n\n"
    header += f"作者：{sol['author']['name']} | 点赞：{sol.get('upvote', 0)}\n\n---\n\n"
    return header + sol["content"]


async def check_login(page: Page) -> bool:
    """Check if currently logged in to Luogu."""
    await page.goto("https://www.luogu.com.cn", timeout=15000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(2)
    logged_in = await page.evaluate("""
        () => {
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {
                try {
                    const d = JSON.parse(s.textContent);
                    if (d.currentUser && d.currentUser.uid) return true;
                } catch(e) {}
            }
            return false;
        }
    """)
    return logged_in
