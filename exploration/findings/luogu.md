# Luogu (洛谷) 探索发现

## 访问方式
- 是否需要登录：题面**不需要**，题解**需要**
- Cloudflare 防护：否
- 首次访问人类介入方式：仅获取题解时需要登录（支持扫码/账密登录，cookie 持久化后后续自动）

## 题面获取
- URL 模式：`https://www.luogu.com.cn/problem/{pid}` （如 P3413, P4124, P8820）
- 获取方式：DOM 提取（SSR 嵌入的 JSON 数据）
- API 端点：无独立 API，数据嵌入在页面 `<script type="application/json">` 标签中
- DOM 选择器：`script[type="application/json"]`（第一个匹配 `template === "problem.show"` 的）
- 响应格式：HTML 页面，内嵌 JSON
- Markdown 源文本字段路径：
  ```
  data.problem.content.background    — 题目背景（可能为空）
  data.problem.content.description   — 题目描述
  data.problem.content.formatI       — 输入格式
  data.problem.content.formatO       — 输出格式
  data.problem.content.hint          — 提示/数据范围
  data.problem.content.name          — 题目名称
  data.problem.samples               — [[input1, output1], [input2, output2], ...]
  data.problem.limits.time           — 时间限制数组（ms，每个测试点）
  data.problem.limits.memory         — 内存限制数组（KB，每个测试点；524288 = 512MB）
  ```
- `data.problem.contenu` 与 `data.problem.content` 完全一致（i18n 别名）
- 公式格式：`$...$`（标准 LaTeX 行内公式）
- 样例格式说明：`samples` 是二维数组 `[[input, output], ...]`，input/output 为纯文本字符串

## 题解获取
- 是否有题解/Editorial：是（用户提交的题解，需登录查看）
- 获取方式：导航到题解页面 → 提取嵌入 JSON
- URL 模式：`https://www.luogu.com.cn/problem/solution/{pid}`
- 分页参数：`?page=2`（每页 10 条）
- DOM 选择器：`script[type="application/json"]`（匹配 `template === "problem.solution"` 的）
- 数据路径：
  ```
  data.solutions.result[]         — 题解列表
  data.solutions.perPage          — 每页条数（默认 10）
  data.solutions.count            — 题解总数
  ```
- 每条题解字段：
  ```
  result[].content                — Markdown 正文（完整内容）
  result[].contentFull            — bool，是否为完整内容
  result[].title                  — 标题
  result[].author.name            — 作者名
  result[].author.uid             — 作者 UID
  result[].upvote                 — 点赞数
  result[].time                   — Unix 时间戳
  result[].lid                    — 题解 ID (string)
  ```
- 内容格式：Markdown（与题面相同，`$...$` LaTeX 公式）
- 排序：默认按点赞数降序（第一条即最高赞）
- 注意：洛谷题解是用户提交的，质量参差不齐；通常取第一条（按点赞排序）
- **`_contentOnly=1` 参数已失效**（返回 HTML），必须用页面嵌入 JSON 方式提取

## 提取代码模板

```python
# 题面提取（无需登录，可 headless）
async def fetch_luogu_statement(page, pid: str) -> dict:
    await page.goto(f"https://www.luogu.com.cn/problem/{pid}", timeout=30000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(2)
    
    data = await page.evaluate("""
        () => {
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {
                try {
                    const d = JSON.parse(s.textContent);
                    if (d.template === 'problem.show') return d;
                } catch(e) {}
            }
            return null;
        }
    """)
    
    problem = data["data"]["problem"]
    content = problem["content"]
    return {
        "name": content["name"],
        "background": content.get("background", ""),
        "description": content["description"],
        "input_format": content["formatI"],
        "output_format": content["formatO"],
        "hint": content.get("hint", ""),
        "samples": problem["samples"],  # [[in, out], ...]
        "time_limit_ms": problem["limits"]["time"][0],
        "memory_limit_mb": problem["limits"]["memory"][0] // 1024,
    }


# 题解提取（需要登录，使用 persistent context）
async def fetch_luogu_solution(page, pid: str) -> str | None:
    await page.goto(
        f"https://www.luogu.com.cn/problem/solution/{pid}",
        wait_until="domcontentloaded"
    )
    await asyncio.sleep(3)
    
    data = await page.evaluate("""
        () => {
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {
                try {
                    const d = JSON.parse(s.textContent);
                    if (d.template === 'problem.solution') return d;
                } catch(e) {}
            }
            return null;
        }
    """)
    
    if not data:
        return None
    solutions = data["data"]["solutions"]["result"]
    if not solutions:
        return None
    # 取第一条（最高赞）
    return solutions[0]["content"]
```

## 注意事项
- 洛谷题面页面无需登录即可获取完整数据，headless 模式正常工作
- 题解页面严格要求登录，使用 persistent context 保存登录态（首次需 headed 模式手动登录）
- `_contentOnly=1` 参数已全面失效（新版洛谷不再支持），统一使用页面嵌入 JSON 提取
- 题解页面加载较慢，建议用 `wait_until="domcontentloaded"` + `asyncio.sleep(3)` 而非 `networkidle`
- `/fe/api/problem/detail/{pid}` 端点存在但返回 418 (GET) 或 403 (POST 未登录)，不推荐使用
- `limits` 数组长度等于测试点数量，通常所有测试点限制相同，取 `[0]` 即可
- 题目 ID 格式：P + 数字（如 P3413）、B + 数字（入门题）、CF/AT/SP 前缀（远程题）
- 公式无特殊转义，直接使用标准 `$...$` 即可在 Markdown 中正常显示
- 题解按点赞数降序排列，`contentFull=True` 表示内容完整未截断
