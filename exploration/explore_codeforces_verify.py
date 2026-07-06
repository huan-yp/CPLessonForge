"""Codeforces 完整验证脚本 - Stealth 模式绕过 Cloudflare。

在终端手动运行：
    cd scripts/ && uv run python explore_codeforces_verify.py
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth


DATA_DIR = "data/cf_profile"
PROBLEM_URL = "https://codeforces.com/problemset/problem/1542/E1"
CONTEST_URL = "https://codeforces.com/contest/1542"
OUTPUT_FILE = "findings/codeforces_verify.json"


async def ensure_cf_passed(page, url):
    """Navigate to URL and ensure Cloudflare is passed."""
    print(f"  → {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)

    # Wait and check for Cloudflare
    for attempt in range(5):
        await asyncio.sleep(4)
        title = await page.title()
        if "just a moment" not in title.lower() and "请稍候" not in title:
            print(f"  ✓ {title[:50]}")
            return True
        if attempt == 0:
            print("  ⏳ Cloudflare 验证中，等待自动通过...")
        if attempt == 2:
            print("  ⚠️  如果浏览器显示复选框，请手动点击")
            print("     点击后等待页面跳转，然后按 Enter...")
            input()

    # Final check
    title = await page.title()
    if "just a moment" in title.lower() or "请稍候" in title:
        print("  ⚠️  Cloudflare 仍未通过，请在浏览器中操作后按 Enter...")
        input()
    return True


async def main():
    results = {}

    stealth = Stealth(navigator_platform_override="MacIntel")

    async with stealth.use_async(async_playwright()) as p:
        print("=" * 60)
        print("Codeforces 探索验证 (Stealth 模式)")
        print("=" * 60)

        # Launch with stealth settings
        print("\n▶ 启动 Stealth 浏览器...")
        context = await p.chromium.launch_persistent_context(
            DATA_DIR,
            headless=False,
            channel="chrome",  # Use system Chrome instead of bundled Chromium
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else await context.new_page()
        print("  ✓ Stealth 浏览器已启动")

        # ============================================================
        # PART 1: 题面公式提取验证
        # ============================================================
        print("\n" + "=" * 60)
        print("PART 1: 题面公式提取验证")
        print("=" * 60)

        await ensure_cf_passed(page, PROBLEM_URL)

        # Wait for problem statement
        try:
            await page.wait_for_selector(".problem-statement", timeout=15000)
            print("  ✓ .problem-statement 已加载")
        except Exception:
            print("  ✗ 页面加载失败，请在浏览器中手动导航到题目页面后按 Enter...")
            input()
            await page.wait_for_selector(".problem-statement", timeout=30000)

        # 1a: Verify <script type="math/tex"> elements exist
        math_info = await page.eval_on_selector(
            ".problem-statement",
            """el => {
                const inline = el.querySelectorAll('script[type="math/tex"]');
                const display = el.querySelectorAll('script[type="math/tex; mode=display"]');
                return {
                    inlineCount: inline.length,
                    displayCount: display.length,
                    inlineSamples: Array.from(inline).slice(0, 8).map(s => s.textContent),
                    displaySamples: Array.from(display).slice(0, 3).map(s => s.textContent)
                };
            }"""
        )
        print(f"\n  公式统计:")
        print(f"    行内公式: {math_info['inlineCount']} 个")
        print(f"    行间公式: {math_info['displayCount']} 个")
        print(f"  行内公式样本:")
        for i, s in enumerate(math_info['inlineSamples'][:5]):
            print(f"    [{i}] ${s}$")
        if math_info['displaySamples']:
            print(f"  行间公式样本:")
            for i, s in enumerate(math_info['displaySamples']):
                print(f"    [{i}] $${s}$$")

        results['formula_inline_count'] = math_info['inlineCount']
        results['formula_display_count'] = math_info['displayCount']
        results['formula_samples'] = math_info['inlineSamples']

        # 1b: Full text extraction with math restored
        clean_text = await page.eval_on_selector(
            ".problem-statement",
            """el => {
                const clone = el.cloneNode(true);

                // Replace inline math
                clone.querySelectorAll('script[type="math/tex"]').forEach(script => {
                    const latex = script.textContent;
                    const replacement = document.createTextNode('$' + latex + '$');
                    let prev = script.previousElementSibling;
                    while (prev && (prev.classList.contains('MathJax') ||
                                    prev.classList.contains('MathJax_Preview'))) {
                        const toRemove = prev;
                        prev = prev.previousElementSibling;
                        toRemove.remove();
                    }
                    script.replaceWith(replacement);
                });

                // Replace display math
                clone.querySelectorAll('script[type="math/tex; mode=display"]').forEach(script => {
                    const latex = script.textContent;
                    const replacement = document.createTextNode('\\n$$' + latex + '$$\\n');
                    let prev = script.previousElementSibling;
                    while (prev) {
                        if (prev.querySelector && prev.querySelector('.MathJax')) {
                            const toRemove = prev;
                            prev = prev.previousElementSibling;
                            toRemove.remove();
                        } else {
                            break;
                        }
                    }
                    script.replaceWith(replacement);
                });

                // Remove MathJax artifacts
                clone.querySelectorAll('.MathJax, .MathJax_Preview, .MathJax_Display').forEach(el => el.remove());

                // Extract structured parts
                const header = clone.querySelector('.header');
                const titleEl = header?.querySelector('.title');
                const timeLimitEl = header?.querySelector('.time-limit');
                const memLimitEl = header?.querySelector('.memory-limit');

                const sections = {};
                sections.title = titleEl?.textContent?.trim() || '';
                sections.timeLimit = timeLimitEl?.textContent?.replace('time limit per test', '')?.trim() || '';
                sections.memoryLimit = memLimitEl?.textContent?.replace('memory limit per test', '')?.trim() || '';

                const bodyDiv = header?.nextElementSibling;
                sections.body = bodyDiv?.innerText?.trim() || '';

                const inputSpec = clone.querySelector('.input-specification');
                sections.input = inputSpec?.innerText?.replace(/^Input\\n?/, '')?.trim() || '';

                const outputSpec = clone.querySelector('.output-specification');
                sections.output = outputSpec?.innerText?.replace(/^Output\\n?/, '')?.trim() || '';

                const sampleTests = clone.querySelectorAll('.sample-test');
                sections.samples = Array.from(sampleTests).map(st => ({
                    input: st.querySelector('.input pre')?.textContent || '',
                    output: st.querySelector('.output pre')?.textContent || ''
                }));

                const note = clone.querySelector('.note');
                sections.note = note?.innerText?.replace(/^Note\\n?/, '')?.trim() || '';

                return sections;
            }"""
        )

        print(f"\n  提取结果:")
        print(f"    标题: {clean_text['title']}")
        print(f"    时限: {clean_text['timeLimit']}")
        print(f"    内存: {clean_text['memoryLimit']}")
        print(f"    正文 (前 400 字符):")
        print(f"      {clean_text['body'][:400]}")
        print(f"    输入说明: {clean_text['input'][:150]}")
        print(f"    输出说明: {clean_text['output'][:150]}")
        print(f"    样例数: {len(clean_text['samples'])}")
        for i, s in enumerate(clean_text['samples']):
            print(f"      [{i}] in={s['input'][:30]} out={s['output'][:30]}")

        dollar_count = clean_text['body'].count('$')
        print(f"\n  ✓ 公式嵌入验证: 正文含 {dollar_count} 个 $ 符号")
        results['formula_extraction_works'] = dollar_count > 0
        results['extracted_body'] = clean_text['body'][:500]

        # ============================================================
        # PART 2: Editorial 获取验证
        # ============================================================
        print("\n" + "=" * 60)
        print("PART 2: Editorial 获取验证")
        print("=" * 60)

        # Navigate to contest page to find editorial link
        await ensure_cf_passed(page, CONTEST_URL)
        await asyncio.sleep(2)

        # Search for editorial links
        editorial_links = await page.eval_on_selector_all(
            "a",
            """els => els
                .filter(el => {
                    const text = (el.textContent || '').toLowerCase();
                    return text.includes('editorial') || text.includes('tutorial') || text.includes('разбор');
                })
                .map(el => ({href: el.href, text: el.textContent.trim().substring(0, 100)}))
            """
        )
        print(f"\n  比赛页面 editorial 链接: {len(editorial_links)} 个")
        for link in editorial_links:
            print(f"    {link['text'][:60]} → {link['href']}")

        # Also check all blog links on page
        if not editorial_links:
            blog_links = await page.eval_on_selector_all(
                "a[href*='/blog/entry/']",
                "els => els.map(el => ({href: el.href, text: el.textContent.trim().substring(0, 100)}))"
            )
            print(f"  页面 blog 链接: {len(blog_links)} 个")
            for link in blog_links[:5]:
                print(f"    {link['text'][:60]} → {link['href']}")

        # Try a different contest known to have editorial
        if not editorial_links:
            print("\n  Contest 1542 无 editorial 链接，尝试 contest 1984...")
            await ensure_cf_passed(page, "https://codeforces.com/contest/1984")
            await asyncio.sleep(2)
            editorial_links = await page.eval_on_selector_all(
                "a",
                """els => els
                    .filter(el => {
                        const text = (el.textContent || '').toLowerCase();
                        return (text.includes('editorial') || text.includes('tutorial') || text.includes('разбор'))
                            && el.href && el.href.includes('/blog/');
                    })
                    .map(el => ({href: el.href, text: el.textContent.trim().substring(0, 100)}))
                """
            )
            print(f"  Contest 1984 editorial 链接: {len(editorial_links)} 个")
            for link in editorial_links:
                print(f"    {link['text'][:60]} → {link['href']}")

        # Navigate to an editorial page
        editorial_url = editorial_links[0]['href'] if editorial_links else None

        if not editorial_url:
            # Use a known editorial as fallback
            editorial_url = "https://codeforces.com/blog/entry/130183"
            print(f"\n  使用已知 editorial: {editorial_url}")

        print(f"\n  访问 Editorial...")
        await ensure_cf_passed(page, editorial_url)
        await asyncio.sleep(2)

        # Extract editorial content
        try:
            await page.wait_for_selector(".ttypography", timeout=10000)
            print("  ✓ .ttypography 存在")

            editorial_data = await page.eval_on_selector(
                ".ttypography",
                """el => {
                    const clone = el.cloneNode(true);

                    clone.querySelectorAll('script[type="math/tex"]').forEach(script => {
                        const latex = script.textContent;
                        const replacement = document.createTextNode('$' + latex + '$');
                        let prev = script.previousElementSibling;
                        while (prev && (prev.classList.contains('MathJax') ||
                                        prev.classList.contains('MathJax_Preview'))) {
                            const toRemove = prev;
                            prev = prev.previousElementSibling;
                            toRemove.remove();
                        }
                        script.replaceWith(replacement);
                    });

                    clone.querySelectorAll('script[type="math/tex; mode=display"]').forEach(script => {
                        const latex = script.textContent;
                        const replacement = document.createTextNode('\\n$$' + latex + '$$\\n');
                        let prev = script.previousElementSibling;
                        while (prev) {
                            if (prev.querySelector && prev.querySelector('.MathJax')) {
                                const toRemove = prev;
                                prev = prev.previousElementSibling;
                                toRemove.remove();
                            } else { break; }
                        }
                        script.replaceWith(replacement);
                    });

                    clone.querySelectorAll('.MathJax, .MathJax_Preview, .MathJax_Display').forEach(el => el.remove());

                    return {
                        text: clone.innerText.substring(0, 3000),
                        mathCount: el.querySelectorAll('script[type="math/tex"]').length,
                    };
                }"""
            )

            print(f"  公式数: {editorial_data['mathCount']}")
            print(f"  Editorial 文本 (前 800 字符):")
            print(f"    {editorial_data['text'][:800]}")

            results['editorial_extraction_works'] = True
            results['editorial_url'] = editorial_url
            results['editorial_math_count'] = editorial_data['mathCount']
            results['editorial_text_sample'] = editorial_data['text'][:500]

        except Exception as e:
            print(f"  ✗ .ttypography 未找到: {e}")
            # Try alternative selector
            content = await page.evaluate("document.querySelector('.content')?.innerText?.substring(0, 500) || 'N/A'")
            print(f"  .content 内容: {content}")
            results['editorial_extraction_works'] = False

        # ============================================================
        # PART 3: 连续访问稳定性
        # ============================================================
        print("\n" + "=" * 60)
        print("PART 3: 连续访问稳定性")
        print("=" * 60)

        test_urls = [
            ("1542/E2", "https://codeforces.com/problemset/problem/1542/E2"),
            ("1984/C1", "https://codeforces.com/problemset/problem/1984/C1"),
        ]
        success = 0
        for name, url in test_urls:
            await asyncio.sleep(3)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(4)
                title = await page.title()
                if "just a moment" not in title.lower() and "请稍候" not in title:
                    try:
                        await page.wait_for_selector(".problem-statement", timeout=10000)
                        print(f"  ✓ {name} - 成功")
                        success += 1
                    except Exception:
                        print(f"  △ {name} - 页面加载但无 .problem-statement (title: {title[:40]})")
                else:
                    print(f"  ✗ {name} - Cloudflare 拦截")
                    print("    请完成验证后按 Enter...")
                    input()
                    try:
                        await page.wait_for_selector(".problem-statement", timeout=15000)
                        print(f"    → 验证后成功")
                        success += 1
                    except Exception:
                        print(f"    → 验证后仍失败")
            except Exception as e:
                print(f"  ✗ {name} - 错误: {e}")

        results['stability_success'] = success
        results['stability_total'] = len(test_urls)
        print(f"\n  稳定性: {success}/{len(test_urls)}")

        # ============================================================
        # SUMMARY
        # ============================================================
        print("\n" + "=" * 60)
        print("验证总结")
        print("=" * 60)
        print(f"  公式提取: {'✓' if results.get('formula_extraction_works') else '✗'}")
        print(f"  Editorial 提取: {'✓' if results.get('editorial_extraction_works') else '✗'}")
        print(f"  连续访问: {results.get('stability_success', 0)}/{results.get('stability_total', 0)}")

        # Save
        Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n  结果已保存: {OUTPUT_FILE}")

        await context.close()
        print("\n✓ 完成")


if __name__ == "__main__":
    asyncio.run(main())
