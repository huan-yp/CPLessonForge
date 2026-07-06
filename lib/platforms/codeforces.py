"""Codeforces problem fetcher.

Statement: DOM extraction with MathJax formula recovery from <script type="math/tex">
Editorial: blog post extraction from .ttypography
Requires stealth browser to bypass Cloudflare.
"""

import asyncio
import re
from playwright.async_api import Page

from ..browser import wait_for_cloudflare


def _parse_problem_id(problem_id: str) -> tuple[str, str]:
    """Parse 'CF1542E1' -> ('1542', 'E1')"""
    m = re.match(r"cf(\d+)([a-z]\d?)", problem_id.lower())
    if not m:
        raise ValueError(f"Cannot parse Codeforces problem ID: {problem_id}")
    contest_id = m.group(1)
    index = m.group(2).upper()
    return contest_id, index


EXTRACT_STATEMENT_JS = """
() => {
    const el = document.querySelector('.problem-statement');
    if (!el) return null;

    const clone = el.cloneNode(true);

    // Replace inline math
    clone.querySelectorAll('script[type="math/tex"]').forEach(script => {
        const latex = script.textContent;
        const text = document.createTextNode('$' + latex + '$');
        const prev = script.previousElementSibling;
        if (prev && (prev.classList.contains('MathJax') || prev.classList.contains('MathJax_Preview'))) {
            prev.replaceWith(text);
            script.remove();
        } else {
            script.replaceWith(text);
        }
    });

    // Replace display math
    clone.querySelectorAll('script[type="math/tex; mode=display"]').forEach(script => {
        const latex = script.textContent;
        const text = document.createTextNode('\\n$$' + latex + '$$\\n');
        const prev = script.previousElementSibling;
        if (prev && (prev.classList.contains('MathJax') || prev.classList.contains('MathJax_Display'))) {
            prev.replaceWith(text);
            script.remove();
        } else {
            script.replaceWith(text);
        }
    });

    // Remove MathJax artifacts
    clone.querySelectorAll('.MathJax, .MathJax_Preview, .MathJax_Display').forEach(e => e.remove());

    // Extract structured parts
    const header = clone.querySelector('.header');
    const title = header?.querySelector('.title')?.textContent?.trim() || '';
    const timeLimit = header?.querySelector('.time-limit')?.textContent?.trim() || '';
    const memLimit = header?.querySelector('.memory-limit')?.textContent?.trim() || '';

    // Body paragraphs (divs without class after .header)
    let body = '';
    const children = clone.children;
    for (let i = 0; i < children.length; i++) {
        const child = children[i];
        if (child === header) continue;
        if (child.classList.contains('input-specification')) {
            body += '\\n## 输入\\n' + child.innerText.replace(/^Input\\n?/i, '') + '\\n';
        } else if (child.classList.contains('output-specification')) {
            body += '\\n## 输出\\n' + child.innerText.replace(/^Output\\n?/i, '') + '\\n';
        } else if (child.classList.contains('sample-tests')) {
            // handled separately
        } else if (child.classList.contains('note')) {
            body += '\\n## 说明\\n' + child.innerText.replace(/^Note\\n?/i, '') + '\\n';
        } else {
            body += '\\n' + child.innerText + '\\n';
        }
    }

    // Samples
    const samples = [];
    clone.querySelectorAll('.sample-test').forEach(st => {
        const inp = st.querySelector('.input pre')?.textContent || '';
        const out = st.querySelector('.output pre')?.textContent || '';
        samples.push({input: inp, output: out});
    });

    return {title, timeLimit, memLimit, body, samples};
}
"""


async def fetch_statement(page: Page, problem_id: str) -> str:
    """Fetch CF problem statement as Markdown. Page must be from a stealth browser."""
    contest_id, index = _parse_problem_id(problem_id)
    url = f"https://codeforces.com/contest/{contest_id}/problem/{index}"

    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await wait_for_cloudflare(page)

    # Detect redirect to homepage (problem doesn't exist)
    current = page.url.rstrip("/")
    if current == "https://codeforces.com" or "/problem/" not in current:
        raise RuntimeError(
            f"{problem_id} 不存在（重定向到 {current}）。"
            f"请检查题号：contest {contest_id} 可能没有 problem {index}"
        )

    await page.wait_for_selector(".problem-statement", timeout=15000)

    data = await page.evaluate(EXTRACT_STATEMENT_JS)
    if not data:
        raise RuntimeError(f"Failed to extract statement for {problem_id}")

    parts = []
    parts.append(f"# {data['title']}")
    parts.append(f"\n{data['timeLimit']} | {data['memLimit']}\n")
    parts.append(data["body"])

    if data["samples"]:
        parts.append("\n## 样例\n")
        for i, s in enumerate(data["samples"], 1):
            parts.append(f"### 输入 {i}\n```\n{s['input']}\n```\n")
            parts.append(f"### 输出 {i}\n```\n{s['output']}\n```\n")

    return "\n".join(parts)


async def fetch_editorial(page: Page, problem_id: str) -> str | None:
    """Fetch editorial blog post for the contest."""
    contest_id, _ = _parse_problem_id(problem_id)
    contest_url = f"https://codeforces.com/contest/{contest_id}"

    await page.goto(contest_url, wait_until="domcontentloaded", timeout=30000)
    await wait_for_cloudflare(page)
    await asyncio.sleep(2)

    # Find editorial link
    editorial_href = await page.evaluate("""
        () => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                const text = (a.textContent || '').toLowerCase();
                const href = a.href || '';
                if ((text.includes('editorial') || text.includes('tutorial') || text.includes('разбор'))
                    && href.includes('/blog/')) {
                    return href;
                }
            }
            return null;
        }
    """)

    if not editorial_href:
        return None

    await page.goto(editorial_href, wait_until="domcontentloaded", timeout=30000)
    await wait_for_cloudflare(page)
    await asyncio.sleep(2)

    # Extract content from .ttypography
    content = await page.evaluate("""
        () => {
            const el = document.querySelector('.ttypography');
            if (!el) return null;

            const clone = el.cloneNode(true);

            // Replace math
            clone.querySelectorAll('script[type="math/tex"]').forEach(script => {
                const latex = script.textContent;
                const text = document.createTextNode('$' + latex + '$');
                const prev = script.previousElementSibling;
                if (prev && (prev.classList.contains('MathJax') || prev.classList.contains('MathJax_Preview'))) {
                    prev.replaceWith(text);
                    script.remove();
                } else {
                    script.replaceWith(text);
                }
            });
            clone.querySelectorAll('script[type="math/tex; mode=display"]').forEach(script => {
                const latex = script.textContent;
                const text = document.createTextNode('\\n$$' + latex + '$$\\n');
                const prev = script.previousElementSibling;
                if (prev) prev.remove();
                script.replaceWith(text);
            });
            clone.querySelectorAll('.MathJax, .MathJax_Preview, .MathJax_Display').forEach(e => e.remove());

            return clone.innerText;
        }
    """)

    if not content:
        return None

    return f"# CF{contest_id} Editorial\n\n{content.strip()}"
