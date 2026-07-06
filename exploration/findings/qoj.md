# QOJ 探索发现

## 访问方式
- 是否需要登录：否（题面公开可见）
- Cloudflare 防护：是（Turnstile 验证）
- 首次访问人类介入方式：使用反检测设置的 Playwright 可自动通过（`--disable-blink-features=AutomationControlled` + 移除 `--enable-automation` + 清除 `navigator.webdriver`）。偶尔需要人工点击验证框。持久化 context 可减少后续验证。

## 题面获取

### 重要：QOJ 存在两种题面格式

**格式 A：HTML 内联（如 problem/1）**
- 题面直接嵌入 `<article class="uoj-article top-buffer-md">` 内
- HTML 结构：`<p>`, `<ul>`, `<li>`, `<pre>` 等标准标签
- 公式：MathJax 渲染后，原始 LaTeX 保存在 `<script type="math/tex" id="MathJax-Element-{n}">...</script>` 中
- 行内公式：`<script type="math/tex">N</script>`
- 行间公式：`<script type="math/tex; mode=display">...</script>`（待确认）
- 样例：`<pre>` 标签

**格式 B：PDF/iframe（如 problem/14554）**
- `<article class="uoj-article">` 为空
- 题面通过 iframe 加载：`<iframe src="/download.php?type=statement&id={id}" id="statements-pdf">`
- PDF 下载端点：`GET /download.php?type=statement&id={problem_id}`
- 此类题目通常来自正式比赛（如 CCPC Online 2025），原始题面就是 PDF

### 判断方式
- 加载页面后检查 `article.uoj-article` 内容长度
- 如果 innerHTML < 50 字符 → 格式 B（PDF）
- 如果 innerHTML > 50 字符 → 格式 A（HTML）
- 也可检查是否存在 `iframe#statements-pdf`

### URL 模式
- 题面页：`https://qoj.ac/problem/{problem_id}`
- 指定语言：`https://qoj.ac/problem/{problem_id}/statement/{lang}`（`default`/`en`/`zh`）
- PDF 下载：`https://qoj.ac/download.php?type=statement&id={problem_id}`
- 附件下载：`https://qoj.ac/download.php?type=problem&id={problem_id}`

### 获取方式
- DOM 提取（格式 A）：等待 MathJax 渲染完成后从 `article.uoj-article` 提取
- PDF 下载（格式 B）：直接请求 `/download.php?type=statement&id={id}`

### DOM 选择器
- 主容器：`.uoj-content`
- 题面区域：`#tab-statement article.uoj-article`
- PDF iframe：`iframe#statements-pdf`
- MathJax 公式源：`script[type="math/tex"]`

### MathJax 配置
```javascript
MathJax.Hub.Config({
    tex2jax: {
        inlineMath: [["$", "$"], ["\\(", "\\)"]],
        processEscapes: true
    }
});
```

### 公式格式
- 源文本使用 `$...$` 或 `\(...\)` 标记行内公式
- MathJax 渲染后 LaTeX 源保存在 `<script type="math/tex">` 标签中
- 提取策略：与 Codeforces 相同——从 `<script type="math/tex">` 提取原始 LaTeX

### 样例格式说明
- 格式 A：样例在 `<pre>` 标签中，前面通常有标题（如 `<h3>Sample Input</h3>`）
- 格式 B：样例在 PDF 中

## 题解获取
- 是否有题解/Editorial：**否**（无内置题解系统）
- QOJ 有博客系统（`/blogs`），部分用户可能发布题解博客，但无官方结构化题解入口
- 题目页面无 Editorial/Solution 链接

## 页面结构
- UOJ 开源架构（Bootstrap + jQuery + MathJax）
- Tab 导航：Statement | Languages | Submit | Custom Test | Attachments | Discussions & Issues
- 多语言支持：`/problem/{id}/statement/en`、`/problem/{id}/statement/zh` 等

## 注意事项
- **Cloudflare 反爬**：必须使用反检测设置，标准 Playwright 会被拦截
  - 必需参数：`args=["--disable-blink-features=AutomationControlled"]`
  - 必需参数：`ignore_default_args=["--enable-automation"]`
  - 必需脚本：`Object.defineProperty(navigator, 'webdriver', {get: () => undefined})`
- **两种格式并存**：必须同时支持 HTML 提取和 PDF 下载两种路径
- **PDF 格式题目较多**：正式比赛题目（CCPC、ICPC 等）通常为 PDF 格式
- **无独立 API**：所有数据通过 DOM 提取或直接下载获取
- **MathJax 渲染时间**：需要等待 MathJax 完成渲染后再提取（`waitForFunction` 检测 `.MathJax_SVG` 出现）
- **持久化 context 重要**：保存 Cloudflare cookie 避免重复验证
- **`/problem/{id}/statement/default` 返回完整 HTML 页面**（非 API fragment），不适合直接作为数据源
