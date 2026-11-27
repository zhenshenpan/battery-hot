package io.github.zhenshenpan.twa;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/** 收藏只存本机（SharedPreferences），不联网、不传服务器 */
public class FavStore {

    private static final String PREF = "bh_fav";
    private static final String KEY = "items";

    private static SharedPreferences sp(Context c) {
        return c.getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    private static JSONArray load(Context c) {
        try {
            return new JSONArray(sp(c).getString(KEY, "[]"));
        } catch (Exception e) {
            return new JSONArray();
        }
    }

    private static void save(Context c, JSONArray arr) {
        sp(c).edit().putString(KEY, arr.toString()).apply();
    }

    public static boolean has(Context c, String id) {
        if (id == null || id.isEmpty()) {
            return false;
        }
        JSONArray a = load(c);
        for (int i = 0; i < a.length(); i++) {
            JSONObject o = a.optJSONObject(i);
            if (o != null && id.equals(o.optString("id"))) {
                return true;
            }
        }
        return false;
    }

    public static boolean toggle(Context c, JSONObject item) {
        String id = item.optString("id");
        JSONArray a = load(c);
        for (int i = 0; i < a.length(); i++) {
            JSONObject o = a.optJSONObject(i);
            if (o != null && id.equals(o.optString("id"))) {
                a.remove(i);
                save(c, a);
                return false;
            }
        }
        JSONObject copy;
        try {
            copy = new JSONObject(item.toString());
        } catch (Exception e) {
            copy = item;
        }
        try {
            copy.put("_ts", System.currentTimeMillis());
        } catch (Exception ignored) {
        }
        JSONArray next = new JSONArray();
        next.put(copy);
        for (int i = 0; i < a.length(); i++) {
            next.put(a.opt(i));
        }
        save(c, next);
        return true;
    }

    public static JSONArray list(Context c) {
        JSONArray src = load(c);
        List<JSONObject> tmp = new ArrayList<JSONObject>();
        for (int i = 0; i < src.length(); i++) {
            JSONObject o = src.optJSONObject(i);
            if (o != null) {
                tmp.add(o);
            }
        }
        Collections.sort(tmp, new Comparator<JSONObject>() {
            @Override
            public int compare(JSONObject x, JSONObject y) {
                long a = x.optLong("_ts", 0L);
                long b = y.optLong("_ts", 0L);
                if (a == b) {
                    return 0;
                }
                return a < b ? 1 : -1;
            }
        });
        JSONArray out = new JSONArray();
        for (int i = 0; i < tmp.size(); i++) {
            out.put(tmp.get(i));
        }
        return out;
    }
}
