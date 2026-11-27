package io.github.zhenshenpan.twa;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

public class DetailActivity extends Activity {

    private static final int C_BG = 0xFFF5F6F8;
    private static final int C_CARD = 0xFFFFFFFF;
    private static final int C_TEXT = 0xFF18212A;
    private static final int C_SUB = 0xFF6B7784;
    private static final int C_LINE = 0xFFE7EAEE;
    private static final int C_ACCENT = 0xFF0F9D76;
    private static final int C_ACCENT_BG = 0xFFE7F5F0;

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

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        final JSONObject o;
        try {
            o = new JSONObject(getIntent().getStringExtra("item"));
        } catch (Exception e) {
            setResult(RESULT_CANCELED);
            finish();
            return;
        }

        ScrollView sv = new ScrollView(this);
        sv.setBackgroundColor(C_BG);
        sv.setFillViewport(true);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(0, dp(8), 0, dp(26));
        sv.addView(root, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setBackgroundColor(C_CARD);
        bar.setPadding(dp(16), dp(12), dp(16), dp(12));
        TextView back = text("← 返回", 13, C_ACCENT, true);
        back.setPadding(dp(10), dp(6), dp(12), dp(6));
        back.setBackground(round(C_ACCENT_BG, 16, 0, 0));
        back.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        });
        bar.addView(back);

        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        blp.leftMargin = dp(8);
        final TextView favBtn = text(FavStore.has(this, o.optString("id")) ? "★ 已收藏" : "☆ 收藏", 12, C_ACCENT, true);
        favBtn.setPadding(dp(10), dp(6), dp(10), dp(6));
        favBtn.setBackground(round(C_ACCENT_BG, 12, 0, 0));
        favBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                boolean on = FavStore.toggle(DetailActivity.this, o);
                favBtn.setText(on ? "★ 已收藏" : "☆ 收藏");
                Toast.makeText(DetailActivity.this, on ? "已加入我的收藏" : "已移出收藏", Toast.LENGTH_SHORT).show();
            }
        });
        bar.addView(favBtn, blp);

        bar.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        bar.addView(text("蓄电池热榜", 12, C_SUB, true));
        root.addView(bar, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout head = cardBox();
        LinearLayout chipRow = new LinearLayout(this);
        chipRow.setOrientation(LinearLayout.HORIZONTAL);
        chipRow.setGravity(Gravity.CENTER_VERTICAL);
        String kicker = o.optString("kicker", o.optString("category", ""));
        if (!kicker.isEmpty()) {
            TextView k = text(kicker, 10.5f, C_ACCENT, true);
            k.setPadding(dp(7), dp(3), dp(7), dp(3));
            k.setBackground(round(C_ACCENT_BG, 6, 0, 0));
            LinearLayout.LayoutParams klp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            klp.rightMargin = dp(6);
            chipRow.addView(k, klp);
        }
        int score = o.optInt("score", 0);
        if (score > 0) {
            TextView s = text("AI " + score, 10.5f, C_SUB, true);
            s.setPadding(dp(7), dp(3), dp(7), dp(3));
            s.setBackground(round(0xFFF1F3F5, 6, 0, 0));
            chipRow.addView(s, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        }
        head.addView(chipRow);

        TextView title = text(o.optString("title"), 20, C_TEXT, true);
        title.setPadding(0, dp(10), 0, 0);
        title.setLineSpacing(dp(4), 1.22f);
        head.addView(title);

        String summary = o.optString("summary", "");
        if (!summary.isEmpty()) {
            TextView st = text(summary, 13, 0xFF3C4650, false);
            st.setPadding(0, dp(10), 0, 0);
            st.setLineSpacing(dp(3), 1.38f);
            head.addView(st);
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
            meta.append(heat).append(" 家信源报道");
        }
        JSONArray tags = o.optJSONArray("tags");
        if (tags != null && tags.length() > 0) {
            if (meta.length() > 0) {
                meta.append(" · ");
            }
            for (int i = 0; i < tags.length() && i < 4; i++) {
                if (i > 0) {
                    meta.append(" / ");
                }
                meta.append(tags.optString(i));
            }
        }
        if (meta.length() > 0) {
            TextView m = text(meta.toString(), 10.5f, C_SUB, false);
            m.setPadding(0, dp(10), 0, 0);
            head.addView(m);
        }
        root.addView(head);

        JSONArray points = o.optJSONArray("points");
        if (points != null && points.length() > 0) {
            LinearLayout c = cardBox();
            c.addView(text("关键信息", 13, C_TEXT, true));
            for (int i = 0; i < points.length(); i++) {
                String p = points.optString(i);
                if (p == null || p.isEmpty()) {
                    continue;
                }
                TextView pt = text("· " + p, 12.5f, 0xFF3C4650, false);
                pt.setPadding(0, dp(7), 0, 0);
                pt.setLineSpacing(dp(3), 1.35f);
                c.addView(pt);
            }
            root.addView(c);
        }

        String why = o.optString("importance", "");
        if (!why.isEmpty()) {
            LinearLayout c = cardBox();
            c.addView(text("为什么重要", 13, C_TEXT, true));
            TextView wt = text(why, 12.5f, 0xFF3C4650, false);
            wt.setPadding(0, dp(7), 0, 0);
            wt.setLineSpacing(dp(3), 1.35f);
            c.addView(wt);
            root.addView(c);
        }

        JSONArray caveats = o.optJSONArray("caveats");
        if (caveats != null && caveats.length() > 0) {
            LinearLayout c = cardBox();
            c.addView(text("需要留意", 13, C_TEXT, true));
            for (int i = 0; i < caveats.length(); i++) {
                String p = caveats.optString(i);
                if (p == null || p.isEmpty()) {
                    continue;
                }
                TextView pt = text("· " + p, 12.5f, C_SUB, false);
                pt.setPadding(0, dp(7), 0, 0);
                c.addView(pt);
            }
            root.addView(c);
        }

        String firstUrl = "";
        JSONArray sources = o.optJSONArray("sources");
        if (sources != null && sources.length() > 0) {
            LinearLayout c = cardBox();
            c.addView(text("在应用内阅读原文", 13, C_TEXT, true));
            for (int i = 0; i < sources.length(); i++) {
                JSONObject s = sources.optJSONObject(i);
                if (s == null) {
                    continue;
                }
                final String url = s.optString("url", "");
                if (url.isEmpty()) {
                    continue;
                }
                if (firstUrl.isEmpty()) {
                    firstUrl = url;
                }
                final String nm = s.optString("name", "原文");
                TextView btn = text("阅读 · " + nm + "  ›", 12.5f, C_ACCENT, true);
                btn.setPadding(dp(12), dp(9), dp(12), dp(9));
                btn.setBackground(round(C_ACCENT_BG, 8, 0, 0));
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                lp.topMargin = dp(8);
                btn.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        Intent it = new Intent(DetailActivity.this, ReaderActivity.class);
                        it.putExtra("url", url);
                        it.putExtra("name", nm);
                        startActivity(it);
                    }
                });
                c.addView(btn, lp);
            }
            root.addView(c);
        }

        if (!firstUrl.isEmpty()) {
            final String u = firstUrl;
            TextView alt = text("改用系统浏览器打开这条", 10.5f, C_SUB, false);
            alt.setPadding(dp(18), dp(12), dp(18), 0);
            alt.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(u)));
                    } catch (Exception ignored) {
                    }
                }
            });
            root.addView(alt);
        }

        TextView foot = text("内容来自公开报道聚合，价格与招中标数据引自公开披露，仅供参考。", 10, C_SUB, false);
        foot.setPadding(dp(18), dp(14), dp(18), 0);
        root.addView(foot);

        setContentView(sv);
    }
}
