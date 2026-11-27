#!/usr/bin/env python3
"""导出原生 App 使用的 data/app.json（由 data/news.js、data/daily/*.js 派生）"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def slice_object(text, pos):
    """从 pos 起找第一个 {，按括号配对取出完整 JSON 文本"""
    start = text.find("{", pos)
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return None


def pick(obj, keys):
    return {k: obj.get(k) for k in keys if obj.get(k) not in (None, "", [])}


def main():
    news_path = os.path.join(DATA, "news.js")
    if not os.path.exists(news_path):
        raise SystemExit("缺少 data/news.js")

    text = read_text(news_path)
    head = re.search(r"window\.BATTERY_NEWS\s*=\s*", text)
    news = json.loads(slice_object(text, head.end() if head else 0))

    daily = {}
    daily_dir = os.path.join(DATA, "daily")
    if os.path.isdir(daily_dir):
        for fn in sorted(os.listdir(daily_dir)):
            if not fn.endswith(".js"):
                continue
            body = read_text(os.path.join(daily_dir, fn))
            pattern = r'window\.BATTERY_DAILY\["([^"]+)"\]\s*=\s*'
            for m in re.finditer(pattern, body):
                obj_raw = slice_object(body, m.end())
                if not obj_raw:
                    continue
                try:
                    obj = json.loads(obj_raw)
                except Exception as exc:
                    print("跳过 %s：%s" % (m.group(1), exc))
                    continue
                daily[m.group(1)] = pick(
                    obj,
                    ["key", "type", "label", "dateCN", "weekday", "title", "dek",
                     "sections", "stats", "categories", "updatedAt"],
                )

    keys = []
    for a in (news.get("archive") or []):
        k = a.get("key")
        if k and k in daily and k not in keys:
            keys.append(k)
    for k in sorted(daily.keys(), reverse=True):
        if k not in keys:
            keys.append(k)

    app = {
        "updatedAt": news.get("updatedAt"),
        "date": news.get("date"),
        "dateCN": news.get("dateCN"),
        "weekday": news.get("weekday"),
        "headline": news.get("headline"),
        "lead": news.get("lead"),
        "stats": news.get("stats"),
        "picked": [
            pick(p, ["id", "kicker", "title", "summary", "points", "heat", "time",
                     "tags", "score", "importance", "caveats", "sources"])
            for p in (news.get("picked") or [])
        ],
        "hot": [
            pick(h, ["id", "rank", "title", "category", "heat", "trend", "time",
                     "summary", "points", "score", "importance", "caveats", "sources"])
            for h in (news.get("hot") or [])
        ],
        "dailyKeys": keys,
        "daily": daily,
    }

    out = os.path.join(DATA, "app.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(app, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(out) / 1024.0
    print("已生成 %s（%.1f KB，精选 %d + 热点 %d，日报 %d 期）" % (
        out, size, len(app["picked"]), len(app["hot"]), len(daily)))


if __name__ == "__main__":
    main()
