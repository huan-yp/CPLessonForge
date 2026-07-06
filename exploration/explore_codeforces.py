"""Codeforces exploration script.

Launches a stealth Chrome browser with persistent context,
then inspects problem statement DOM structure, formula format, and editorial location.

Key findings:
- Problem statement in .problem-statement (server-rendered HTML + MathJax)
- Formulas: source in <script type="math/tex"> elements
- Editorial: blog posts at /blog/entry/{id}, content in .ttypography
- CF API provides metadata only (no statement text, no blog content)
- MUST use stealth mode to bypass Cloudflare

用法：cd 到 scripts/ 目录后执行：
    uv run python explore_codeforces.py
"""

import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth


DATA_DIR = "data/cf_profile"
PROBLEM_URL = "https://codeforces.com/problemset/problem/1542/E1"
CONTEST_URL = "https://codeforces.com/contest/1542"


async def wait_for_cf(page):
    """Wait for Cloudflare challenge to pass if triggered."""
    await asyncio.sleep(3)
    title = await page.title()
    if "just a moment" in title.lower() or "请稍候" in title:
        print("⚠️  Cloudflare 验证被触发，请在浏览器中完成验证（通常自动通过，如需手动请点击复选框）")
        input("  完成后按 Enter 继续...")
        await asyncio.sleep(3)
        title = await page.title()
        print(f"  验证后页面标题: {title}")
    return title


async def main():
    stealth = Stealth(navigator_platform_override="MacIntel")

    async with stealth.use_async(async_playwright()) as p:
        # Step 1: Launch browser with persistent context + stealth
        print("▶ Step 1: Launching stealth browser with persistent context...")
        context = await p.chromium.launch_persistent_context(
            DATA_DIR,
            headless=False,
            channel="chrome",
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # Step 2: Navigate to problem and handle Cloudflare
        print(f"\n▶ Step 2: Navigating to {PROBLEM_URL}")
        await page.goto(PROBLEM_URL, wait_until="domcontentloaded", timeout=30000)
        title = await wait_for_cf(page)
        print(f"  Page title: {title}")

        # Wait for problem statement
        try:
            await page.wait_for_selector(".problem-statement", timeout=15000)
            print("  ✓ Found .problem-statement")
        except Exception:
            print("  ✗ .problem-statement not found")
            print("  如果 Cloudflare 仍在验证，请完成后按 Enter...")
            input()
            await page.wait_for_selector(".problem-statement", timeout=30000)

        # Step 3: Analyze DOM structure
        print("\n▶ Step 3: DOM structure analysis")
        structure = await page.eval_on_selector(
            ".problem-statement",
            """el => {
                const children = el.children;
                const result = [];
                for (let i = 0; i < children.length; i++) {
                    const child = children[i];
                    result.push({
                        tag: child.tagName,
                        cls: child.className,
                        preview: child.textContent.substring(0, 80)
                    });
                }
                return result;
            }"""
        )
        for item in structure:
            print(f"  <{item['tag']} class=\"{item['cls']}\"> → {item['preview'][:60]}...")

        # Step 4: Formula format analysis
        print("\n▶ Step 4: Formula format")
        math_scripts = await page.eval_on_selector(
            ".problem-statement",
            """el => {
                const inline = el.querySelectorAll('script[type="math/tex"]');
                const display = el.querySelectorAll('script[type="math/tex; mode=display"]');
                return {
                    inlineCount: inline.length,
                    displayCount: display.length,
                    inlineSamples: Array.from(inline).slice(0, 5).map(s => s.textContent),
                    displaySamples: Array.from(display).slice(0, 3).map(s => s.textContent)
                };
            }"""
        )
        print(f"  Inline math (<script type='math/tex'>): {math_scripts['inlineCount']} elements")
        for s in math_scripts['inlineSamples']:
            print(f"    ${s}$")
        print(f"  Display math (<script type='math/tex; mode=display'>): {math_scripts['displayCount']} elements")
        for s in math_scripts['displaySamples']:
            print(f"    $${s}$$")

        # Step 5: Test clean text extraction with math restored
        print("\n▶ Step 5: Clean text extraction")
        clean_text = await page.eval_on_selector(
            ".problem-statement",
            """el => {
                const clone = el.cloneNode(true);
                // Replace inline math: MathJax span + script -> $latex$
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
                    const text = document.createTextNode('$$' + latex + '$$');
                    const prev = script.previousElementSibling;
                    if (prev) { prev.remove(); }
                    script.replaceWith(text);
                });
                // Remove remaining MathJax artifacts
                clone.querySelectorAll('.MathJax, .MathJax_Preview').forEach(el => el.remove());
                return clone.innerText.substring(0, 2000);
            }"""
        )
        print(f"  Extracted text (first 1500 chars):")
        print(clean_text[:1500])

        # Step 6: Sample tests
        print("\n▶ Step 6: Sample tests format")
        samples = await page.eval_on_selector_all(
            ".problem-statement .sample-test",
            """els => els.map(el => ({
                input: el.querySelector('.input pre')?.textContent || '',
                output: el.querySelector('.output pre')?.textContent || ''
            }))"""
        )
        for i, s in enumerate(samples):
            print(f"  Sample {i+1}:")
            print(f"    Input: {s['input'][:100]}")
            print(f"    Output: {s['output'][:100]}")

        # Step 7: Find editorial
        print(f"\n▶ Step 7: Looking for editorial on contest page")
        await page.goto(CONTEST_URL, wait_until="domcontentloaded", timeout=30000)
        await wait_for_cf(page)

        editorial_links = await page.eval_on_selector_all(
            "a",
            """els => els
                .filter(el => {
                    const text = (el.textContent || '').toLowerCase();
                    const href = el.href || '';
                    return (text.includes('editorial') || text.includes('tutorial') || text.includes('разбор'))
                        && href.includes('/blog/');
                })
                .map(el => ({href: el.href, text: el.textContent.trim().substring(0, 80)}))
            """
        )
        print(f"  Editorial links found: {len(editorial_links)}")
        for link in editorial_links:
            print(f"    {link['text']} → {link['href']}")

        if not editorial_links:
            print("  (Editorial link not found on contest page - may need manual discovery)")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print("""
✓ Problem URL: /problemset/problem/{contestId}/{index}
✓ Container: .problem-statement
✓ Formula: <script type="math/tex"> for inline, mode=display for block
✓ Samples: .sample-test > .input/.output > pre
✓ Editorial: blog post at /blog/entry/{id}, content in .ttypography
✓ Cloudflare: persistent context required, may need human intervention
✗ CF API: metadata only, no statement/blog content
""")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
