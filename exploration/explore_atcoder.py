"""AtCoder 平台探索脚本 - 采集题面和 Editorial 的结构信息"""

import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="en-US")
        page = await context.new_page()

        # === Step 2: 采集题面 ===
        print("=" * 60)
        print("Step 2: 采集题面 - abc282_g")
        print("=" * 60)

        await page.goto("https://atcoder.jp/contests/abc282/tasks/abc282_g", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_selector("#task-statement", timeout=30000)

        # 提取 innerHTML
        inner_html = await page.eval_on_selector("#task-statement", "el => el.innerHTML")
        print(f"\n--- #task-statement innerHTML (前 3000 字符) ---")
        print(inner_html[:3000])
        print(f"\n--- 总长度: {len(inner_html)} 字符 ---")

        # 提取纯文本
        inner_text = await page.eval_on_selector("#task-statement", "el => el.innerText")
        print(f"\n--- #task-statement innerText (前 2000 字符) ---")
        print(inner_text[:2000])

        # 分析结构
        structure = await page.evaluate("""() => {
            const stmt = document.querySelector('#task-statement');
            const sections = stmt.querySelectorAll('section');
            const result = [];
            sections.forEach((s, i) => {
                const h3 = s.querySelector('h3');
                const pres = s.querySelectorAll('pre');
                result.push({
                    index: i,
                    heading: h3 ? h3.textContent.trim() : '(no heading)',
                    preCount: pres.length,
                    firstPreSnippet: pres.length > 0 ? pres[0].textContent.substring(0, 100) : null
                });
            });
            return result;
        }""")
        print(f"\n--- 页面 section 结构 ---")
        for s in structure:
            print(f"  Section {s['index']}: heading='{s['heading']}', pre_count={s['preCount']}")
            if s['firstPreSnippet']:
                print(f"    pre snippet: {s['firstPreSnippet'][:80]}")

        # 检查公式格式 - 查看源码中的 $ 符号
        formula_check = await page.evaluate("""() => {
            const stmt = document.querySelector('#task-statement');
            const html = stmt.innerHTML;
            const patterns = {
                'dollar_single': (html.match(/\\$[^$]+\\$/g) || []).slice(0, 3),
                'dollar_triple': (html.match(/\\$\\$\\$[^$]+\\$\\$\\$/g) || []).slice(0, 3),
                'backslash_paren': (html.match(/\\\\\\([^)]+\\\\\\)/g) || []).slice(0, 3),
                'var_tags': (html.match(/<var>[^<]+<\\/var>/g) || []).slice(0, 5),
                'mathjax_spans': stmt.querySelectorAll('.MathJax, .MathJax_Preview, .mjx-chtml').length,
            };
            return patterns;
        }""")
        print(f"\n--- 公式格式检测 ---")
        for k, v in formula_check.items():
            print(f"  {k}: {v}")

        # === Step 3: 寻找 Editorial ===
        print("\n" + "=" * 60)
        print("Step 3: 寻找 Editorial")
        print("=" * 60)

        await page.goto("https://atcoder.jp/contests/abc282/editorial", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2000)

        # 检查页面标题和结构
        title = await page.title()
        print(f"\nEditorial 页面标题: {title}")

        editorial_links = await page.evaluate("""() => {
            const rows = document.querySelectorAll('table tbody tr, .panel, .editorial-list a, a[href*="editorial"]');
            const links = [];
            document.querySelectorAll('a').forEach(a => {
                if (a.href && a.href.includes('editorial')) {
                    links.push({text: a.textContent.trim().substring(0, 80), href: a.href});
                }
            });
            // Also get the table structure
            const table = document.querySelector('table');
            let tableHtml = table ? table.innerHTML.substring(0, 2000) : 'no table found';
            return {links: links.slice(0, 10), tableHtml};
        }""")
        print(f"\n--- Editorial 链接 ---")
        for link in editorial_links['links']:
            print(f"  {link['text']}: {link['href']}")
        print(f"\n--- Editorial 表格结构 (前 1500 字符) ---")
        print(editorial_links['tableHtml'][:1500])

        # 找到 G 题的 editorial 链接并访问
        g_editorial_url = None
        for link in editorial_links['links']:
            if '_g' in link['href'].lower() or 'G -' in link['text'] or 'abc282_g' in link['href'].lower():
                g_editorial_url = link['href']
                break

        if not g_editorial_url:
            # Try to find from table
            g_editorial_url = await page.evaluate("""() => {
                const links = document.querySelectorAll('a[href*="editorial"]');
                for (const a of links) {
                    if (a.href.includes('/editorial/')) {
                        // Get all editorial links, find one that might be for G
                        const row = a.closest('tr');
                        if (row && row.textContent.includes('G')) {
                            return a.href;
                        }
                    }
                }
                // Just return any editorial link to explore the format
                for (const a of links) {
                    if (a.href.match(/\\/editorial\\/\\d+/)) {
                        return a.href;
                    }
                }
                return null;
            }""")

        if g_editorial_url:
            print(f"\n--- 访问 Editorial 页面: {g_editorial_url} ---")
            await page.goto(g_editorial_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)

            editorial_content = await page.evaluate("""() => {
                // Try common selectors for editorial content
                const selectors = ['.editorial-content', '#editorial-content', '.lang-en', '.lang-ja',
                                   'article', '.markdown', '#task-statement', '.contest-editorial'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent.trim().length > 50) {
                        return {selector: sel, html: el.innerHTML.substring(0, 3000), text: el.innerText.substring(0, 1500)};
                    }
                }
                // Fallback: get main content
                const main = document.querySelector('main, #main-container, .container');
                if (main) {
                    return {selector: 'main/container', html: main.innerHTML.substring(0, 3000), text: main.innerText.substring(0, 1500)};
                }
                return {selector: 'body', html: document.body.innerHTML.substring(0, 3000), text: document.body.innerText.substring(0, 1500)};
            }""")
            print(f"\n  找到内容的选择器: {editorial_content['selector']}")
            print(f"\n  --- Editorial HTML (前 2000 字符) ---")
            print(editorial_content['html'][:2000])
            print(f"\n  --- Editorial Text (前 1000 字符) ---")
            print(editorial_content['text'][:1000])
        else:
            print("\n  ⚠️ 未找到 G 题 Editorial 链接")

        # === Step 4: 额外测试一个不同的题 ===
        print("\n" + "=" * 60)
        print("Step 4: 额外验证 - dp 相关题面")
        print("=" * 60)

        await page.goto("https://atcoder.jp/contests/dp/tasks/dp_a", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_selector("#task-statement", timeout=30000)

        dp_html = await page.eval_on_selector("#task-statement", "el => el.innerHTML")
        print(f"\n--- dp_a 题面 HTML (前 1500 字符) ---")
        print(dp_html[:1500])

        await context.close()
        await browser.close()

    print("\n" + "=" * 60)
    print("探索完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
