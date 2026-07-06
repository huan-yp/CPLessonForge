# AtCoder 探索发现

## 访问方式
- 是否需要登录：否
- Cloudflare 防护：否
- 首次访问人类介入方式：无需

## 题面获取
- URL 模式：`https://atcoder.jp/contests/{contest_id}/tasks/{contest_id}_{problem_letter}`
  - 例：ABC282G → `https://atcoder.jp/contests/abc282/tasks/abc282_g`
  - 可加 `?lang=en` 参数，但页面始终包含双语内容
- 获取方式：DOM 提取
- DOM 选择器：`#task-statement .lang-en`（英文版）或 `#task-statement .lang-ja`（日文版）
- 响应格式：服务端渲染 HTML
- 公式格式：KaTeX 渲染后的 DOM。**原始 TeX 源文本在 `<annotation encoding="application/x-tex">` 标签中**
  - 示例：`<span class="katex"><span class="katex-mathml"><math>...<annotation encoding="application/x-tex">A=(A_1,A_2,\ldots,A_N)</annotation></math></span>...</span>`
  - 提取策略：用正则或 DOM API 提取所有 `annotation[encoding="application/x-tex"]` 的 textContent，替换外层 `<var><span>...<span>` 为 `$tex$`
- 样例格式说明：
  - 位于 `<section>` 中，标题为 "Sample Input N" / "Sample Output N"
  - 样例数据在 `<pre>` 标签中，纯文本
- 页面结构：
  ```
  #task-statement
  └─ span.lang-en
     ├─ p (Score: 600 points)
     └─ div.part
        ├─ section > h3 "Problem Statement" + p*
        ├─ section > h3 "Constraints" + p/ul
        ├─ section > h3 "Input" + p + pre (格式说明)
        ├─ section > h3 "Output" + p
        ├─ section > h3 "Sample Input 1" + pre
        ├─ section > h3 "Sample Output 1" + pre + p (解释)
        └─ ...更多样例
  ```

## 题解获取
- 是否有题解/Editorial：是（官方 Editorial，contest 结束后发布）
- 获取方式：两步
  1. 访问列表页获取 editorial ID
  2. 访问单篇 editorial 页面提取内容
- URL 模式：
  - 列表页：`https://atcoder.jp/contests/{contest_id}/editorial?lang=en`
  - 单篇：`https://atcoder.jp/contests/{contest_id}/editorial/{editorial_id}`
- 列表页结构：
  - 页面按问题分组，每个问题有 `<h3>` 标题（如 "G - Similar Permutation"）
  - 每个问题下有多个 editorial 链接，分为"解説"（日文）和"Editorial"（英文翻译）
  - 选英文版：找 text 为 "Editorial" 的 `<a>` 链接
- 单篇 editorial 内容格式：
  - 标题：`.col-sm-12 h2`（含问题名 + "Editorial" + author）
  - 内容：`hr.mt-1` 之后的兄弟 `<div>` 元素
  - 公式格式：同题面（KaTeX，`annotation` 标签中有 TeX 源）
  - 内容结构：`<h3>` 分段 + `<p>` 段落 + 公式

## 题目 ID 映射规则

| 用户输入 | contest_id | problem_letter |
|----------|-----------|----------------|
| ABC282G  | abc282    | g              |
| ARC150A  | arc150    | a              |
| AGC001F  | agc001    | f              |
| DP_A     | dp        | a              |

解析规则：
- 匹配 `(abc|arc|agc|dp)(\d+)?([a-z]\d?)?`
- contest_id = prefix + number（全小写）
- problem_letter = 最后的字母部分（小写）
- task_id = `{contest_id}_{problem_letter}`

## 注意事项
- **Persistent context 超时问题**：使用 `launch_persistent_context()` 时 AtCoder 页面加载极慢（>60s 超时），但 `browser.launch()` + `new_context()` 正常工作。正式工具中建议对 AtCoder 不使用 persistent context。
- **双语页面**：`#task-statement` 下同时包含 `.lang-ja` 和 `.lang-en`，需明确选择语言。
- **KaTeX 已渲染**：页面上的公式是服务端渲染的 KaTeX DOM，不是原始 `$...$` 文本。必须从 `<annotation>` 标签提取源 TeX。
- **innerText 不可用**：直接取 innerText 会得到公式的渲染文本（如 `(1,2,…,N)` 被重复显示为 aria 和视觉两份），需要自定义提取逻辑。
- **Editorial 可能缺失**：不是所有 contest 都有英文 editorial。如果只有"解説"（日文），需要回退到日文版。
- **无速率限制**：AtCoder 未观察到明显的速率限制或 anti-bot 措施。
