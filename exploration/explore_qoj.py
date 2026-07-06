"""QOJ exploration script.

Launches a headed browser with anti-detection settings, handles Cloudflare,
then inspects problem statement structure (HTML vs PDF), formula format, and samples.

Key findings:
- Two statement formats: HTML inline (article.uoj-article) or PDF (iframe)
- HTML format: MathJax renders formulas, source in <script type="math/tex">
- PDF format: downloadable at /download.php?type=statement&id={problem_id}
- No editorial system
- Cloudflare protection requires anti-detection browser settings
"""

import asyncio
import re
from playwright.async_api import async_playwright


DATA_DIR = "data/qoj_profile"
PROBLEM_URL_HTML = "https://qoj.ac/problem/1"
PROBLEM_URL_PDF = "https://qoj.ac/problem/14554"


async def wait_for_cloudflare(page, timeout=90):
    """Wait for Cloudflare challenge to resolve."""
    for i in range(timeout):
        title = await page.title()
        if "just a moment" not in title.lower() and "请稍候" not in title and "安全验证" not in title:
            return True
        if i % 10 == 0 and i > 0:
            print(f"    ... waiting ({i}s)")
        await asyncio.sleep(1)
    return False


async def main():
    async with async_playwright() as p:
        print("▶ Step 1: Launching browser with anti-detection settings...")
        context = await p.chromium.launch_persistent_context(
            DATA_DIR,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            delete navigator.__proto__.webdriver;
            window.chrome = {runtime: {}};
        """)

        # --- Test with HTML-format problem (problem/1) ---
        print(f"\n▶ Step 2: Testing HTML-format problem: {PROBLEM_URL_HTML}")
        await page.goto(PROBLEM_URL_HTML, wait_until="domcontentloaded", timeout=60000)

        title = await page.title()
        if "just a moment" in title.lower() or "请稍候" in title:
            print("  ⚠️  Cloudflare triggered. Please click checkbox if needed.")
            if not await wait_for_cloudflare(page):
                print("  ✗ Timeout")
                await context.close()
                return
        print(f"  ✓ Loaded: {await page.title()}")

        # Wait for MathJax rendering
        try:
            await page.wait_for_function(
                "() => document.querySelector('article.uoj-article')?.innerHTML.trim().length > 50",
                timeout=15000
            )
        except:
            await asyncio.sleep(5)

        # Extract HTML-format statement
        print("\n▶ Step 3: Extracting HTML-format statement")
        html_data = await page.evaluate("""() => {
            const article = document.querySelector('article.uoj-article');
            if (!article) return {type: 'not_found'};
            const hasIframe = !!document.querySelector('iframe#statements-pdf');
            if (hasIframe || article.innerHTML.trim().length < 50) {
                return {type: 'pdf', iframeSrc: document.querySelector('iframe#statements-pdf')?.src || ''};
            }
            return {
                type: 'html',
                innerHTML: article.innerHTML,
                childCount: article.children.length,
                hasMathJax: !!article.querySelector('.MathJax_SVG'),
                mathScripts: Array.from(article.querySelectorAll('script[type="math/tex"]')).map(s => s.textContent).slice(0, 10),
                pres: Array.from(article.querySelectorAll('pre')).map(p => p.textContent.substring(0, 200))
            };
        }""")

        print(f"  Format: {html_data['type']}")
        if html_data['type'] == 'html':
            print(f"  Children: {html_data['childCount']}")
            print(f"  MathJax rendered: {html_data['hasMathJax']}")
            print(f"  Math formulas ({len(html_data['mathScripts'])}):")
            for m in html_data['mathScripts'][:5]:
                print(f"    ${m}$")
            print(f"  Pre blocks ({len(html_data['pres'])}):")
            for pre in html_data['pres'][:3]:
                print(f"    {pre[:100]}")
            print(f"  innerHTML preview:")
            print(html_data['innerHTML'][:3000])

        # --- Test with PDF-format problem (problem/14554) ---
        print(f"\n\n▶ Step 4: Testing PDF-format problem: {PROBLEM_URL_PDF}")
        await page.goto(PROBLEM_URL_PDF, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        pdf_data = await page.evaluate("""() => {
            const article = document.querySelector('article.uoj-article');
            const iframe = document.querySelector('iframe#statements-pdf');
            return {
                articleEmpty: !article || article.innerHTML.trim().length < 50,
                hasIframe: !!iframe,
                iframeSrc: iframe?.src || '',
                langs: Array.from(document.querySelectorAll('a[href*="/statement/"]')).map(a => ({
                    text: a.textContent.trim(),
                    href: a.href
                }))
            };
        }""")
        print(f"  Article empty: {pdf_data['articleEmpty']}")
        print(f"  Has PDF iframe: {pdf_data['hasIframe']}")
        print(f"  Iframe src: {pdf_data['iframeSrc']}")
        print(f"  Language variants: {pdf_data['langs']}")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print("""
✓ Two statement formats exist on QOJ:
  - HTML: content in article.uoj-article, math in <script type="math/tex">
  - PDF: iframe at /download.php?type=statement&id={id}

✓ Detection: check article.uoj-article innerHTML length
  - > 50 chars → HTML format (extract DOM)
  - < 50 chars + iframe#statements-pdf → PDF format (download)

✓ Formula: MathJax with $...$ and \\(...\\), source in <script type="math/tex">
✓ Samples: <pre> blocks (HTML format) or in PDF
✓ No editorial system
✓ Cloudflare: anti-detection settings required
✓ No login required
✓ Download: /download.php?type=statement&id={id} (PDF)
✓ Download: /download.php?type=problem&id={id} (attachments/test data)
""")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
