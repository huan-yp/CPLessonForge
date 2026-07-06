# problem-fetcher

从竞赛 OJ 平台批量获取题面和题解的 CLI 工具。支持 Luogu、AtCoder、Codeforces、QOJ。

## 安装

```bash
uv sync
uv run playwright install chromium
```

## 使用

```bash
# 获取题面
uv run python fetch.py P3413
uv run python fetch.py ABC282G
uv run python fetch.py CF1542E1
uv run python fetch.py QOJ14554

# 获取题面 + 题解
uv run python fetch.py CF1542E1 --editorial

# 批量获取
uv run python fetch.py P3413 P4124 CF1542E1 --editorial

# 指定输出目录
uv run python fetch.py --output-dir ./problems P3413

# 登录（Luogu 题解需要）
uv run python fetch.py login luogu
```

## 支持的平台

| 平台 | 题号前缀 | 题面 | 题解 | 认证方式 |
|------|---------|------|------|---------|
| Luogu | `P`, `B` | 无需登录 | 需登录 | Persistent context |
| AtCoder | `ABC`, `ARC`, `AGC` | 公开 | 公开 | 无 |
| Codeforces | `CF` | Cloudflare | Cloudflare | Stealth + persistent |
| QOJ | `QOJ` | Cloudflare | 无题解系统 | Stealth + persistent |

## 输出格式

```
<output-dir>/
├── CF1542E1/
│   ├── statement.md
│   └── editorial.md
├── QOJ14554/
│   ├── statement.md
│   └── statement.pdf   # PDF 格式题目
└── ...
```

## 特性

- Cloudflare 反爬自动绕过（Stealth 模式 + 系统 Chrome）
- 浏览器 session 持久化，首次验证后后续自动通过
- 不存在的题号秒级报错（检测重定向），不浪费 15s 超时
- CF/QOJ 失败自动重试一次
- 非交互环境优雅降级（跳过需要登录的操作并提示）
- Luogu 直接提取嵌入 JSON 中的 Markdown 原文
- CF/QOJ 从 `<script type="math/tex">` 还原 LaTeX 公式
- AtCoder 从 KaTeX `<annotation>` 标签恢复 TeX 源码
- QOJ 自动识别 HTML/PDF 两种格式

## 项目结构

```
fetch.py              CLI 入口
lib/
├── browser.py        浏览器管理（Stealth/Normal/Luogu 三种模式）
└── platforms/
    ├── luogu.py      洛谷采集器
    ├── atcoder.py    AtCoder 采集器
    ├── codeforces.py Codeforces 采集器
    └── qoj.py        QOJ 采集器
exploration/          开发过程中的探索脚本和发现记录
```

## License

MIT
