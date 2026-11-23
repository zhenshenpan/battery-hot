#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日报修缮步骤（在 collect.py 之后运行）：
1. 清掉摘要里的页面 JS 残留（如 traceid / .concat(...)），清空后用标题事实补要点；
2. 日报只保留当天（含前一日滞后入库）的事件；
3. 调 DeepSeek 把当天素材写成有判断的日报（无 key 时退回结构化版本）。
    python scripts/refine.py
"""
import os
import re
import json
import datetime
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
NEWS = os.path.join(DATA, "news.js")
HIST = os.path.join(DATA, "history")
DAILY = os.path.join(DATA, "daily")

JUNK = re.compile(r"traceid|\.concat\(|function\s*\(|=>|\bvar\s+\w+\s*=|"
                  r"<script|<style|document\.|window\.|onclick|import\s|export\s|"
                  r"console\.|ajax|jQuery|\ufffd", re.I)
HAN = re.compile(r"[\u4e00-\u9fa5]")

CAT_ORDER = ["招中标", "价格行情", "项目动态", "技术路线", "政策标准", "海外市场", "企业动态"]

DAILY_SYS = (
    "你是储能与电池行业日报的主编。基于给定素材写一份给行业从业者看的当日日报：\n"
    "- 只允许使用素材里出现的事实与数字，不得补写、不得推测具体数据；信息不足就写「仅见标题」「待核实」。\n"
    "- 不写「本文将从三方面阐述」这类空话，不堆标题，而是把同一品类的事放在一起判断：价格往哪走、"
    "规模往哪集中、技术路线的真实进度与宣传口径差在哪。\n"
    "- 语气克制、专业，句子直给。\n"
    "输出 JSON：{\"lede\":\"150-220字当日综述，点出今天最值得记住的一两件事与市场方向\","
    "\"sections\":[{\"title\":\"招中标：…\",\"paras\":[\"80-150字\",\"…\"]}],"
    "\"watch\":[\"值得继续盯的3条，每条40字内\"],\"next\":\"明日关注，40字内\"}。\n"
    "sections 只写素材里确实有条目的品类，2-4 个即可，标题要具体。"
)


def title_points(title):
    ps = []
    m = re.search(r"(\d+(?:\.\d+)?)\s*MW\s*/\s*(\d+(?:\.\d+)?)\s*(MWh|GWh)", title, re.I) \
        or re.search(r"(\d+(?:\.\d+)?)\s*(GWh|MWh)", title, re.I)
    if m:
        ps.append("规模 " + m.group(0).replace(" ", ""))
    m = re.search(r"(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*元/Wh", title)
    if m:
        ps.append("单价 " + m.group(0).replace(" ", ""))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(亿元|万元)", title)
    if m:
        ps.append("金额 " + m.group(0).replace(" ", ""))
    for kw in ("EPC招标", "EPC中标", "开标", "中标候选人公示", "并网", "开工", "投运", "征求意见"):
        if kw in title.replace(" ", ""):
            ps.append("环节 " + kw)
            break
    for kw in ("构网型", "半固态", "全钒液流", "钠离子", "压缩空气"):
        if kw in title:
            ps.append(kw)
            break
    return ps[:4]


def clean_text(s):
    if not s:
        return ""
    parts = [p.strip() for p in re.split(r"[。！？]", s) if p.strip()]
    keep = [p for p in parts if not JUNK.search(p) and len(HAN.findall(p)) >= 6]
    return ("。".join(keep) + "。") if keep else ""


def ai_call(payload, max_tokens=1300):
    key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if not key:
        print("[refine] 未配置 DEEPSEEK_API_KEY，跳过 AI 主笔")
        return None
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": DAILY_SYS},
                     {"role": "user", "content": payload}],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read().decode("utf-8", "ignore"))
        print("[refine] tokens=%s" % (resp.get("usage") or {}).get("total_tokens"))
        return json.loads(resp["choices"][0]["message"]["content"])
    except Exception as e:
        print("[refine] AI 失败 %r" % (e,))
        return None


def load_history(today_str):
    fn = os.path.join(HIST, today_str + ".json")
    if not os.path.exists(fn):
        return []
    with open(fn, encoding="utf-8") as fp:
        return json.load(fp)


def build_daily(news, rows, today):
    def days_ago(r):
        try:
            return (today - datetime.datetime.strptime(r.get("date", today.strftime("%Y-%m-%d")),
                                                       "%Y-%m-%d")).days
        except Exception:
            return 0

    fresh = [r for r in rows if days_ago(r) == 0]
    if len(fresh) < 6:
        fresh = [r for r in rows if days_ago(r) <= 1]
    fresh.sort(key=lambda r: (-r.get("heat", 1), -len(r.get("summary") or "")))

    ai = None
    if fresh:
        material = [dict(t=r["title"], k=r.get("category") or "", h=r.get("heat", 1),
                         s=(r.get("summary") or "")[:70],
                         src="/".join((r.get("sources") or [])[:3])) for r in fresh[:30]]
        ai = ai_call(json.dumps(dict(date=today.strftime("%Y-%m-%d"), items=material),
                                ensure_ascii=False))

    if ai and (ai.get("lede") or ai.get("sections")):
        secs = []
        if ai.get("lede"):
            secs.append(dict(title="今日综述", paras=[str(ai["lede"])]))
        for s in (ai.get("sections") or []):
            ps = [str(p) for p in (s.get("paras") or []) if str(p).strip()]
            if ps:
                secs.append(dict(title=str(s.get("title") or "当日要点"), paras=ps))
        if ai.get("watch"):
            secs.append(dict(title="值得继续盯", paras=[str(w) for w in ai["watch"] if str(w).strip()]))
        if ai.get("next"):
            secs.append(dict(title="明日关注", paras=[str(ai["next"])]))
        dek = (f"{today.strftime('%m月%d日')}·当日 {len(fresh)} 起事件、"
               f"{len({r.get('category') for r in fresh})} 个品类；数字均来自标题与摘要，未做补写。")
        return dict(title=f"储能与电池行业日报 · {today.strftime('%m月%d日')}",
                    dek=dek, sections=secs, tables=news.get("daily", {}).get("tables", []),
                    end="本期日报由采集管线生成，AI 主笔")

    secs = []
    for cat in CAT_ORDER:
        sub = [r for r in fresh if r.get("category") == cat][:4]
        if not sub:
            continue
        paras = [f"{r['title']}（{r.get('date', '')[-5:]}，{' / '.join((r.get('sources') or [])[:2])}）"
                 + (f" — {r['summary']}" if r.get("summary") else "") for r in sub]
        secs.append(dict(title=cat, paras=paras))
    dek = f"{today.strftime('%m月%d日')}·当日 {len(fresh)} 起事件（未配置 AI 主笔，按品类排列）"
    return dict(title=f"储能与电池行业日报 · {today.strftime('%m月%d日')}", dek=dek,
                sections=secs, tables=news.get("daily", {}).get("tables", []),
                end="本期日报由采集管线自动生成")


def main():
    if not os.path.exists(NEWS):
        print("[refine] 找不到 data/news.js")
        return 0
    with open(NEWS, encoding="utf-8") as fp:
        raw = fp.read()
    news = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(tzinfo=None)
    today_str = today.strftime("%Y-%m-%d")

    fixed = 0
    for coll in ("picked", "hot"):
        for it in news.get(coll, []):
            s2 = clean_text(it.get("summary") or "")
            pts = [p for p in (it.get("points") or []) if not JUNK.search(p) and len(HAN.findall(p)) >= 4]
            if s2 != (it.get("summary") or "") or len(pts) != len(it.get("points") or []):
                fixed += 1
            it["summary"] = s2
            it["points"] = pts or title_points(it["title"])
    print(f"[refine] 摘要修缮 {fixed} 条")

    rows = load_history(today_str)
    if not rows:
        print("[refine] 没有当天历史快照，日报保持不变")
    else:
        news["daily"] = build_daily(news, rows, today)
        key = today_str
        obj = dict(key=key, type="day",
                   label=f"{today.month}月{today.day}日",
                   dateCN=news.get("dateCN", ""), weekday=news.get("weekday", ""),
                   issue=news.get("issue", ""), updatedAt=news.get("updatedAt", ""),
                   stats=news.get("stats", []), categories=news.get("categories", []),
                   daily=news["daily"])
        os.makedirs(DAILY, exist_ok=True)
        with open(os.path.join(DAILY, key + ".js"), "w", encoding="utf-8") as fp:
            fp.write("window.BATTERY_DAILY = window.BATTERY_DAILY || {};\n")
            fp.write("window.BATTERY_DAILY[" + json.dumps(key) + "] = "
                     + json.dumps(obj, ensure_ascii=False, indent=1) + ";\n")

    with open(NEWS, "w", encoding="utf-8") as fp:
        fp.write("/* 由 scripts/collect.py + scripts/refine.py 自动生成，请勿手工编辑 */\n"
                 "window.BATTERY_NEWS = " + json.dumps(news, ensure_ascii=False, indent=2) + ";\n")
    print(f"[refine] done | 日报节数={len(news.get('daily', {}).get('sections', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
