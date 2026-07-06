"""QOJ problem fetcher.

Statement: two formats — HTML inline (DOM extraction) or PDF download
Requires stealth browser to bypass Cloudflare.
No editorial system available.
"""

import asyncio
from pathlib import Path
from playwright.async_api import Page

from ..browser import wait_for_cloudflare


EXTRACT_HTML_STATEMENT_JS = """
() => {
    const article = document.querySelector('#tab-statement article.uoj-article')
                 || document.querySelector('article.uoj-article');
    if (!article) return null;

    // Check if content is empty (PDF format)
    if (article.innerHTML.trim().length < 50) return null;

    const clone = article.cloneNode(true);

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
        if (prev) prev.remove();
        script.replaceWith(text);
    });

    clone.querySelectorAll('.MathJax, .MathJax_Preview, .MathJax_SVG').forEach(e => e.remove());

    return clone.innerText;
}
"""


async def fetch_statement(page: Page, problem_id: str, output_dir: Path | None = None) -> str:
    """Fetch QOJ problem statement.

    Returns Markdown string for HTML format.
    For PDF format, downloads to output_dir and returns a note about the PDF.
    """
    pid = problem_id.replace("QOJ", "").replace("qoj", "")
    url = f"https://qoj.ac/problem/{pid}"

    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await wait_for_cloudflare(page)
    await asyncio.sleep(3)

    # Check for PDF iframe
    has_pdf = await page.evaluate("""
        () => {
            const iframe = document.querySelector('iframe#statements-pdf');
            if (iframe) return true;
            const article = document.querySelector('#tab-statement article.uoj-article')
                         || document.querySelector('article.uoj-article');
            if (!article || article.innerHTML.trim().length < 50) return true;
            return false;
        }
    """)

    if has_pdf:
        pdf_url = f"https://qoj.ac/download.php?type=statement&id={pid}"
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = output_dir / "statement.pdf"
            # Use in-page fetch to inherit browser cookies (bypasses Cloudflare)
            pdf_base64 = await page.evaluate("""
                async (url) => {
                    const resp = await fetch(url);
                    const blob = await resp.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    });
                }
            """, pdf_url)
            import base64
            pdf_bytes = base64.b64decode(pdf_base64)
            pdf_path.write_bytes(pdf_bytes)
            return f"# QOJ{pid}\n\n题面为 PDF 格式，已保存至 statement.pdf"
        else:
            return f"# QOJ{pid}\n\n题面为 PDF 格式，下载地址：{pdf_url}"

    # HTML format: wait for MathJax
    try:
        await page.wait_for_function(
            "() => !document.querySelector('.MathJax_Processing')",
            timeout=10000
        )
    except Exception:
        pass

    # Extract content
    title = await page.evaluate("""
        () => {
            const h1 = document.querySelector('.page-header');
            return h1 ? h1.textContent.trim() : '';
        }
    """)

    content = await page.evaluate(EXTRACT_HTML_STATEMENT_JS)

    if not content:
        return f"# QOJ{pid}\n\n无法提取题面内容（可能为空页面或未知格式）"

    header = f"# QOJ{pid}"
    if title:
        header += f" - {title}"
    return f"{header}\n\n{content.strip()}"


async def fetch_editorial(page: Page, problem_id: str) -> str | None:
    """QOJ has no editorial system."""
    return None
