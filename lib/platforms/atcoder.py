"""AtCoder problem fetcher.

Statement: extracted from #task-statement .lang-en with KaTeX annotation recovery
Editorial: from contest editorial page
"""

import re
from playwright.async_api import Page


def _parse_problem_id(problem_id: str) -> tuple[str, str]:
    """Parse 'ABC282G' -> ('abc282', 'g')"""
    m = re.match(r"(abc|arc|agc|dp)(\d*)?([a-z]\d?)", problem_id.lower())
    if not m:
        raise ValueError(f"Cannot parse AtCoder problem ID: {problem_id}")
    prefix, number, letter = m.groups()
    contest_id = prefix + (number or "")
    return contest_id, letter


# JS to extract text with LaTeX formulas restored from KaTeX annotations
EXTRACT_JS = """
(container) => {
    function extractNode(node) {
        if (node.nodeType === 3) return node.textContent;
        if (node.nodeType !== 1) return '';

        const el = node;
        const tag = el.tagName.toLowerCase();

        // KaTeX span: extract LaTeX from annotation
        if (el.classList.contains('katex')) {
            const ann = el.querySelector('annotation[encoding="application/x-tex"]');
            if (ann) return '$' + ann.textContent + '$';
            return el.textContent;
        }

        // Skip KaTeX internals (already handled by parent .katex)
        if (el.classList.contains('katex-mathml') || el.classList.contains('katex-html')) {
            return '';
        }

        // Block elements
        if (tag === 'br') return '\\n';
        if (tag === 'pre') return '\\n```\\n' + el.textContent + '\\n```\\n';
        if (tag === 'li') return '- ' + Array.from(el.childNodes).map(extractNode).join('');

        let inner = Array.from(el.childNodes).map(extractNode).join('');

        if (tag === 'p') return '\\n' + inner + '\\n';
        if (tag === 'h3') return '\\n## ' + inner + '\\n';
        if (tag === 'ul' || tag === 'ol') return '\\n' + inner;
        if (tag === 'var') return inner;

        return inner;
    }

    return extractNode(container);
}
"""


async def fetch_statement(page: Page, problem_id: str) -> str:
    """Fetch AtCoder problem statement as Markdown."""
    contest_id, letter = _parse_problem_id(problem_id)
    url = f"https://atcoder.jp/contests/{contest_id}/tasks/{contest_id}_{letter}"

    await page.goto(url, timeout=30000)
    await page.wait_for_selector("#task-statement", timeout=15000)

    # Extract English version
    en_section = await page.query_selector("#task-statement .lang-en")
    if not en_section:
        en_section = await page.query_selector("#task-statement")

    text = await en_section.evaluate(EXTRACT_JS)

    # Get title
    title = await page.eval_on_selector(
        "title", "el => el.textContent"
    )
    # Title format: "G - Similar Permutation"
    task_title = title.split(" - ", 1)[-1].split(" - ")[0] if " - " in title else title

    header = f"# {problem_id.upper()} - {task_title}\n"
    return header + text


async def fetch_editorial(page: Page, problem_id: str) -> str | None:
    """Fetch official editorial for the problem."""
    contest_id, letter = _parse_problem_id(problem_id)

    # Go to editorial list page
    url = f"https://atcoder.jp/contests/{contest_id}/editorial"
    await page.goto(url, timeout=30000)
    await page.wait_for_load_state("domcontentloaded")

    # Find editorial link for this problem
    # Structure: <h3>G - Title</h3> <div class="editorial-section"><ul><li>...<a>...</li></ul></div>
    editorial_url = await page.evaluate("""
        (letter) => {
            const headings = document.querySelectorAll('h3');
            for (const h3 of headings) {
                const hText = h3.textContent.trim().toLowerCase();
                if (!hText.startsWith(letter + ' -') && !hText.startsWith(letter + ' ')) continue;
                // Found the right problem section; next sibling is div.editorial-section
                const section = h3.nextElementSibling;
                if (!section) continue;
                // Prefer English editorial, then any /editorial/ link
                let best = null;
                const links = section.querySelectorAll('a[href*="/editorial/"]');
                for (const a of links) {
                    const href = a.href;
                    if (href.includes('/jump?')) continue;
                    const text = a.textContent.trim().toLowerCase();
                    if (text === 'editorial' || text.includes('english')) return href;
                    if (!best) best = href;
                }
                return best;
            }
            return null;
        }
    """, letter)

    if not editorial_url:
        return None

    await page.goto(editorial_url, timeout=30000)
    await page.wait_for_load_state("domcontentloaded")

    # Extract editorial content after the <hr>
    content = await page.evaluate("""
        () => {
            function extractNode(node) {
                if (node.nodeType === 3) return node.textContent;
                if (node.nodeType !== 1) return '';
                const el = node;
                const tag = el.tagName.toLowerCase();
                if (el.classList.contains('katex')) {
                    const ann = el.querySelector('annotation[encoding="application/x-tex"]');
                    if (ann) return '$' + ann.textContent + '$';
                    return el.textContent;
                }
                if (el.classList.contains('katex-mathml') || el.classList.contains('katex-html')) return '';
                if (tag === 'pre') return '\\n```\\n' + el.textContent + '\\n```\\n';
                if (tag === 'br') return '\\n';
                if (tag === 'li') return '- ' + Array.from(el.childNodes).map(extractNode).join('') + '\\n';
                let inner = Array.from(el.childNodes).map(extractNode).join('');
                if (tag === 'p') return '\\n' + inner + '\\n';
                if (tag === 'h3' || tag === 'h2') return '\\n## ' + inner + '\\n';
                if (tag === 'ul' || tag === 'ol') return '\\n' + inner;
                return inner;
            }

            // Find content after first <hr>
            const hr = document.querySelector('hr.mt-1') || document.querySelector('hr');
            if (!hr) return null;
            let content = '';
            let sibling = hr.nextElementSibling;
            while (sibling) {
                content += extractNode(sibling);
                sibling = sibling.nextElementSibling;
            }
            return content;
        }
    """)

    if not content:
        return None

    return f"# {problem_id.upper()} Editorial\n\n{content.strip()}"
