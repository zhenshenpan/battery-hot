#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蓄电池热榜 · 采集管线
抓取 5 个垂直信源 -> 标题聚类去重 -> 独立信源数作为热度 -> 摘要提炼 ->
DeepSeek 评分 -> 生成 data/news.js、data/daily/*.js（日报/月报/年报）、data/history/*.json
只用标准库：python scripts/collect.py
"""

import re
import os
import json
import time
import datetime
import urllib.request
import gzip
import html as htmllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
HIST_DIR = os.path.join(DATA_DIR, "history")
DAILY_DIR = os.path.join(DATA_DIR, "daily")

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
WEEK_CN = "一二三四五六日"

RELEVANT = re.compile(
    r"储能|电池|锂电|锂电池|钠电|钠离子|固态|半固态|电芯|正极|负极|电解液|隔膜|碳酸锂|六氟|"
    r"磷酸铁锂|三元|换电|充电桩|BMS|PACK|电堆|氢燃料|构网|微电网|虚拟电厂|风光储|"
    r"并网|招标|中标|EPC|MWh|GWh|MW/|度电|PCS|逆变器|回收|梯次")


# ---------------------------------------------------------------- 抓取基础
def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    for enc in ("utf-8", "gb18030"):
        try:
            s = raw.decode(enc)
            if "\ufffd" not in s:
                return s
        except Exception:
            continue
    return raw.decode("gb18030", "ignore")


def clean(t):
    t = re.sub(r"<[^>]+>", "", t)
    t = htmllib.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def anchors(html):
    return [(h.strip(), t) for h, t in
            re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S)]


def text_of(x):
    return clean(re.sub(r"<!--.*?-->", "", x, flags=re.S))


def abs_url(base, path):
    if path.startswith("http"):
        return path
    if path.startswith("//"):
        return "https:" + path
    return base.rstrip("/") + "/" + path.lstrip("/")


def mmdd(d):
    return d.strftime("%m-%d") if d else ""


def keynum(d):
    return int(d.strftime("%Y%m%d")) if d else 0


# ---------------------------------------------------------------- 信源适配
def src_chinabattery():
    base = "http://www.chinabattery.org"
    out = []
    for p in (1, 2):
        try:
            h = fetch(f"{base}/list/1318/{p}.html")
        except Exception:
            continue
        for href, txt in anchors(h):
            if "/detail/" not in href:
                continue
            t = text_of(txt)
            m = re.match(r"(.+?)\[(\d{4}-\d{1,2}-\d{1,2})\]$", t)
            if not m:
                continue
            title = m.group(1).strip()
            if len(title) < 8:
                continue
            try:
                dt = datetime.datetime.strptime(m.group(2), "%Y-%m-%d")
            except Exception:
                dt = None
            out.append(dict(title=title, url=abs_url(base, href),
                            source="中国电池工业协会", date=dt, region="国内"))
    return out


def src_bjx():
    base = "https://chuneng.bjx.com.cn"
    out = []
    for path in ("/zb/", "/"):
        try:
            h = fetch(base + path)
        except Exception:
            continue
        for href, txt in anchors(h):
            t = text_of(txt)
            if not (14 <= len(t) <= 70) or "news.bjx.com.cn/html/" not in href:
                continue
            m = re.search(r"/html/(\d{4})(\d{2})(\d{2})/", href)
            dt = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
            out.append(dict(title=t, url=href, source="北极星储能网", date=dt, region="国内"))
    return out


def src_escn():
    base = "https://www.escn.com.cn"
    out = []
    try:
        h = fetch(base + "/")
    except Exception:
        return out
    for href, txt in anchors(h):
        if "show-" not in href:
            continue
        t = text_of(txt).lstrip("●· ").strip()
        if not (12 <= len(t) <= 70):
            continue
        out.append(dict(title=t, url=abs_url(base, href), source="中国储能网",
                        date=TODAY.replace(tzinfo=None), region="国内"))
    return out


def src_ofweek():
    base = "https://libattery.ofweek.com"
    out = []
    try:
        h = fetch(base + "/")
    except Exception:
        return out
    for href, txt in anchors(h):
        t = text_of(txt)
        if not (12 <= len(t) <= 70) or "ART-" not in href:
            continue
        m = re.search(r"/(\d{4})-(\d{2})/", href)
        dt = datetime.datetime(int(m.group(1)), int(m.group(2)), 15) if m else None
        out.append(dict(title=t, url=abs_url(base, href), source="OFweek 锂电网",
                        date=dt, region="国内"))
    return out


def src_itdcw():
    base = "https://www.itdcw.com"
    out = []
    try:
        h = fetch(base + "/")
    except Exception:
        return out
    for href, txt in anchors(h):
        t = text_of(txt)
        if not (14 <= len(t) <= 70) or "/news/" not in href or t.startswith("-->"):
            continue
        m = re.search(r"/(\d{2})(\d{2})\d+(\d{4})\.html", href)
        dt = None
        if m:
            try:
                dt = datetime.datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            except Exception:
                dt = None
        if dt and abs((TODAY.replace(tzinfo=None) - dt).days) > 120:
            continue
        out.append(dict(title=t, url=href if href.startswith("http") else abs_url(base, href),
                        source="电池网", date=dt, region="国内"))
    return out


SOURCES = [src_chinabattery, src_bjx, src_escn, src_ofweek, src_itdcw]

# ---------------------------------------------------------------- 聚类
STOP = re.compile(r"[，。！？、；：“”‘’（）()《》【】\-\—\·:：\"'%\s]")
DIGEST_PREFIX = re.compile(r"^(今日行业动态|今日招中标动态|招中标日报|储能日报|【[^】]*】|\[[^\]]*\])\s*[｜|]\s*")


def norm(title):
    t = DIGEST_PREFIX.sub("", title)
    t = STOP.sub("", t)
    return re.sub(r"\d{4}年|\d+月|\d+日", "", t)


def bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


def similar(a, b, threshold=0.52):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return min(len(na), len(nb)) >= 8
    ga, gb = bigrams(na), bigrams(nb)
    if not ga or not gb:
        return False
    return len(ga & gb) / len(ga | gb) >= threshold


CAT_RULES = [
    ("招中标", r"招标|中标|开标|报价|采购|框采|元/Wh|EPC|PC\+O|成交"),
    ("价格行情", r"价格|涨价|跌价|下调|上调|碳酸锂|六氟|电解液|元/吨|行情"),
    ("技术路线", r"固态|半固态|钠电|钠离子|构网|液流|压缩空气|飞轮|钛酸锂|材料|电芯|专利|能量密度"),
    ("政策标准", r"政策|方案|通知|征求意见|国标|标准|补贴|备案|管理办法|实施意见|税收|消费税|监管"),
    ("项目动态", r"并网|开工|投运|建成|电站|项目|验收|落地|扩容|投产"),
    ("海外市场", r"欧洲|美国|北美|印度|德国|英国|澳洲|日本|韩国|海外|出海|沙特|东南亚|非洲"),
]


def categorize(title):
    for name, pat in CAT_RULES:
        if re.search(pat, title):
            return name
    return "企业动态"


def tags_for(title, cat):
    found = []
    for kw, tag in [("半固态", "半固态"), ("固态", "固态"), ("钠", "钠电"), ("构网", "构网型"),
                    ("液流", "液流"), ("压缩空气", "压缩空气"), ("EPC", "EPC"), ("电芯", "电芯"),
                    ("碳酸锂", "碳酸锂"), ("招标", "招标"), ("中标", "中标"), ("海外", "出海"),
                    ("欧洲", "海外"), ("北美", "海外"), ("并网", "并网"), ("政策", "政策")]:
        if kw in title and tag not in found:
            found.append(tag)
    return (found or [cat])[:3]


def cluster(items):
    groups = []
    for it in sorted(items, key=lambda x: -keynum(x["date"])):
        for g in groups:
            if any(similar(m["title"], it["title"]) for m in g["members"][:6]):
                g["members"].append(it)
                if keynum(it["date"]) > keynum(g["date"]):
                    g["title"], g["url"], g["date"] = it["title"], it["url"], it["date"]
                break
        else:
            groups.append(dict(title=it["title"], url=it["url"], date=it["date"], members=[it]))
    for g in groups:
        seen = {}
        for m in g["members"]:
            seen.setdefault(m["source"], m["url"])
        g["sources"] = [dict(name=k, url=v) for k, v in seen.items()]
        g["heat"] = len(seen)
        g["category"] = categorize(g["title"])
        g["tags"] = tags_for(g["title"], g["category"])
    return groups


# ---------------------------------------------------------------- 摘要提炼
BOILER = re.compile(r"中国电池工业协会，英文名称|成立于1988|ICP证|ICP备|版权所有|关于我们|会员服务|"
                    r"广告服务|网站地图|免责声明|投稿邮箱|扫码关注|未经授权")
CLEAN_SITE = re.compile(r"【[^】]{1,14}】|（[^）]{0,10}(?:讯|报道)）|\([^)]{0,10}(?:讯|报道)\)")
CLEAN_PREFIX = re.compile(r"^(?:原标题|来源|编辑|责任编辑|记者|通讯员|文|图|作者)\s*[：:][^，。]{0,20}")
CLEAN_TAIL = re.compile(r"[（(]?\s*(?:责任编辑|编辑|来源|作者)\s*[：:]?\s*[^。]{0,24}$")
CLEAN_LEAD = re.compile(r"^[（\[【][^）\]】]{0,24}[）\]】]")
UNITS = re.compile(
    r"\d+(?:\.\d+)?\s*(?:元/Wh|元/GWh|元/吨|元/千瓦时|元/kWh|万元/吨|万元|亿元|"
    r"GWh|MWh|MW|GW|kWh|个百分点|%|倍|万台|万辆|万吨)")
ACTION = re.compile("中标|招标|开标|签约|开工|并网|投运|投产|下线|发布|出台|征求意见|"
                    "上涨|下跌|跌破|突破|扩容|交付|获批|落地|装车|量产")
NOISE = re.compile(r"记者|专访|演讲|致辞|表示|认为|指出|据透露|编辑整理|小编")


def _clean_sent(s):
    s = clean(s)
    s = CLEAN_SITE.sub("", s)
    s = CLEAN_LEAD.sub("", s)
    s = CLEAN_PREFIX.sub("", s)
    s = CLEAN_TAIL.sub("", s)
    s = re.sub(r"^(?:北极星储能网|中国储能网|电池网|OFweek\s*锂电网|锂电网|中国电池工业协会)"
               r"\s*(?:讯|消息|报道|电|新闻)", "", s)
    return s.strip(" ，、·:：-")


def _split_sents(text):
    text = re.sub(r"\s+", "", re.sub(r"<[^>]+>", " ", text))
    out = []
    for p in re.split(r"[。！？!?；;]", text):
        s = _clean_sent(p)
        if 12 <= len(s) and "\ufffd" not in s:
            out.append(s)
    return out


def _score_sent(s):
    sc = 3 if 20 <= len(s) <= 90 else (1 if len(s) > 90 else -1)
    sc += min(len(UNITS.findall(s)), 2) * 2
    if ACTION.search(s):
        sc += 2
    if RELEVANT.search(s):
        sc += 1
    if NOISE.search(s):
        sc -= 2
    return sc


def _trim(s, limit):
    s = s.strip(" ，、；")
    if len(s) <= limit:
        return s
    cut = s[:limit]
    pos = max(cut.rfind("，"), cut.rfind("、"), cut.rfind("；"))
    if pos >= 12:
        cut = cut[:pos]
    return cut.rstrip("，、；") + "…"


def _blocks(h):
    out = [clean(m) for m in re.findall(
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+'
        r'content=["\']([^"\']{20,})', h, re.I)]
    for m in re.finditer(
            r'<(?:div|article|section)[^>]*(?:class|id)=["\'][^"\']*'
            r'(?:content|article|detail|txt|zoom|TRS|body|main)[^"\']*["\'][^>]*>(.*?)'
            r'</(?:div|article|section)>', h, re.S | re.I):
        ps = re.findall(r"<p[^>]*>(.*?)</p>", m.group(1), re.S) or [m.group(1)]
        out.extend(clean(p) for p in ps[:8])
    if sum(1 for b in out if len(b) >= 40) < 3:
        out.extend(clean(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", h, re.S)[:12])
    return [b for b in out if len(b) >= 30 and not BOILER.search(b)]


def digest(url):
    """返回 {'summary': 1-2 句提炼, 'points': 2-3 条关键信息}"""
    h = ""
    for attempt in range(2):
        try:
            h = fetch(url, timeout=18)
            break
        except Exception:
            if attempt:
                return dict(summary="", points=[])
            time.sleep(1.5)
    sents, seen = [], set()
    for b in _blocks(h):
        for s in _split_sents(b):
            k = norm(s)[:34]
            if k in seen:
                continue
            seen.add(k)
            sents.append(s)
    sents = [s for s in sents if len(s) >= 16 and not BOILER.search(s)]
    if not sents:
        return dict(summary="", points=[])
    ranked = sorted(sents, key=_score_sent, reverse=True)
    fit = [s for s in ranked if len(s) <= 96]
    best = fit[0] if fit else ranked[0]
    summary = best.strip("。")
    for s in ranked[1:]:
        if len(summary) >= 52:
            break
        if norm(s)[:12] != norm(best)[:12]:
            add = _trim(s, 48)
            if add:
                summary += "。" + add
                break
    summary = re.sub(r"…+$", "", summary).rstrip("，、；。") + "。"
    points = []
    for s in ranked:
        if len(points) >= 3:
            break
        if not (UNITS.search(s) or ACTION.search(s)):
            continue
        p = _trim(s, 36).rstrip("。")
        if p and p not in points:
            points.append(p)
    return dict(summary=summary, points=points)


# ---------------------------------------------------------------- 历史与归档
def load_prev(today_str):
    try:
        files = sorted(os.listdir(HIST_DIR))
    except Exception:
        return {}
    prev = {}
    for f in files:
        if not f.endswith(".json") or f.startswith(today_str):
            continue
        try:
            with open(os.path.join(HIST_DIR, f), encoding="utf-8") as fp:
                rows = json.load(fp)
            for r in rows:
                prev[r["title"]] = r["heat"]
        except Exception:
            continue
    return prev


def save_history(today_str, groups):
    os.makedirs(HIST_DIR, exist_ok=True)
    rows = []
    for g in groups[:150]:
        sm = (g.get("digest") or {}).get("summary", "")
        rows.append(dict(title=g["title"], heat=g["heat"], category=g["category"],
                         sources=[s["name"] for s in g["sources"]], summary=sm[:70],
                         date=g["date"].strftime("%Y-%m-%d") if g.get("date") else today_str))
    with open(os.path.join(HIST_DIR, today_str + ".json"), "w", encoding="utf-8") as fp:
        json.dump(rows, fp, ensure_ascii=False, indent=1)
    files = sorted(f for f in os.listdir(HIST_DIR) if f.endswith(".json"))
    for f in files[:-90]:
        try:
            os.remove(os.path.join(HIST_DIR, f))
        except Exception:
            pass


def _write_daily_js(key, obj):
    os.makedirs(DAILY_DIR, exist_ok=True)
    with open(os.path.join(DAILY_DIR, key + ".js"), "w", encoding="utf-8") as fp:
        fp.write("window.BATTERY_DAILY = window.BATTERY_DAILY || {};\n")
        fp.write("window.BATTERY_DAILY[" + json.dumps(key) + "] = "
                 + json.dumps(obj, ensure_ascii=False, indent=1) + ";\n")


def save_daily_file(payload, today):
    key = payload["date"]
    obj = dict(key=key, type="day",
               label=f"{today.month}月{today.day}日 · 周{WEEK_CN[today.weekday()]}",
               dateCN=payload["dateCN"], weekday=payload["weekday"], issue=payload["issue"],
               updatedAt=payload["updatedAt"], stats=payload["stats"],
               categories=payload["categories"], daily=payload["daily"])
    _write_daily_js(key, obj)
    files = sorted(f for f in os.listdir(DAILY_DIR) if re.match(r"^\d{4}-\d{2}-\d{2}\.js$", f))
    for f in files[:-120]:
        try:
            os.remove(os.path.join(DAILY_DIR, f))
        except Exception:
            pass


def _history_rows(prefix):
    rows = []
    try:
        files = sorted(f for f in os.listdir(HIST_DIR) if f.endswith(".json"))
    except Exception:
        return rows
    for f in files:
        if not f.startswith(prefix):
            continue
        try:
            with open(os.path.join(HIST_DIR, f), encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception:
            continue
        for r in data:
            if r.get("title"):
                r["_day"] = f[:-5]
                rows.append(r)
    return rows


def _merge_period(rows):
    merged = {}
    for r in rows:
        k = norm(r["title"])[:44]
        if not k:
            continue
        m = merged.get(k)
        if m is None:
            merged[k] = dict(title=r["title"], category=r.get("category") or categorize(r["title"]),
                             days={r["_day"]}, heat=r.get("heat", 1),
                             sources=list(r.get("sources") or []), summary=r.get("summary", ""))
        else:
            m["days"].add(r["_day"])
            m["heat"] = max(m["heat"], r.get("heat", 1))
            if len(r["title"]) > len(m["title"]):
                m["title"] = r["title"]
            if not m["summary"] and r.get("summary"):
                m["summary"] = r["summary"]
            for s in (r.get("sources") or []):
                if s not in m["sources"]:
                    m["sources"].append(s)
    ev = list(merged.values())
    ev.sort(key=lambda x: (len(x["days"]) * 60 + x["heat"]), reverse=True)
    return ev


CAT_TITLES = {
    "招中标": "招中标：价格与规模坐标",
    "价格行情": "价格行情：成本曲线",
    "项目动态": "项目动态：开工、并网与投运",
    "技术路线": "技术路线：半固态、钠电与构网",
    "政策标准": "政策与标准：合规边界",
    "海外市场": "海外市场：出海与本地化",
    "企业动态": "企业动态：产能、资本与人事",
}
CAT_ORDER = ["招中标", "价格行情", "项目动态", "技术路线", "政策标准", "海外市场", "企业动态"]


def build_period(prefix, kind, title, word):
    rows = _history_rows(prefix)
    if len(rows) < 3:
        return None
    ev = _merge_period(rows)
    day_count = len({r["_day"] for r in rows})
    sections = []
    for cat in CAT_ORDER:
        subset = [e for e in ev if e["category"] == cat][:5]
        if not subset:
            continue
        paras = []
        for e in subset:
            first = min(e["days"])[5:].replace("-", "/")
            body = f"{e['title']}（首次 {first}，覆盖 {len(e['days'])} 期 / {len(e['sources']) or 1} 源）"
            if e["summary"]:
                body += f" — {e['summary']}"
            paras.append(body)
        sections.append(dict(title=f"{word}｜{CAT_TITLES[cat]}", paras=paras, category=cat))

    tables = []
    multi = [[e["title"][:46], str(len(e["days"])), str(e["heat"]),
              " / ".join(e["sources"][:2])] for e in ev[:8]]
    if multi:
        tables.append(dict(caption="多期持续热点（按覆盖期数排序）",
                           head=["事件", "覆盖期数", "峰值信源数", "主要信源"], rows=multi))
    price_rows = []
    for e in ev:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(万元/吨|元/吨|元/Wh|元/GWh)", e["title"])
        if m and re.search(r"价格|涨|跌|下调|上调|突破|失守|报价", e["title"]):
            price_rows.append([e["title"][:46], m.group(0), " / ".join(e["sources"][:3])])
    if price_rows:
        tables.append(dict(caption="价格信号（按事件标题抽取）", head=["事件", "数值", "信源"],
                           rows=price_rows[:8]))

    cat_counts = {}
    for e in ev:
        cat_counts[e["category"]] = cat_counts.get(e["category"], 0) + 1
    dek = (f"{title}：共 {day_count} 期日报、{len(rows)} 条记录，合并为 {len(ev)} 起事件；"
           f"其中被 2 个及以上信源报道的 {len([e for e in ev if e['heat'] >= 2])} 起。"
           f"排序按“覆盖期数 → 峰值信源数”，可看出整个周期里反复出现的主线。")
    return dict(key=prefix, type=kind, label=title, dateCN=title, weekday="", issue="已归档",
                updatedAt=TODAY.strftime("%Y-%m-%d %H:%M"),
                stats=[dict(n=str(day_count), l="覆盖期数"), dict(n=str(len(ev)), l="合并事件"),
                       dict(n=str(len(rows)), l="记录条数")],
                categories=[dict(name=k, count=v) for k, v in
                            sorted(cat_counts.items(), key=lambda kv: -kv[1])],
                daily=dict(title=title, dek=dek, sections=sections, tables=tables,
                           end="本报告由采集管线按历史快照自动汇总"))


def archive_index(today):
    try:
        names = sorted(f[:-3] for f in os.listdir(DAILY_DIR) if f.endswith(".js"))
    except Exception:
        names = []
    days, months, years = [], [], []
    for k in names:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", k):
            d = datetime.datetime.strptime(k, "%Y-%m-%d")
            label = f"{d.month}月{d.day}日 · 周{WEEK_CN[d.weekday()]}"
            days.append(dict(key=k, type="day",
                             label=(f"{d.year}年{label}" if d.year != today.year else label)))
        elif re.match(r"^\d{4}-\d{2}$", k):
            y, mo = k.split("-")
            cur = (int(y), int(mo)) == (today.year, today.month)
            months.append(dict(key=k, type="month",
                               label=f"{y}年{int(mo)}月" + ("（当期）" if cur else "")))
        elif re.match(r"^\d{4}$", k):
            years.append(dict(key=k, type="year", label=f"{k} 年度"))
    days.sort(key=lambda x: x["key"], reverse=True)
    months.sort(key=lambda x: x["key"], reverse=True)
    years.sort(key=lambda x: x["key"], reverse=True)
    return days[:30] + months + years


# ---------------------------------------------------------------- 近 7 天热度
def _hist_by_day():
    out = {}
    try:
        files = sorted(f for f in os.listdir(HIST_DIR) if f.endswith(".json"))
    except Exception:
        return out
    for f in files:
        try:
            with open(os.path.join(HIST_DIR, f), encoding="utf-8") as fp:
                rows = json.load(fp)
        except Exception:
            continue
        d = {}
        for r in rows:
            k = norm(r.get("title", ""))[:40]
            if k:
                d[k] = max(d.get(k, 0), r.get("heat", 1))
        out[f[:-5]] = d
    return out


def trend_series(g, hist, today, days=7):
    """该事件最近 N 天每天被多少个信源报道；没有出现的日子给 null"""
    key = norm(g["title"])[:40]
    tstr = today.strftime("%Y-%m-%d")
    pts = []
    for off in range(days - 1, -1, -1):
        day = (today - datetime.timedelta(days=off)).strftime("%Y-%m-%d")
        h = g["heat"] if day == tstr else hist.get(day, {}).get(key)
        pts.append(dict(d=day[5:], h=h))
    return pts


# ---------------------------------------------------------------- AI 评分
AI_SYS = (
    "你是储能与电池行业的资深分析师。基于每条信息的标题、摘要、报道信源与品类，给出三项判断：\n"
    "1) score：0-100 分，衡量信息成色——事实密度（有没有具体数字、时间、主体）、影响面、可核对性；"
    "纯标题党、厂商通稿、营销软文、旧闻重发要显著压低（40 分以下）。\n"
    "2) importance：一句话说明这条对该领域的重要性，25 字以内，不要复述标题。\n"
    "3) caveats：0-3 条「这篇需要留个心眼」的地方，例如“疑似厂商通稿”“单一信源未获交叉印证”"
    "“数据口径未说明”“概念先行、无落地证据”“旧闻重发”“标题放大结论”。没有问题时给空数组。\n"
    "只输出 JSON 对象：{\"items\":[{\"id\":\"p1\",\"score\":72,\"importance\":\"...\",\"caveats\":[\"...\"]}]}，不要任何解释文字。"
)


def ai_score(entries):
    key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if not key or not entries:
        print("[ai] 未配置 DEEPSEEK_API_KEY，跳过 AI 评分")
        return {}
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": AI_SYS},
                     {"role": "user", "content": json.dumps(entries, ensure_ascii=False)}],
        "temperature": 0.2,
        "max_tokens": 1600,
        "response_format": {"type": "json_object"},
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read().decode("utf-8", "ignore"))
        data = json.loads(resp["choices"][0]["message"]["content"])
        items = data.get("items") or data.get("data") or []
        out = {}
        for it in items:
            if not isinstance(it, dict) or "id" not in it:
                continue
            out[str(it["id"])] = dict(score=int(it.get("score", 0) or 0),
                                      importance=str(it.get("importance", "") or ""),
                                      caveats=[str(c) for c in (it.get("caveats") or [])][:3])
        usage = resp.get("usage") or {}
        print(f"[ai] scored={len(out)} tokens={usage.get('total_tokens')}")
        return out
    except Exception as e:
        print(f"[ai] 评分失败：{e!r}")
        return {}


# ---------------------------------------------------------------- 日报排版
CAT_LABELS = {
    "招中标": "招中标：价格与规模的最新坐标",
    "价格行情": "价格行情：材料与系统的成本曲线",
    "项目动态": "项目动态：开工、并网与投运",
    "技术路线": "技术路线：从半固态到钠电",
    "政策标准": "政策与标准：合规边界在收紧",
    "海外市场": "海外市场：出海与本地化",
    "企业动态": "企业动态：产能、资本与人事",
}


def join_sources(g):
    return " / ".join(s["name"] for s in g["sources"])


def build_daily(groups, total, src_count, today):
    sections = []
    for cat in CAT_ORDER:
        rows = [g for g in groups if g["category"] == cat][:4]
        if not rows:
            continue
        paras = []
        for g in rows:
            body = f"{g['title']}（{mmdd(g['date'])}，{join_sources(g)}）"
            s = g.get("summary", "")
            if s:
                body += f" — {s}"
            paras.append(body)
        sections.append(dict(title=CAT_LABELS[cat], paras=paras, category=cat))

    tender_rows, price_rows = [], []
    for g in groups:
        t = g["title"]
        scale = re.search(r"(\d+(?:\.\d+)?)\s*(GWh|MWh|MW)/(\d+(?:\.\d+)?)\s*(GWh|MWh|MW)", t) \
            or re.search(r"(\d+(?:\.\d+)?)\s*(GWh|MWh)", t)
        money = re.search(r"(\d+\.\d+)\s*元/Wh", t)
        if money and re.search("招标|中标|开标|报价", t):
            tender_rows.append([t[:46], scale.group(0) if scale else "—", money.group(0),
                                join_sources(g)])
        m = re.search(r"(\d+(?:\.\d+)?)\s*(万元/吨|元/吨|元/Wh|元/GWh)", t)
        if m and re.search(r"价格|涨|跌|下调|上调|突破|失守", t):
            price_rows.append([t[:46], m.group(0), join_sources(g)])

    tables = []
    if tender_rows:
        tables.append(dict(caption="招中标价格速览（自动抽取）",
                           head=["事件", "规模", "单价", "信源"], rows=tender_rows[:8]))
    if price_rows:
        tables.append(dict(caption="价格信号（自动抽取）",
                           head=["事件", "数值", "信源"], rows=price_rows[:6]))

    dek = (f"{today.strftime('%m月%d日')}自动汇总：共 {total} 条信息、{len(groups)} 起事件，"
           f"其中招中标类 {len([g for g in groups if g['category'] == '招中标'])} 条、"
           f"价格类 {len([g for g in groups if g['category'] == '价格行情'])} 条、"
           f"技术路线类 {len([g for g in groups if g['category'] == '技术路线'])} 条。"
           f"以下按品类排列，每条标注报道机构，供交叉核对。")
    return dict(title="储能与电池行业日报", dek=dek, sections=sections, tables=tables,
                end="本期日报由采集管线自动生成")


def _headline(groups):
    if not groups:
        return "今日储能与电池情报"
    t = re.sub(r"^[\d.]+\s*元/Wh[！!]?\s*", "", groups[0]["title"].strip())
    return t[:33].rstrip("，、·") + "…" if len(t) > 34 else t


def pick_lead(groups, total, src_count):
    names = "；".join(g["title"] for g in groups[:3])
    return (f"本期从 {src_count} 个垂直信源聚合 {total} 条信息，去重聚类后得到 {len(groups)} 起事件。"
            f"多源共同报道的前三起是：{names}。"
            f"热度按独立信源报道数计算，同一件事被越多机构报道，排名越靠前。")


# ---------------------------------------------------------------- 主流程
def main():
    items, ok_sources = [], []
    for fn in SOURCES:
        try:
            got = fn()
            got = [x for x in got if len(x["title"]) >= 8 and RELEVANT.search(x["title"])][:80]
            if got:
                ok_sources.append(len(got))
                items.extend(got)
                print(f"[ok] {fn.__name__}: {len(got)}")
            else:
                print(f"[empty] {fn.__name__}")
        except Exception as e:
            print(f"[fail] {fn.__name__}: {e!r}")

    seen, uniq = set(), []
    for it in items:
        k = (it["title"], it["source"])
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    print(f"raw={len(items)} uniq={len(uniq)} sources={len(ok_sources)}")
    if len(uniq) < 8:
        print("抓取数量不足，保留上一版数据，未覆盖 news.js")
        return 0

    groups = cluster(uniq)
    today_nd = TODAY.replace(tzinfo=None)
    importance = re.compile(r"宁德时代|亿纬|比亚迪|远景|阳光电源|海博思创|中车|华为|特斯拉|"
                            r"固态|半固态|钠|构网|液流|税收|消费税|实施方案|中标|开标|0\.\d+元/Wh")

    def score(g):
        kw = 6 if importance.search(g["title"]) else 0
        days = (today_nd - g["date"]).days if g["date"] else 30
        fresh = 10 if days <= 2 else 6 if days <= 5 else 2 if days <= 10 else 0
        return g["heat"] * 100 + kw + fresh

    groups.sort(key=score, reverse=True)
    for g in groups[:26]:
        try:
            g["digest"] = digest(g["url"])
        except Exception:
            g["digest"] = dict(summary="", points=[])
        g["summary"] = g["digest"]["summary"]
        time.sleep(0.35)

    today = TODAY.replace(tzinfo=None)
    today_str = today.strftime("%Y-%m-%d")
    prev = load_prev(today_str)
    hist = _hist_by_day()
    for g in groups[:30]:
        g["trend"] = trend_series(g, hist, today)

    def trend_of(g):
        p = prev.get(g["title"])
        if p is None or g["heat"] > p:
            return "up"
        return "down" if g["heat"] < p else "flat"

    picked, cat_used = [], {}
    for g in groups:
        if cat_used.get(g["category"], 0) >= 2 or not g.get("summary"):
            continue
        cat_used[g["category"]] = cat_used.get(g["category"], 0) + 1
        picked.append(g)
        if len(picked) >= 8:
            break
    if len(picked) < 4:
        picked = groups[:8]

    picked_out = []
    for i, g in enumerate(picked, 1):
        picked_out.append(dict(
            id=f"p{i}", kicker=g["category"], title=g["title"],
            summary=g["summary"] or "该条仅有标题级信息，正文摘要待补，请点开来源核对原文。",
            points=(g.get("digest") or {}).get("points", []), heat=str(g["heat"]), time=mmdd(g["date"]),
            tags=g["tags"], sources=g["sources"], trend=g.get("trend"),
            why=f"本期由 {g['heat']} 个独立信源报道" + (
                "，属跨平台高频事件，建议结合多家原文交叉核对。" if g["heat"] >= 2
                else "，为单一信源首发，引用前请核对原文口径。")))

    hot, src_used, ranked = [], {}, []
    for g in groups:
        prim = g["sources"][0]["name"] if g["sources"] else "?"
        if src_used.get(prim, 0) >= 4:
            continue
        src_used[prim] = src_used.get(prim, 0) + 1
        ranked.append(g)
        if len(ranked) >= 15:
            break
    for i, g in enumerate(ranked, 1):
        hot.append(dict(id=f"h{i}", rank=i, title=g["title"], category=g["category"], heat=g["heat"],
                        trend=trend_of(g), series=g.get("trend"), time=mmdd(g["date"]),
                        isNew=(g["title"] not in prev), sources=g["sources"],
                        summary=g.get("summary") or "",
                        points=(g.get("digest") or {}).get("points", [])))

    entries = []
    for p in picked_out:
        entries.append(dict(id=p["id"], title=p["title"], summary=p["summary"][:90],
                            category=p["kicker"], sources=[s["name"] for s in p["sources"]]))
    for h in hot:
        entries.append(dict(id=h["id"], title=h["title"], summary=(h["summary"] or "")[:90],
                            category=h["category"], sources=[s["name"] for s in h["sources"]]))
    scores = ai_score(entries)
    for p in picked_out + hot:
        a = scores.get(p["id"])
        if a:
            p["score"] = a["score"]
            p["importance"] = a["importance"]
            p["caveats"] = a["caveats"]

    cat_counts = {}
    for g in groups:
        cat_counts[g["category"]] = cat_counts.get(g["category"], 0) + 1
    payload = dict(
        date=today_str, dateCN=f"{today.year}年{today.month}月{today.day}日",
        weekday="星期" + WEEK_CN[today.weekday()], updatedAt=TODAY.strftime("%Y-%m-%d %H:%M"),
        issue="每日更新", headline=_headline(groups),
        lead=pick_lead(groups, len(uniq), len(ok_sources)),
        stats=[dict(n=str(len(uniq)), l="本期收录"), dict(n=str(len(ok_sources)), l="覆盖信源"),
               dict(n=str(len(groups)), l="去重事件")],
        prices=[], categories=[dict(name=k, count=v) for k, v in
                               sorted(cat_counts.items(), key=lambda kv: -kv[1])],
        picked=picked_out, hot=hot,
        daily=build_daily(groups, len(uniq), len(ok_sources), today))

    ed_path = os.path.join(DATA_DIR, "editorial.json")
    if os.path.exists(ed_path):
        try:
            with open(ed_path, encoding="utf-8") as fp:
                day = json.load(fp).get(today_str)
            if day:
                for k in ("headline", "lead", "picked", "daily", "prices"):
                    if k in day:
                        payload[k] = day[k]
                print("[editorial] 已合并编辑层")
        except Exception as e:
            print("[editorial] 读取失败", e)

    save_history(today_str, groups)
    save_daily_file(payload, today)
    month = build_period(today.strftime("%Y-%m"), "month",
                         f"{today.year}年{today.month}月月报", "本月")
    if month:
        _write_daily_js(month["key"], month)
        print(f"[month] {month['key']} events={month['stats'][1]['n']}")
    year = build_period(today.strftime("%Y"), "year", f"{today.year} 年度报告", "全年")
    if year:
        _write_daily_js(year["key"], year)
        print(f"[year] {year['key']} events={year['stats'][1]['n']}")
    payload["archive"] = archive_index(today)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "news.js"), "w", encoding="utf-8") as fp:
        fp.write("/* 由 scripts/collect.py 自动生成，请勿手工编辑 */\n"
                 "window.BATTERY_NEWS = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")
    print(f"written data/news.js | picked={len(picked_out)} hot={len(hot)} "
          f"sections={len(payload['daily']['sections'])} archive={len(payload['archive'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
