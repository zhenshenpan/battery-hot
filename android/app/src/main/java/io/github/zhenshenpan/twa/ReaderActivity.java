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
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

public class ReaderActivity extends Activity {

    private static final int C_CARD = 0xFFFFFFFF;
    private static final int C_TEXT = 0xFF18212A;
    private static final int C_SUB = 0xFF6B7784;
    private static final int C_LINE = 0xFFE7EAEE;
    private static final int C_ACCENT = 0xFF0F9D76;
    private static final int C_ACCENT_BG = 0xFFE7F5F0;

    private WebView web;
    private ProgressBar bar;

    private int dp(float v) {
        return (int) (TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v,
                getResources().getDisplayMetrics()) + 0.5f);
    }

    private GradientDrawable round(int color, int radiusDp) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(radiusDp));
        return g;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        final String url = getIntent().getStringExtra("url");
        String name = getIntent().getStringExtra("name");
        if (name == null || name.isEmpty()) {
            name = "原文";
        }

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(C_CARD);

        LinearLayout bar0 = new LinearLayout(this);
        bar0.setOrientation(LinearLayout.HORIZONTAL);
        bar0.setGravity(Gravity.CENTER_VERTICAL);
        bar0.setPadding(dp(14), dp(10), dp(14), dp(10));
        bar0.setBackgroundColor(C_CARD);

        TextView back = new TextView(this);
        back.setText("← 返回");
        back.setTextSize(13);
        back.setTextColor(C_ACCENT);
        back.setTypeface(Typeface.DEFAULT_BOLD);
        back.setPadding(dp(10), dp(6), dp(12), dp(6));
        back.setBackground(round(C_ACCENT_BG, 16));
        back.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        });
        bar0.addView(back);

        TextView title = new TextView(this);
        title.setText(name);
        title.setTextSize(13);
        title.setTextColor(C_TEXT);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setPadding(dp(12), 0, dp(8), 0);
        title.setSingleLine(true);
        title.setEllipsize(android.text.TextUtils.TruncateAt.END);
        LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        bar0.addView(title, tlp);

        TextView ext = new TextView(this);
        ext.setText("浏览器");
        ext.setTextSize(11.5f);
        ext.setTextColor(C_SUB);
        ext.setPadding(dp(8), dp(5), dp(8), dp(5));
        ext.setBackground(round(0xFFF1F3F5, 12));
        ext.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
                } catch (Exception ignored) {
                }
            }
        });
        bar0.addView(ext);
        root.addView(bar0, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        bar.setMax(100);
        bar.setProgressTintList(android.content.res.ColorStateList.valueOf(C_ACCENT));
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(2));
        root.addView(bar, blp);

        View line = new View(this);
        line.setBackgroundColor(C_LINE);
        root.addView(line, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 1));

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(true);
        try {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        } catch (Exception ignored) {
        }
        s.setUserAgentString(s.getUserAgentString() + " BatteryHotApp/1.0.3");

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String u) {
                if (u != null && (u.startsWith("http://") || u.startsWith("https://"))) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(u)));
                } catch (Exception ignored) {
                }
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String u) {
                bar.setVisibility(View.GONE);
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int p) {
                bar.setProgress(p);
                bar.setVisibility(p >= 100 ? View.GONE : View.VISIBLE);
            }
        });

        root.addView(web, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(root);

        if (url == null || url.isEmpty()) {
            Toast.makeText(this, "缺少原文地址", Toast.LENGTH_SHORT).show();
            return;
        }
        web.loadUrl(url);
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}
