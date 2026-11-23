# 采集管线说明

`python scripts/collect.py`：只用 Python 标准库，无需 pip 安装任何包。

- 抓取：5 个垂直信源（中国电池工业协会 / 北极星储能网 / 中国储能网 / OFweek 锂电网 / 电池网）
- 聚类：标题归一化 + bigram Jaccard 相似度去重，同一事件合并
- 热度：独立信源数（被几家机构报道）
- 摘要：按“含数据 / 含动作词”给句子打分，取 1–2 句完整句；另抽 2–3 条关键信息
- AI 评分：读环境变量 `DEEPSEEK_API_KEY`，调 DeepSeek 一次批量给出 score / importance / caveats；未配置则静默跳过
- 趋势：读 `data/history/*.json` 算近 7 日每日信源数
- 输出：`data/news.js`、`data/history/YYYY-MM-DD.json`、`data/daily/*.js`（日报 / 月报 / 年报）

本地手工跑：`$env:DEEPSEEK_API_KEY="sk-..."; python scripts/collect.py`
