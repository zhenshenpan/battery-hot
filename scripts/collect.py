# -*- coding: utf-8 -*-
"""
蓄电池热榜 · 采集管线
抓取 -> 标题聚类去重 -> 统计独立信源数 -> 抽取摘要 -> 生成 data/news.js
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

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))


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
            title, ds = m.group(1).strip(), m.group(2)
            if len(title) < 8:
                continue
            try:
                dt = datetime.datetime.strptime(ds, "%Y-%m-%d")
            except Exception:
                dt = None
            out.append(dict(title=title, url=abs_url(base, href), source="中国电池工业协会",
                            date=dt, region="国内"))
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
            if not (14 <= len(t) <= 70):
                continue
            if "news.bjx.com.cn/html/" not in href:
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
        t = text_of(txt)
        t = t.lstrip("●· ").strip()
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
        if not (14 <= len(t) <= 70) or "/news/" not in href:
            continue
        if t.startswith("-->"):
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

STOP = re.compile(r"[，。！？、；：“”‘’（）()《》【】\-\—\·:：\"'%\s]")
DIGEST_PREFIX = re.compile(r"^(今日行业动态|今日招中标动态|招中标日报|储能日报|【[^】]*】|\[[^\]]*\])\s*[｜|]\s*")


def norm(title):
    t = DIGEST_PREFIX.sub("", title)
    t = STOP.sub("", t)
    t = re.sub(r"\d{4}年|\d+月|\d+日", "", t)
    return t


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
    j = len(ga & gb) / len(ga | gb)
    return j >= threshold


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
    for kw, tag in [
        ("半固态", "半固态"), ("固态", "固态"), ("钠", "钠电"), ("构网", "构网型"),
        ("液流", "液流"), ("压缩空气", "压缩空气"), ("EPC", "EPC"), ("电芯", "电芯"),
        ("碳酸锂", "碳酸锂"), ("招标", "招标"), ("中标", "中标"), ("海外", "出海"),
        ("欧洲", "海外"), ("北美", "海外"), ("并网", "并网"), ("政策", "政策"),
    ]:
        if kw in title and tag not in found:
            found.append(tag)
    if not found:
        found = [cat]
    return found[:3]


BOILER = re.compile(r"中国电池工业协会，英文名称|成立于1988|ICP证|ICP备|版权所有|关于我们|会员服务|"
                    r"广告服务|网站地图|免责声明|投稿邮箱|扫码关注|未经授权")


def _good(s):
    return len(s) >= 40 and not BOILER.search(s) and not re.search(r"许可证|公网安备", s)


def extract_summary(url, limit=120):
    try:
        h = fetch(url, timeout=15)
    except Exception:
        return ""
    for pat in (r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{20,})',
                r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']{20,})'):
        m = re.search(pat, h, re.I)
        if m:
            s = clean(m.group(1))
            if _good(s):
                return s[:limit]
    for p in re.findall(r"<p[^>]*>(.*?)</p>", h, re.S):
        s = clean(p)
        if _good(s):
            return s[:limit]
    return ""


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
    rows = [dict(title=g["title"], heat=g["heat"]) for g in groups]
    with open(os.path.join(HIST_DIR, today_str + ".json"), "w", encoding="utf-8") as fp:
        json.dump(rows, fp, ensure_ascii=False, indent=1)
    files = sorted(f for f in os.listdir(HIST_DIR) if f.endswith(".json"))
    for f in files[:-90]:
        try:
            os.remove(os.path.join(HIST_DIR, f))
        except Exception:
            pass


def join_sources(gs):
    return " / ".join(s["name"] for s in gs["sources"])


def _headline(groups):
    if not groups:
        return "今日储能与电池情报"
    t = groups[0]["title"].strip()
    t = re.sub(r"^[\d.]+\s*元/Wh[！!]?\s*", "", t)
    if len(t) > 34:
        t = t[:33].rstrip("，、·") + "…"
    return t


def pick_lead(groups, total, src_count):
    names = "；".join(g["title"] for g in groups[:3])
    return (f"本期从 {src_count} 个垂直信源聚合 {total} 条信息，去重聚类后得到 {len(groups)} 起事件。"
            f"多源共同报道的前三起是：{names}。"
            f"热度按独立信源报道数计算，同一件事被越多机构报道，排名越靠前。")


def build_daily(groups, total, src_count, today):
    sections = []
    order = ["招中标", "价格行情", "项目动态", "技术路线", "政策标准", "海外市场", "企业动态"]
    labels = {
        "招中标": "招中标：价格与规模的最新坐标",
        "价格行情": "价格行情：材料与系统的成本曲线",
        "项目动态": "项目动态：开工、并网与投运",
        "技术路线": "技术路线：从半固态到钠电",
        "政策标准": "政策与标准：合规边界在收紧",
        "海外市场": "海外市场：出海与本地化",
        "企业动态": "企业动态：产能、资本与人事",
    }
    for cat in order:
        rows = [g for g in groups if g["category"] == cat][:4]
        if not rows:
            continue
        paras = []
        for g in rows:
            s = g.get("summary", "")
            body = f"{g['title']}（{mmdd(g['date'])}，{join_sources(g)}）"
            if s:
                body += f" — {s}"
            paras.append(body)
        sections.append(dict(title=labels[cat], paras=paras, category=cat))

    tender_rows, price_rows = [], []
    for g in groups:
        t = g["title"]
        scale = re.search(r"(\d+(?:\.\d+)?)\s*(GWh|MWh|MW)/(\d+(?:\.\d+)?)\s*(GWh|MWh|MW)", t)
        if not scale:
            scale = re.search(r"(\d+(?:\.\d+)?)\s*(GWh|MWh)", t)
        money = re.search(r"(\d+\.\d+)\s*元/Wh", t)
        if money and ("招标" in t or "中标" in t or "开标" in t or "报价" in t):
            tender_rows.append([t[:46], (scale.group(0) if scale else "—"),
                                money.group(0), join_sources(g)])
    for g in groups:
        t = g["title"]
        m = re.search(r"(\d+(?:\.\d+)?)\s*(万元/吨|元/吨|元/Wh|元/GWh)", t)
        if m and re.search(r"价格|涨|跌|下调|上调|突破|失守", t):
            price_rows.append([t[:46], m.group(0), join_sources(g)])

    tables = []
    if tender_rows:
        tables.append(dict(caption="招中标价格速览（自动抽取）",
                           head=["事件", "规模", "单价", "信源"],
                           rows=tender_rows[:8]))
    if price_rows:
        tables.append(dict(caption="价格信号（自动抽取）",
                           head=["事件", "数值", "信源"],
                           rows=price_rows[:6]))

    dek = (f"{today.strftime('%m月%d日')}自动汇总：共 {total} 条信息、{len(groups)} 起事件，"
           f"其中招中标类 {len([g for g in groups if g['category'] == '招中标'])} 条、"
           f"价格类 {len([g for g in groups if g['category'] == '价格行情'])} 条、"
           f"技术路线类 {len([g for g in groups if g['category'] == '技术路线'])} 条。"
           f"以下按品类排列，每条标注报道机构，供交叉核对。")

    return dict(title="储能与电池行业日报", dek=dek, sections=sections, tables=tables,
                end="本期日报由采集管线自动生成")


RELEVANT = re.compile(
    r"储能|电池|锂电|锂电池|钠电|钠离子|固态|半固态|电芯|正极|负极|电解液|隔膜|碳酸锂|六氟|"
    r"磷酸铁锂|三元|换电|充电桩|BMS|PACK|电堆|氢燃料|构网|微电网|虚拟电厂|风光储|"
    r"并网|招标|中标|EPC|MWh|GWh|MW/|度电|PCS|逆变器|回收|梯次"
)


def is_relevant(title):
    return bool(RELEVANT.search(title))


def main():
    items, ok_sources = [], []
    for fn in SOURCES:
        try:
            got = fn()
            got = [x for x in got if len(x["title"]) >= 8 and is_relevant(x["title"])]
            got = got[:80]
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
        if k in seen:
            continue
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

    for g in groups[:16]:
        try:
            g["summary"] = extract_summary(g["url"])
        except Exception:
            g["summary"] = ""
        time.sleep(0.4)

    today = TODAY.replace(tzinfo=None)
    today_str = today.strftime("%Y-%m-%d")
    prev = load_prev(today_str)

    def trend_of(g):
        p = prev.get(g["title"])
        if p is None:
            return "up"
        if g["heat"] > p:
            return "up"
        if g["heat"] < p:
            return "down"
        return "flat"

    picked, cat_used = [], {}
    for g in groups:
        if cat_used.get(g["category"], 0) >= 2:
            continue
        if not g.get("summary"):
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
            id=f"p{i}",
            kicker=g["category"],
            title=g["title"],
            summary=g.get("summary") or "点击查看原文与报道来源。",
            heat=str(g["heat"]),
            time=mmdd(g["date"]),
            tags=g["tags"],
            sources=g["sources"],
            why=f"本期由 {g['heat']} 个独立信源报道" + (
                "，属跨平台高频事件，建议结合多家原文交叉核对。" if g["heat"] >= 2
                else "，为单一信源首发，引用前请核对原文口径。"),
        ))

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
        hot.append(dict(rank=i, title=g["title"], category=g["category"], heat=g["heat"],
                        trend=trend_of(g), time=mmdd(g["date"]), isNew=(g["title"] not in prev),
                        sources=g["sources"], summary=g.get("summary") or ""))

    cat_counts = {}
    for g in groups:
        cat_counts[g["category"]] = cat_counts.get(g["category"], 0) + 1
    cats = sorted(cat_counts.items(), key=lambda kv: -kv[1])

    payload = dict(
        date=today_str,
        dateCN=f"{today.year}年{today.month}月{today.day}日",
        weekday="星期" + "一二三四五六日"[today.weekday()],
        updatedAt=TODAY.strftime("%Y-%m-%d %H:%M"),
        issue="每日更新",
        headline=_headline(groups),
        lead=pick_lead(groups, len(uniq), len(ok_sources)),
        stats=[dict(n=str(len(uniq)), l="本期收录"),
               dict(n=str(len(ok_sources)), l="覆盖信源"),
               dict(n=str(len(groups)), l="去重事件")],
        prices=[],
        categories=[dict(name=k, count=v) for k, v in cats],
        picked=picked_out,
        hot=hot,
        daily=build_daily(groups, len(uniq), len(ok_sources), today),
    )

    ed_path = os.path.join(DATA_DIR, "editorial.json")
    if os.path.exists(ed_path):
        try:
            with open(ed_path, encoding="utf-8") as fp:
                ed = json.load(fp)
            day = ed.get(today_str)
            if day:
                for k in ("headline", "lead", "picked", "daily", "prices"):
                    if k in day:
                        payload[k] = day[k]
                print("[editorial] 已合并编辑层")
        except Exception as e:
            print("[editorial] 读取失败", e)

    js = ("/* 由 scripts/collect.py 自动生成，请勿手工编辑 */\n"
          "window.BATTERY_NEWS = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "news.js"), "w", encoding="utf-8") as fp:
        fp.write(js)
    save_history(today_str, groups)
    print(f"written data/news.js | picked={len(picked_out)} hot={len(hot)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
