# Codeforces 探索发现

## 访问方式
- 是否需要登录：否（题面公开）
- Cloudflare 防护：是（aggressive，curl 完全被阻挡）
- 绕过方式：**必须使用 Stealth 模式**
  - 使用 `playwright-stealth` 库（`Stealth().use_async(async_playwright())`）
  - 使用系统 Chrome（`channel="chrome"`）而非 Playwright 自带 Chromium
  - 添加 `--disable-blink-features=AutomationControlled`
  - 移除 `--enable-automation` 默认参数（`ignore_default_args=["--enable-automation"]`）
  - 使用 persistent context（`data/cf_profile/`）保持 cookie
- 普通 Playwright 模式：**无法通过 Cloudflare**（即使人工点击验证也无效）
- Stealth 模式稳定性：已验证连续访问多个页面均成功（2/2）

## 题面获取
- URL 模式：`https://codeforces.com/problemset/problem/{contest_id}/{problem_index}`
  - 例：`https://codeforces.com/problemset/problem/1542/E1`
  - 备用模式：`https://codeforces.com/contest/{contest_id}/problem/{problem_index}`
- 获取方式：DOM 提取（无可用 API 获取题面文本）
- API 端点：CF 公共 API（`/api/problemset.problems`）仅返回元数据（contestId, index, name, type, tags），**不含题面文本**
- DOM 选择器：`.problem-statement`
- 响应格式：服务端渲染的 HTML + MathJax 客户端渲染
- Markdown 源文本字段路径：无（CF 不提供 Markdown 原文）
- 公式格式：
  - 原始格式（作者编写时）：`$$$...$$$`（行内），`$$$$$$...$$$$$$`（行间/display）
  - 渲染后 DOM 中：MathJax 将公式渲染为复杂 span 结构，但保留 `<script type="math/tex">` 元素作为源文本备份
  - **已验证提取策略**：从 `<script type="math/tex">` 提取 LaTeX 源文本，替换为 `$...$`；display math 从 `<script type="math/tex; mode=display">` 提取，替换为 `$$...$$`
  - 验证结果：单题 64 个行内公式全部正确还原（如 `$n$`、`$1, 2, \ldots, n$`、`$a_1, a_2, \ldots, a_n$`）
- 样例格式说明：
  - 容器：`.sample-tests`
  - 输入/输出：各在一个 `<pre>` 标签内，纯文本
  - 样例分组：`.sample-test` 内含 `.input` 和 `.output` 子 div

## 题面 DOM 结构

```
.problem-statement
├── .header
│   ├── .title          → "E1. Abnormal Permutation Pairs (easy version)"
│   ├── .time-limit     → "time limit per test: 1 second"
│   ├── .memory-limit   → "memory limit per test: 512 megabytes"
│   ├── .input-file     → "standard input"
│   └── .output-file    → "standard output"
├── div (无 class)       → 题面正文（含公式、HTML 段落）
├── .input-specification → 输入格式说明
├── .output-specification → 输出格式说明
├── .sample-tests        → 样例输入输出
│   └── .sample-test
│       ├── .input > pre  → 样例输入
│       └── .output > pre → 样例输出
└── .note               → 备注/提示
```

## 题面提取算法

```python
# 伪代码：从 .problem-statement 提取 Markdown 文本
1. 克隆 .problem-statement DOM
2. 找到所有 <script type="math/tex">，读取 textContent 作为 LaTeX
3. 将 MathJax span + script 替换为 $latex$
4. 对 display math 同理，替换为 $$latex$$
5. 分段提取：
   - .header → 标题 + 限制信息
   - 无 class 的 div → 题面正文（innerText）
   - .input-specification → "## 输入" + innerText
   - .output-specification → "## 输出" + innerText
   - .sample-tests → 格式化为代码块
   - .note → "## 说明" + innerText
```

## 题解获取
- 是否有题解/Editorial：是（几乎所有正式比赛都有）
- 获取方式：浏览器导航到 editorial 博客页面，从 `.ttypography` 提取
- URL 模式：`https://codeforces.com/blog/entry/{blog_id}`
- **已验证** Editorial 发现方式：
  1. 从比赛页面（`/contest/{id}`）查找含 "editorial"/"tutorial"/"разбор" 的链接（验证成功：contest 1542 → `/blog/entry/92492`）
  2. 通过 CF API `user.blogEntries` 搜索比赛作者的博客列表作为备选
- 内容格式：HTML（与题面相同的 MathJax 渲染 + `<script type="math/tex">` 备份）
- 内容容器：`.ttypography`（已验证，单篇 editorial 含 165 个公式）
- Editorial 结构：按题目分段，每题含 "Hint"、"Tutorial"、"Code" 小节
- CF API `blogEntry.view` 不返回 content 字段，仅返回元数据（必须浏览器提取）

## 注意事项

1. **必须使用 Stealth 模式**：普通 Playwright（含 headless=False）无法通过 Cloudflare，即使人工点击验证也无效。必须：
   - `from playwright_stealth import Stealth`
   - `async with Stealth(navigator_platform_override="MacIntel").use_async(async_playwright()) as p:`
   - `channel="chrome"` + `ignore_default_args=["--enable-automation"]`
   - `args=["--disable-blink-features=AutomationControlled"]`

2. **请求间隔**：连续访问建议间隔 > 3 秒，避免触发频率限制。

3. **MathJax 渲染延迟**：`<script type="math/tex">` 在 DOM 加载时就已存在（服务端渲染），无需等待 MathJax 完成渲染。

4. **公式还原的关键**：不要依赖 MathJax span 的 textContent（会丢失 LaTeX 命令）。必须从 `<script type="math/tex">` 标签中读取原始 LaTeX。清理时需移除 `.MathJax`、`.MathJax_Preview`、`.MathJax_Display` 残留元素。

5. **CF 特殊三美元符号**：CF 的 `$$$...$$$` 格式是其特有的，在输出 Markdown 时已自动转换为标准 `$...$`（因为 DOM 中 script 标签内容本身就是纯 LaTeX）。

6. **Editorial 定位**：优先在比赛页面查找含 "editorial"/"tutorial"/"разбор" 的 `<a>` 链接。博客 ID 与比赛 ID 无固定数学关系。

7. **wait_until 策略**：使用 `domcontentloaded` 而非 `networkidle`（MathJax CDN 持续有请求，networkidle 会超时）。

8. **API 限制**：CF 公共 API 有速率限制（建议每次请求间隔 > 2 秒），且不提供题面/博客正文内容。API 仅可用于获取元数据或发现 editorial 博客 ID。
