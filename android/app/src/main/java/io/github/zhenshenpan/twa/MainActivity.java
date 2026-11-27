package io.github.zhenshenpan.twa;

import android.app.Activity;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {

    private static final String DATA_URL = "https://zhenshenpan.github.io/battery-hot/data/app.json";
    private static final String CACHE_NAME = "app-cache.json";

    private static final int C_BG = 0xFFF5F6F8;
    private static final int C_CARD = 0xFFFFFFFF;
    private static final int C_TEXT = 0xFF18212A;
    private static final int C_SUB = 0xFF6B7784;
    private static final int C_LINE = 0xFFE7EAEE;
    private static final int C_ACCENT = 0xFF0F9D76;
    private static final int C_ACCENT_BG = 0xFFE7F5F0;
    private static final int C_CHIP = 0xFFF1F3F5;

    private LinearLayout body;
    private TextView dateTv;
    private TextView[] tabs = new TextView[3];

    private JSONObject data;
    private String tab = "picked";
    private String dailyKey = "";
    private boolean loading = false;

    private final Handler ui = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildShell();
        paintTabs();
        body.addView(plainCard("正在更新…"));
        loadData();
    }

    /* ---------------- 基础工具 ---------------- */

    private int dp(float v) {
        return (int) (TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v,
                getResources().getDisplayMetrics()) + 0.5f);
    }

    private GradientDrawable round(int color, int radiusDp, int strokeDp, int strokeColor) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(radiusDp));
        if (strokeDp > 0) {
            g.setStroke(dp(strokeDp), strokeColor);
        }
        return g;
    }

    private TextView text(String s, float sp, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s == null ? "" : s);
        t.setTextSize(sp);
        t.setTextColor(color);
        t.setLineSpacing(dp(2), 1.12f);
        if (bold) {
            t.setTypeface(Typeface.DEFAULT_BOLD);
        }
        return t;
    }

    private LinearLayout cardBox() {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setBackground(round(C_CARD, 14, 1, C_LINE));
        int p = dp(14);
        c.setPadding(p, p, p, p);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.leftMargin = dp(14);
        lp.rightMargin = dp(14);
        lp.topMargin = dp(6);
        lp.bottomMargin = dp(6);
        c.setLayoutParams(lp);
        return c;
    }

    private LinearLayout plainCard(String msg) {
        LinearLayout c = cardBox();
        c.addView(text(msg, 13, C_SUB, false));
        return c;
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }

    /* ---------------- 骨架 ---------------- */

    private void buildShell() {
        ScrollView sv = new ScrollView(this);
        sv.setBackgroundColor(C_BG);
        sv.setFillViewport(true);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        sv.addView(root, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.VERTICAL);
        head.setBackgroundColor(C_CARD);
        head.setPadding(dp(16), dp(14), dp(16), dp(12));
        root.addView(head, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout brandRow = new LinearLayout(this);
        brandRow.setOrientation(LinearLayout.HORIZONTAL);
        brandRow.setGravity(Gravity.CENTER_VERTICAL);
        TextView brand = text("蓄电池热榜", 19, C_TEXT, true);
        brandRow.addView(brand);
        brandRow.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        TextView refresh = text("刷新", 12, C_ACCENT, true);
        refresh.setPadding(dp(12), dp(6), dp(12), dp(6));
        refresh.setBackground(round(C_ACCENT_BG, 16, 0, 0));
        refresh.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                loadData();
            }
        });
        brandRow.addView(refresh);
        head.addView(brandRow);

        dateTv = text("每日蓄电池情报", 11.5f, C_SUB, false);
        dateTv.setPadding(0, dp(6), 0, 0);
        head.addView(dateTv);

        LinearLayout tabRow = new LinearLayout(this);
        tabRow.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        tlp.topMargin = dp(12);
        head.addView(tabRow, tlp);

        String[] names = {"精选", "热点榜", "电池日报"};
        final String[] keys = {"picked", "hot", "daily"};
        for (int i = 0; i < 3; i++) {
            TextView t = text(names[i], 13.5f, C_SUB, true);
            t.setGravity(Gravity.CENTER);
            t.setPadding(0, dp(9), 0, dp(9));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            if (i > 0) {
                lp.leftMargin = dp(8);
            }
            t.setLayoutParams(lp);
            final String k = keys[i];
            t.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    tab = k;
                    render();
                }
            });
            tabs[i] = t;
            tabRow.addView(t);
        }

        body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(0, dp(4), 0, dp(26));
        root.addView(body, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        setContentView(sv);
    }

    private void paintTabs() {
        for (int i = 0; i < 3; i++) {
            boolean active = (i == 0 && "picked".equals(tab))
                    || (i == 1 && "hot".equals(tab))
                    || (i == 2 && "daily".equals(tab));
            tabs[i].setTextColor(active ? C_ACCENT : C_SUB);
            tabs[i].setBackground(round(active ? C_ACCENT_BG : C_CARD, 10, 0, 0));
        }
    }

    /* ---------------- 数据 ---------------- */

    private void loadData() {
        if (loading) {
            return;
        }
        loading = true;
        String cached = readCache();
        if (cached != null && data == null) {
            try {
                data = new JSONObject(cached);
                render();
            } catch (Exception ignored) {
            }
        }
        new Thread(new Runnable() {
            @Override
            public void run() {
                String raw;
                try {
                    raw = http(DATA_URL + "?t=" + System.currentTimeMillis());
                    writeCache(raw);
                } catch (Exception e) {
                    raw = null;
                }
                final String fresh = raw;
                ui.post(new Runnable() {
                    @Override
                    public void run() {
                        loading = false;
                        if (fresh != null) {
                            try {
                                data = new JSONObject(fresh);
                                render();
                            } catch (Exception e) {
                                toast("数据格式异常");
                            }
                        } else if (data == null) {
                            body.removeAllViews();
                            body.addView(plainCard("连不上服务器，也没有本地缓存。检查网络后点右上角「刷新」。"));
                        } else {
                            toast("网络不通，显示上次缓存的内容");
                        }
                    }
                });
            }
        }).start();
    }

    private String http(String u) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(15000);
        conn.setRequestProperty("Accept", "application/json");
        conn.setRequestProperty("User-Agent", "BatteryHotApp/1.0.2");
        conn.setInstanceFollowRedirects(true);
        int code = conn.getResponseCode();
        if (code != 200) {
            throw new IllegalStateException("HTTP " + code);
        }
        InputStream in = conn.getInputStream();
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while ((n = in.read(buf)) > 0) {
            bo.write(buf, 0, n);
        }
        in.close();
        conn.disconnect();
        return new String(bo.toByteArray(), "UTF-8");
    }

    private void writeCache(String raw) {
        try {
            FileOutputStream out = new FileOutputStream(new File(getFilesDir(), CACHE_NAME));
            out.write(raw.getBytes("UTF-8"));
            out.close();
        } catch (Exception ignored) {
        }
    }

    private String readCache() {
        File f = new File(getFilesDir(), CACHE_NAME);
        if (!f.exists()) {
            return null;
        }
        try {
            FileInputStream in = new FileInputStream(f);
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) {
                bo.write(buf, 0, n);
            }
            in.close();
            return new String(bo.toByteArray(), "UTF-8");
        } catch (Exception e) {
            return null;
        }
    }

    /* ---------------- 渲染 ---------------- */

    private void render() {
        paintTabs();
        body.removeAllViews();
        if (data == null) {
            return;
        }
        String head = data.optString("dateCN", "") + " " + data.optString("weekday", "");
        String up = data.optString("updatedAt", "");
        dateTv.setText(head + (up.isEmpty() ? " · 每日蓄电池情报" : " · 更新 " + up));
        if ("picked".equals(tab)) {
            renderPicked();
        } else if ("hot".equals(tab)) {
            renderHot();
        } else {
            renderDaily();
        }
    }

    private void addStats(LinearLayout parent, JSONArray stats) {
        if (stats == null || stats.length() == 0) {
            return;
        }
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(dp(16), dp(10), dp(16), dp(2));
        for (int i = 0; i < stats.length() && i < 3; i++) {
            JSONObject s = stats.optJSONObject(i);
            if (s == null) {
                continue;
            }
            LinearLayout col = new LinearLayout(this);
            col.setOrientation(LinearLayout.VERTICAL);
            col.addView(text(s.optString("n"), 17, C_TEXT, true));
            col.addView(text(s.optString("l"), 10.5f, C_SUB, false));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            col.setLayoutParams(lp);
            row.addView(col);
        }
        parent.addView(row);
    }

    private void renderPicked() {
        LinearLayout hero = new LinearLayout(this);
        hero.setOrientation(LinearLayout.VERTICAL);
        hero.setPadding(dp(16), dp(14), dp(16), dp(6));
        hero.addView(text(data.optString("issue", "今日精选"), 11, C_ACCENT, true));
        TextView title = text(data.optString("headline"), 21, C_TEXT, true);
        title.setPadding(0, dp(8), 0, 0);
        title.setLineSpacing(dp(4), 1.2f);
        hero.addView(title);
        String lead = data.optString("lead", "");
        if (!lead.isEmpty()) {
            TextView lt = text(lead, 12.5f, C_SUB, false);
            lt.setPadding(0, dp(8), 0, 0);
            hero.addView(lt);
        }
        body.addView(hero);
        addStats(body, data.optJSONArray("stats"));

        JSONArray picked = data.optJSONArray("picked");
        if (picked == null) {
            return;
        }
        for (int i = 0; i < picked.length(); i++) {
            JSONObject o = picked.optJSONObject(i);
            if (o != null) {
                body.addView(newsCard(o, -1));
            }
        }
    }

    private void renderHot() {
        LinearLayout hero = new LinearLayout(this);
        hero.setOrientation(LinearLayout.VERTICAL);
        hero.setPadding(dp(16), dp(14), dp(16), dp(4));
        hero.addView(text("当前热点", 11, C_ACCENT, true));
        TextView t = text("蓄电池行业热点榜", 20, C_TEXT, true);
        t.setPadding(0, dp(6), 0, 0);
        hero.addView(t);
        JSONArray hotArr = data.optJSONArray("hot");
        hero.addView(text("按多源报道量加权，共 " + (hotArr == null ? 0 : hotArr.length()) + " 起", 11.5f, C_SUB, false));
        body.addView(hero);

        if (hotArr == null) {
            return;
        }
        for (int i = 0; i < hotArr.length(); i++) {
            JSONObject o = hotArr.optJSONObject(i);
            if (o != null) {
                body.addView(newsCard(o, i + 1));
            }
        }
    }

    private LinearLayout newsCard(final JSONObject o, int rank) {
        LinearLayout c = cardBox();

        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);

        if (rank > 0) {
            TextView r = text(String.valueOf(rank), 12, 0xFFFFFFFF, true);
            r.setGravity(Gravity.CENTER);
            r.setBackground(round(C_ACCENT, 8, 0, 0));
            LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(dp(24), dp(24));
            rlp.rightMargin = dp(8);
            top.addView(r, rlp);
        }

        String kicker = o.optString("kicker", o.optString("category", ""));
        if (!kicker.isEmpty()) {
            TextView k = text(kicker, 10.5f, C_ACCENT, true);
            k.setPadding(dp(7), dp(3), dp(7), dp(3));
            k.setBackground(round(C_ACCENT_BG, 6, 0, 0));
            LinearLayout.LayoutParams klp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            klp.rightMargin = dp(6);
            top.addView(k, klp);
        }

        int score = o.optInt("score", 0);
        if (score > 0) {
            TextView s = text("AI " + score, 10.5f, C_SUB, true);
            s.setPadding(dp(7), dp(3), dp(7), dp(3));
            s.setBackground(round(C_CHIP, 6, 0, 0));
            top.addView(s, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        }
        c.addView(top);

        TextView title = text(o.optString("title"), 17, C_TEXT, true);
        title.setPadding(0, dp(8), 0, 0);
        title.setLineSpacing(dp(3), 1.18f);
        c.addView(title);

        String summary = o.optString("summary", "");
        if (!summary.isEmpty()) {
            TextView s = text(summary, 12.5f, C_SUB, false);
            s.setPadding(0, dp(6), 0, 0);
            c.addView(s);
        }

        StringBuilder meta = new StringBuilder();
        String time = o.optString("time", "");
        if (!time.isEmpty()) {
            meta.append(time);
        }
        String heat = o.optString("heat", "");
        if (!heat.isEmpty()) {
            if (meta.length() > 0) {
                meta.append(" · ");
            }
            meta.append(heat).append(" 家信源");
        }
        JSONArray src = o.optJSONArray("sources");
        if (src != null && src.length() > 0) {
            JSONObject s0 = src.optJSONObject(0);
            String name = s0 == null ? "" : s0.optString("name", "");
            if (!name.isEmpty()) {
                if (meta.length() > 0) {
                    meta.append(" · ");
                }
                meta.append(name);
            }
        }
        if (meta.length() > 0) {
            TextView m = text(meta.toString(), 10.5f, C_SUB, false);
            m.setPadding(0, dp(8), 0, 0);
            c.addView(m);
        }

        c.setClickable(true);
        c.setForeground(new RippleDrawable(ColorStateList.valueOf(0x14000000), null, null));
        c.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Intent it = new Intent(MainActivity.this, DetailActivity.class);
                it.putExtra("item", o.toString());
                startActivity(it);
            }
        });
        return c;
    }

    private void renderDaily() {
        JSONObject daily = data.optJSONObject("daily");
        if (daily == null || daily.length() == 0) {
            body.addView(plainCard("日报还没有生成"));
            return;
        }
        JSONArray order = data.optJSONArray("dailyKeys");
        if (dailyKey.isEmpty() || !daily.has(dailyKey)) {
            dailyKey = (order != null && order.length() > 0) ? order.optString(0) : "";
        }

        HorizontalScrollView hsv = new HorizontalScrollView(this);
        hsv.setHorizontalScrollBarEnabled(false);
        LinearLayout chips = new LinearLayout(this);
        chips.setOrientation(LinearLayout.HORIZONTAL);
        chips.setPadding(dp(14), dp(10), dp(14), dp(2));
        hsv.addView(chips);
        body.addView(hsv);

        if (order != null) {
            for (int i = 0; i < order.length(); i++) {
                String k = order.optString(i);
                JSONObject d = daily.optJSONObject(k);
                if (d == null) {
                    continue;
                }
                String label = d.optString("label", k);
                boolean on = k.equals(dailyKey);
                TextView chip = text(label, 11.5f, on ? 0xFFFFFFFF : C_SUB, true);
                chip.setPadding(dp(11), dp(6), dp(11), dp(6));
                chip.setBackground(round(on ? C_ACCENT : C_CHIP, 16, 0, 0));
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                lp.rightMargin = dp(8);
                final String kk = k;
                chip.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        dailyKey = kk;
                        render();
                    }
                });
                chips.addView(chip, lp);
            }
        }

        JSONObject d = daily.optJSONObject(dailyKey);
        if (d == null) {
            return;
        }

        LinearLayout article = cardBox();
        article.addView(text(d.optString("dateCN", "") + " " + d.optString("weekday", ""), 11, C_ACCENT, true));
        TextView title = text(d.optString("title", dailyKey), 19, C_TEXT, true);
        title.setPadding(0, dp(6), 0, 0);
        title.setLineSpacing(dp(3), 1.2f);
        article.addView(title);
        String dek = d.optString("dek", "");
        if (!dek.isEmpty()) {
            TextView dt = text(dek, 11.5f, C_SUB, false);
            dt.setPadding(0, dp(6), 0, 0);
            article.addView(dt);
        }
        body.addView(article);

        JSONArray sections = d.optJSONArray("sections");
        if (sections == null) {
            return;
        }
        for (int i = 0; i < sections.length(); i++) {
            JSONObject sec = sections.optJSONObject(i);
            if (sec == null) {
                continue;
            }
            LinearLayout c = cardBox();
            c.addView(text(sec.optString("title"), 14, C_TEXT, true));
            JSONArray paras = sec.optJSONArray("paras");
            if (paras != null) {
                for (int j = 0; j < paras.length(); j++) {
                    String p = paras.optString(j);
                    if (p == null || p.isEmpty()) {
                        continue;
                    }
                    TextView pt = text(p, 12.5f, 0xFF3C4650, false);
                    pt.setPadding(0, dp(8), 0, 0);
                    pt.setLineSpacing(dp(3), 1.35f);
                    c.addView(pt);
                }
            }
            body.addView(c);
        }
    }
}
