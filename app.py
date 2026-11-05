import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import re
import requests
import base64
import gzip
import hashlib
from datetime import datetime, timedelta
import jdatetime

from styles import FONTS, inject_login, inject_app

# ================== ثابت‌های پایه ==================
DEFAULT_NAV_ICONS = {
    "overview": {"icon": "fa-chart-pie", "color": "#3b82f6"},
    "journal": {"icon": "fa-circle-plus", "color": "#10b981"},
    "usd": {"icon": "fa-dollar-sign", "color": "#f59e0b"},
    "gold": {"icon": "fa-coins", "color": "#eab308"},
    "settings": {"icon": "fa-gear", "color": "#6b7280"},
}
NAV_LABELS = {"overview": "نمای کلی", "journal": "افزودن دارایی", "usd": "دلار", "gold": "صندوق‌های طلا", "settings": "تنظیمات"}
NAV_EMOJI = {"overview": "📊", "journal": "➕", "usd": "💵", "gold": "🥇", "settings": "⚙️"}

FALLBACK_ICONS = [
    {"class": "fa-folder", "label": "Folder"}, {"class": "fa-coins", "label": "Coins"},
    {"class": "fa-wallet", "label": "Wallet"}, {"class": "fa-money-bill-wave", "label": "Money"},
    {"class": "fa-dollar-sign", "label": "Dollar"}, {"class": "fa-building-columns", "label": "Bank"},
    {"class": "fa-piggy-bank", "label": "Piggy Bank"}, {"class": "fa-vault", "label": "Vault"},
    {"class": "fa-gem", "label": "Gem"}, {"class": "fa-crown", "label": "Crown"},
    {"class": "fa-house", "label": "House"}, {"class": "fa-building", "label": "Building"},
    {"class": "fa-car", "label": "Car"}, {"class": "fa-chart-line", "label": "Chart Line"},
    {"class": "fa-chart-pie", "label": "Chart Pie"}, {"class": "fa-bitcoin-sign", "label": "Bitcoin"},
    {"class": "fa-ethereum", "label": "Ethereum"}, {"class": "fa-landmark", "label": "Landmark"},
    {"class": "fa-industry", "label": "Industry"}, {"class": "fa-seedling", "label": "Seedling"},
    {"class": "fa-briefcase", "label": "Briefcase"}, {"class": "fa-store", "label": "Store"},
    {"class": "fa-sack-dollar", "label": "Sack Dollar"}, {"class": "fa-receipt", "label": "Receipt"},
    {"class": "fa-tag", "label": "Tag"}, {"class": "fa-fire", "label": "Fire"},
    {"class": "fa-bolt", "label": "Bolt"}, {"class": "fa-box", "label": "Box"},
    {"class": "fa-gear", "label": "Gear"}, {"class": "fa-circle-plus", "label": "Circle Plus"},
]

CATEGORY_KEYWORDS = {
    "money": ["coin", "dollar", "money", "wallet", "bank", "cash", "currency", "credit-card", "payment", "receipt", "invoice", "sack", "piggy", "vault", "tax", "donate", "hand-holding", "tip", "price-tag", "bitcoin", "ethereum", "euro", "sterling", "yen", "rupee", "ruble", "won", "lira", "peso", "shekel", "tenge", "exchange", "money-bill", "money-check"],
    "chart": ["chart", "graph", "trend", "analytics", "presentation-chart", "arrow-trend", "magnifying-glass-chart", "square-poll", "ranking", "signal", "wifi", "spinner", "percent"],
    "gems": ["gem", "crown", "diamond", "gift", "award", "medal", "star", "trophy", "ribbon", "certificate"],
    "building": ["building", "house", "home", "office", "factory", "industry", "warehouse", "store", "shop", "landmark", "church", "mosque", "hotel", "school", "hospital", "motel", "tent", "campground"],
    "transport": ["car", "truck", "plane", "ship", "train", "bus", "bike", "motorcycle", "taxi", "rocket", "helicopter", "boat", "tram", "subway", "van", "tractor", "trailer", "wheelchair"],
    "goods": ["box", "package", "shipping", "cart", "basket", "bag-shopping", "boxes", "cubes", "cube"],
    "business": ["briefcase", "handshake", "user-tie", "file-invoice", "file-contract", "clipboard-check", "check-double"],
    "file": ["folder", "file", "save", "download", "upload", "disk", "document", "paper", "clipboard", "notebook", "book", "bookmark", "newspaper", "scroll", "envelope", "mail"],
    "user": ["user", "person", "people", "group", "team", "users"],
    "system": ["gear", "cog", "tool", "wrench", "hammer", "screwdriver", "key", "lock", "shield", "bell", "power-off", "right-from-bracket", "arrow-right-from-bracket", "ellipsis", "bars"],
    "media": ["camera", "photo", "image", "video", "music", "headphone", "play", "pause", "stop", "record", "microphone", "film", "compact-disc", "volume", "speaker"],
    "symbol": ["circle-check", "circle-xmark", "circle-plus", "circle-minus", "circle", "square", "triangle", "heart", "plus", "minus", "equals", "question", "info", "exclamation", "ban", "check"],
    "time": ["clock", "calendar", "time", "hourglass", "stopwatch", "timer", "watch"],
    "nature": ["fire", "bolt", "sun", "leaf", "tree", "seedling", "water", "droplet", "wind", "snow", "cloud", "moon", "snowflake", "mountain"],
}

CATEGORY_LABELS = {
    "money": "💰 پول و ارز", "chart": "📊 سرمایه و نمودار", "gems": "🥇 طلا و جواهر",
    "building": "🏢 ملک و ساختمان", "transport": "🚗 حمل و نقل", "goods": "📦 کالا",
    "business": "💼 کسب و کار", "file": "📁 فایل و سند", "user": "👤 کاربر",
    "system": "⚙️ تنظیمات", "media": "🎬 رسانه", "symbol": "🔷 نماد",
    "time": "⏰ زمان", "nature": "🌿 طبیعت", "other": "📌 سایر",
}

def categorize_icon(icon_class, label):
    text = f"{icon_class} {label}".lower()
    cats = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                cats.append(cat)
                break
    return cats or ["other"]

# ================== تنظیمات صفحه ==================
st.set_page_config(page_title="داشبورد مالی", layout="wide", initial_sidebar_state="expanded")
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
APP_PASSWORD = st.secrets.get("APP_PASSWORD") or "S@mnet11970"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"

def get_auth_token():
    return hashlib.sha256((APP_PASSWORD + "_salt_v2_2024").encode()).hexdigest()

AUTH_TOKEN = get_auth_token()

# ================== آیکون‌ها ==================
@st.cache_data(ttl=86400, show_spinner=False)
def load_fa_icons(cache_v="v7"):
    try:
        r = requests.get("https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/metadata/icons.json", timeout=15)
        if r.status_code == 200:
            meta = r.json()
            icons = []
            for name, info in meta.items():
                if "solid" not in info.get("free", []):
                    continue
                label = info.get("label", name)
                icons.append({"class": f"fa-{name}", "label": label,
                              "categories": categorize_icon(f"fa-{name}", label)})
            if icons:
                return sorted(icons, key=lambda x: x["label"].lower())
    except Exception:
        pass
    return [{"class": ic["class"], "label": ic["label"],
             "categories": categorize_icon(ic["class"], ic["label"])} for ic in FALLBACK_ICONS]

def icon_emoji(fa_class):
    _EMOJI = {
        "fa-folder": "📁", "fa-coins": "🪙", "fa-wallet": "👛", "fa-dollar-sign": "💲",
        "fa-building-columns": "🏦", "fa-gem": "💎", "fa-crown": "👑", "fa-house": "🏠",
        "fa-car": "🚗", "fa-chart-line": "📈", "fa-chart-pie": "📊", "fa-bitcoin-sign": "₿",
        "fa-briefcase": "💼", "fa-store": "🏪", "fa-sack-dollar": "💰", "fa-fire": "🔥",
        "fa-bolt": "⚡", "fa-box": "📦", "fa-gear": "⚙️", "fa-circle-plus": "➕",
    }
    return _EMOJI.get(fa_class, "📁")

# ================== توابع تاریخ ==================
def today_jalali_str():
    return jdatetime.date.today().strftime("%Y/%m/%d")

def iso_to_jalali(iso_str, with_time=True):
    if not iso_str: return "—"
    try:
        dt = datetime.fromisoformat(iso_str)
        j = jdatetime.datetime.fromgregorian(datetime=dt)
        return j.strftime("%Y/%m/%d - %H:%M") if with_time else j.strftime("%Y/%m/%d")
    except Exception:
        return "—"

def parse_jalali(s):
    try:
        s = s.strip().replace("-", "/").replace(".", "/")
        parts = s.split("/")
        if len(parts) != 3: return None
        y, m, d = map(int, parts)
        return jdatetime.date(y, m, d)
    except Exception:
        return None

def jalali_to_gregorian_iso(jdate, time_str="00:00"):
    g = jdate.togregorian()
    return f"{g.strftime('%Y-%m-%d')}T{time_str}:00"

def fmt_num(x):
    try:
        f = float(x)
        return f"{int(f):,}" if f == int(f) else f"{f:,.2f}"
    except Exception:
        return str(x)

def _compact_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def _decompress_if_needed(raw_bytes):
    if len(raw_bytes) >= 2 and raw_bytes[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(raw_bytes)
        except Exception:
            pass
    return raw_bytes

def _short_id():
    return str(int(datetime.now().timestamp() * 1000))

# ================== احراز هویت ==================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    qp_auth = st.query_params.get("auth")
    if qp_auth and qp_auth == AUTH_TOKEN:
        st.session_state.authenticated = True

if not st.session_state.authenticated:
    inject_login()
    st.markdown("<div style='height: 6vh;'></div>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown("""
        <div style="text-align:center; padding: 24px 0 16px 0; direction: rtl;">
            <div style="font-size: 3.2rem; line-height: 1; margin-bottom: 8px;">🔐</div>
            <h1 style="margin: 0; color: #1e40af;">داشبورد مالی</h1>
            <p style="color: #6b7280; margin-top: 8px;">لطفاً رمز عبور را وارد کنید</p>
        </div>
        """, unsafe_allow_html=True)
        with st.container(border=True):
            with st.form("login_form"):
                password = st.text_input("رمز", type="password", placeholder="••••••••", label_visibility="collapsed")
                if st.form_submit_button("🚪 ورود", use_container_width=True):
                    if password == APP_PASSWORD:
                        st.session_state.authenticated = True
                        st.query_params["auth"] = AUTH_TOKEN
                        st.rerun()
                    else:
                        st.error("❌ رمز عبور اشتباه است.")
    st.stop()

# ================== GitHub API ==================
def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

@st.cache_data(ttl=60, show_spinner=False)
def check_github_status(token, repo):
    if not token and not repo: return "no_config", "تنظیم نشده"
    if not token: return "no_token", "توکن ندارد"
    if not repo: return "no_repo", "مخزن ندارد"
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}",
                         headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}, timeout=8)
        if r.status_code == 200: return "ok", f"متصل به {repo}"
        if r.status_code == 401: return "error", "توکن نامعتبر (401)"
        if r.status_code == 404: return "error", "مخزن یافت نشد (404)"
        return "error", f"HTTP {r.status_code}"
    except Exception as e:
        return "error", f"خطای شبکه: {str(e)[:40]}"

def load_local_file():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as f:
                raw = f.read()
            decompressed = _decompress_if_needed(raw)
            return json.loads(decompressed.decode("utf-8"))
    except Exception:
        pass
    return None

def save_local_file(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write(_compact_json(data))
        return True
    except Exception:
        return False

def load_github_file():
    if not GITHUB_TOKEN or not GITHUB_REPO: return None
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(api_url, headers=github_headers(), timeout=20)
        if r.status_code != 200: return None
        info = r.json()
        content_b64 = info.get("content", "")
        if not content_b64:
            raw_url = info.get("download_url") or f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_FILE_PATH}"
            raw_resp = requests.get(raw_url, timeout=30)
            if raw_resp.status_code != 200: return None
            content_bytes = raw_resp.content
        else:
            content_bytes = base64.b64decode(content_b64)
        decompressed = _decompress_if_needed(content_bytes)
        return json.loads(decompressed.decode("utf-8"))
    except Exception:
        return None

def save_github_file(data):
    if not GITHUB_TOKEN or not GITHUB_REPO: return False, "GitHub تنظیم نشده"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    sha = None
    try:
        r = requests.get(url, headers=github_headers(), timeout=15)
        if r.status_code == 200: sha = r.json()["sha"]
        elif r.status_code == 401: return False, "توکن نامعتبر (401)"
    except Exception as e:
        return False, f"خطای شبکه: {str(e)[:50]}"
    raw = _compact_json(data).encode("utf-8")
    compressed = gzip.compress(raw, mtime=0)
    encoded = base64.b64encode(compressed).decode()
    payload = {
        "message": f"update {today_jalali_str()} {datetime.now().strftime('%H:%M')} ({len(compressed):,}B gz)",
        "content": encoded, "branch": GITHUB_BRANCH,
    }
    if sha: payload["sha"] = sha
    try:
        r = requests.put(url, headers=github_headers(), json=payload, timeout=30)
        if r.status_code in (200, 201): return True, ""
        if r.status_code == 401: return False, "توکن نامعتبر (401)"
        if r.status_code == 403: return False, "دسترسی write ندارد (403)"
        if r.status_code == 404: return False, "مخزن یافت نشد (404)"
        if r.status_code == 409: return False, "تضاد SHA (409)"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"خطای شبکه: {str(e)[:50]}"

def verify_github_save(expected_data):
    if not GITHUB_TOKEN or not GITHUB_REPO: return False, "GitHub تنظیم نشده", None
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(api_url, headers=github_headers(), timeout=20)
        if r.status_code != 200: return False, f"HTTP {r.status_code}", None
        info = r.json()
        sha = info.get("sha", "")[:8]
        size_bytes = info.get("size", 0)
        content_b64 = info.get("content", "")
        if not content_b64:
            raw_url = info.get("download_url") or f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_FILE_PATH}"
            raw_resp = requests.get(raw_url, timeout=30)
            if raw_resp.status_code != 200: return False, "خواندن ناموفق", sha
            content_bytes = raw_resp.content
        else:
            content_bytes = base64.b64decode(content_b64)
        decompressed = _decompress_if_needed(content_bytes)
        gh_data = json.loads(decompressed.decode("utf-8"))
        if gh_data.get("last_saved") != expected_data.get("last_saved"):
            return False, "timestamp متفاوت", sha
        kind = "gzip" if content_bytes[:2] == b"\x1f\x8b" else "plain"
        return True, f"تأیید شد — {size_bytes:,}B ({kind})", sha
    except Exception as e:
        return False, str(e)[:50], None

# ================== مهاجرت ==================
def migrate_data(data):
    if not isinstance(data, dict) or not data:
        return {"assets": [], "usd_rates": [], "gold_funds": [], "settings": {
            "font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy(),
            "custom_fonts": {}, "dark_mode": False}}
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list):
        old = data.get("usd_rate")
        data["usd_rates"] = []
        if old:
            data["usd_rates"].append({"id": _short_id(), "rate": old, "note": "منتقل‌شده",
                                     "created_at": datetime.now().isoformat(),
                                     "created_at_jalali": today_jalali_str()})
        data.pop("usd_rate", None)
    if "journals" in data and isinstance(data.get("journals"), list):
        if "assets" not in data or not isinstance(data.get("assets"), list): data["assets"] = []
        for j in data.get("journals", []):
            aid = j.get("id") or _short_id()
            ciso = j.get("created_at_gregorian") or j.get("created_at") or datetime.now().isoformat()
            cjal = j.get("created_at_jalali") or iso_to_jalali(ciso, with_time=False)
            data["assets"].append({
                "id": aid, "name": j.get("asset_name", "بدون نام"), "icon": "fa-folder",
                "color": "#3b82f6", "overview_emoji": "", "currency": j.get("currency", "IRR"),
                "created_at_gregorian": ciso, "created_at_jalali": cjal,
                "records": [{"id": aid + "_r", "date_gregorian": ciso, "date_jalali": cjal,
                            "quantity": j.get("amount", 0), "unit_price": 1, "note": "منتقل‌شده"}]})
        data.pop("journals", None)
    if "assets" not in data or not isinstance(data.get("assets"), list): data["assets"] = []
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list): data["usd_rates"] = []
    if "gold_funds" not in data or not isinstance(data.get("gold_funds"), list): data["gold_funds"] = []
    if "settings" not in data or not isinstance(data.get("settings"), dict):
        data["settings"] = {"font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy(),
                            "custom_fonts": {}, "dark_mode": False}
    data["settings"].setdefault("font", "vazirmatn")
    data["settings"].setdefault("dark_mode", False)
    if "nav_icons" not in data["settings"]: data["settings"]["nav_icons"] = DEFAULT_NAV_ICONS.copy()
    for k, v in DEFAULT_NAV_ICONS.items(): data["settings"]["nav_icons"].setdefault(k, v.copy())
    if "custom_fonts" not in data["settings"]: data["settings"]["custom_fonts"] = {}
    seen = set(); unique = []
    for a in data["assets"]:
        if a.get("id") and a["id"] not in seen:
            seen.add(a["id"]); unique.append(a)
    data["assets"] = unique
    for a in data["assets"]:
        if not isinstance(a.get("icon"), str) or not a["icon"].startswith("fa-"): a["icon"] = "fa-folder"
        a.setdefault("color", "#3b82f6"); a.setdefault("overview_emoji", "")
    seen_g = set(); unique_g = []
    for gf in data["gold_funds"]:
        if gf.get("id") and gf["id"] not in seen_g:
            seen_g.add(gf["id"]); unique_g.append(gf)
    data["gold_funds"] = unique_g
    return data

def load_all():
    local = load_local_file()
    gh = load_github_file()
    l_has = local and (local.get("assets") or local.get("usd_rates") or local.get("gold_funds"))
    g_has = gh and (gh.get("assets") or gh.get("usd_rates") or gh.get("gold_funds"))
    if l_has and g_has:
        l_saved = local.get("last_saved", ""); g_saved = gh.get("last_saved", "")
        chosen = (local if l_saved > g_saved else gh) if (l_saved and g_saved) else gh
        save_local_file(chosen); return migrate_data(chosen)
    if g_has: save_local_file(gh); return migrate_data(gh)
    if l_has: return migrate_data(local)
    return migrate_data({})

def save_all(data, verify=True):
    data["last_saved"] = datetime.now().isoformat()
    data["last_saved_jalali"] = jdatetime.datetime.fromgregorian(datetime=datetime.now()).strftime("%Y/%m/%d - %H:%M")
    local_ok = save_local_file(data)
    gh_ok, gh_err = save_github_file(data)
    if gh_ok:
        if verify:
            v_ok, v_msg, _ = verify_github_save(data)
            if v_ok: st.toast("✅ ذخیره و تأیید شد", icon="✅"); return True
            st.warning(f"⚠️ ذخیره شد ولی تأیید ناقص: {v_msg}"); return False
        st.toast("✅ ذخیره شد"); return True
    else:
        if local_ok:
            st.error(f"❌ **ذخیره GitHub ناموفق!** {gh_err}")
            st.warning("⚠️ فقط در حافظه موقت — با ری‌استارت از دست می‌رود!")
        else:
            st.error(f"❌ **هیچ جا ذخیره نشد!** {gh_err}")
        return False

# ================== توابع کمکی ==================
def get_settings(data):
    s = data.get("settings") or {}
    return {"font": s.get("font", "vazirmatn"),
            "nav_icons": s.get("nav_icons", DEFAULT_NAV_ICONS),
            "custom_fonts": s.get("custom_fonts", {}) or {},
            "dark_mode": bool(s.get("dark_mode", False))}

def get_all_fonts(data):
    fonts = {}
    for k, (name, url) in FONTS.items(): fonts[k] = {"name": name, "family": name, "builtin": True}
    custom = (data.get("settings") or {}).get("custom_fonts", {}) or {}
    for k, info in custom.items(): fonts[k] = {"name": info.get("display_name", k), "family": k, "builtin": False}
    return fonts

def asset_icon(asset):
    ic = asset.get("icon", "fa-folder")
    return ic if isinstance(ic, str) and ic.startswith("fa-") else "fa-folder"

def asset_color(asset): return asset.get("color", "#3b82f6")

def asset_overview_emoji(asset):
    custom = (asset.get("overview_emoji") or "").strip()
    return custom if custom else icon_emoji(asset_icon(asset))

def get_current_usd_rate(data):
    rates = data.get("usd_rates", [])
    if not rates: return None, None
    latest = max(rates, key=lambda x: x.get("created_at", ""))
    return latest["rate"], latest.get("created_at_jalali", "—")

def latest_record(asset):
    records = asset.get("records", [])
    if not records: return None
    return max(records, key=lambda r: (r.get("date_gregorian", ""), r.get("id", "")))

def compute_asset_value(asset, usd_rate):
    rec = latest_record(asset)
    if not rec: return 0, None, None
    value = rec["quantity"] * rec["unit_price"]
    if asset["currency"] == "IRR":
        usd = (value / usd_rate) if (usd_rate and usd_rate > 0) else None
    else:
        usd = value
    return value, usd, rec

def currency_label(cur): return "ریال" if cur == "IRR" else "دلار"

def get_version(key):
    if key not in st.session_state: st.session_state[key] = 0
    return st.session_state[key]

def bump_version(key): st.session_state[key] = st.session_state.get(key, 0) + 1

def sync_usd_rates_to_gold_funds(data):
    rates = sorted(data.get("usd_rates", []), key=lambda x: x.get("created_at", ""))
    updated = 0; missing = 0
    for gf in data.get("gold_funds", []):
        for rec in gf.get("records", []):
            rec_date = rec.get("date_gregorian", "")[:10]
            if not rec_date: continue
            rate_at = None
            for ur in rates:
                if ur.get("created_at", "")[:10] <= rec_date: rate_at = ur["rate"]
                else: break
            if rate_at is not None:
                if rec.get("usd_rate_used") != rate_at:
                    rec["usd_rate_used"] = rate_at; updated += 1
            else: missing += 1
    return updated, missing

def build_portfolio_timeline(data):
    assets = data.get("assets", [])
    usd_rates = sorted(data.get("usd_rates", []), key=lambda x: x.get("created_at", ""))
    all_dates = set()
    for a in assets:
        for r in a.get("records", []):
            if r.get("date_gregorian"): all_dates.add(r["date_gregorian"][:10])
    for r in usd_rates:
        if r.get("created_at"): all_dates.add(r["created_at"][:10])
    if not all_dates: return pd.DataFrame()
    rows = []
    for d in sorted(all_dates):
        rate_at = None
        for ur in usd_rates:
            if ur.get("created_at", "")[:10] <= d: rate_at = ur["rate"]
            else: break
        t_irr = 0.0; t_usd = 0.0
        for a in assets:
            recs = [r for r in a.get("records", []) if r.get("date_gregorian", "")[:10] <= d]
            if not recs: continue
            latest = max(recs, key=lambda r: r.get("date_gregorian", ""))
            val = latest["quantity"] * latest["unit_price"]
            if a["currency"] == "IRR":
                t_irr += val
                if rate_at and rate_at > 0: t_usd += val / rate_at
            else:
                t_usd += val
                if rate_at and rate_at > 0: t_irr += val * rate_at
        try:
            dt = datetime.fromisoformat(d + "T00:00:00")
            jd = jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d")
        except Exception: jd = d
        rows.append({"date_gregorian": d, "date_jalali": jd, "total_irr": t_irr, "total_usd": t_usd})
    return pd.DataFrame(rows)

def render_html_table(df, dark=False):
    bg_head = "#161b22" if dark else "#f3f4f6"
    bg_odd = "#0d1117" if dark else "#f9fafb"
    bg_even = "#161b22" if dark else "#ffffff"
    border = "#30363d" if dark else "#e5e7eb"
    text_col = "#e6edf3" if dark else "#1f2937"
    html = (f'<div style="overflow-x:auto; margin:8px 0;">'
            f'<table style="width:100%; border-collapse:collapse; direction:rtl; '
            f'font-family:inherit; font-size:0.9rem; color:{text_col};">')
    html += f'<thead><tr style="background:{bg_head}; font-weight:bold;">'
    for col in df.columns:
        html += f'<th style="padding:10px 12px; text-align:right; border-bottom:2px solid {border}; white-space:nowrap;">{col}</th>'
    html += '</tr></thead><tbody>'
    for idx, row in df.iterrows():
        bg = bg_odd if idx % 2 == 0 else bg_even
        html += f'<tr style="background:{bg};">'
        for val in row:
            html += f'<td style="padding:8px 12px; text-align:right; border-bottom:1px solid {border};">{val}</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================== تحلیل صندوق طلا ==================
def unit_usd_equivalent(record):
    rate = record.get("usd_rate_used", 0)
    if rate <= 0: return None
    return record["unit_price"] / rate

def gold_gram_per_unit(record):
    """گرم طلا در هر واحد صندوق"""
    if record.get("ounce_price_usd", 0) <= 0 or record.get("usd_rate_used", 0) <= 0 or record.get("unit_price", 0) <= 0:
        return None
    return (record["unit_price"] * 31.1035) / (record["ounce_price_usd"] * record["usd_rate_used"])

def gold_fund_analytics(fund):
    """محاسبه معادل دلاری، بازده، تغییرات برای هر رکورد"""
    records = sorted(fund.get("records", []), key=lambda r: r.get("date_gregorian", ""))
    if not records: return []
    rows = []
    first_usd = None
    for i, r in enumerate(records):
        usd_eq = unit_usd_equivalent(r)
        if first_usd is None and usd_eq: first_usd = usd_eq
        ounce_change = None; usd_change = None
        if i > 0:
            prev = records[i-1]
            if prev.get("ounce_price_usd", 0) > 0:
                ounce_change = (r["ounce_price_usd"] / prev["ounce_price_usd"] - 1) * 100
            if prev.get("usd_rate_used", 0) > 0 and r.get("usd_rate_used", 0) > 0:
                usd_change = (r["usd_rate_used"] / prev["usd_rate_used"] - 1) * 100
        usd_return = None
        if first_usd and usd_eq: usd_return = (usd_eq / first_usd - 1) * 100
        gram = gold_gram_per_unit(r)
        rows.append({"record": r, "usd_equivalent": usd_eq, "usd_return_pct": usd_return,
                     "ounce_change_pct": ounce_change, "usd_change_pct": usd_change,
                     "gram_per_unit": gram})
    return rows

def dollar_trap_analysis(fund, days=30):
    """تحلیل تله دلار در N روز گذشته"""
    records = sorted(fund.get("records", []), key=lambda r: r.get("date_gregorian", ""))
    if len(records) < 2: return None
    last = records[-1]
    last_date_str = last.get("date_gregorian", "")[:10]
    if not last_date_str: return None
    try:
        dt_last = datetime.fromisoformat(last_date_str + "T00:00:00")
        cutoff = (dt_last - timedelta(days=days)).strftime("%Y-%m-%d")
    except Exception: return None
    older = None
    for r in records:
        if r.get("date_gregorian", "")[:10] >= cutoff:
            older = r; break
    if not older or older.get("id") == last.get("id"): return None
    ounce_change = 0; usd_change = 0
    if older.get("ounce_price_usd", 0) > 0:
        ounce_change = (last["ounce_price_usd"] / older["ounce_price_usd"] - 1) * 100
    if older.get("usd_rate_used", 0) > 0:
        usd_change = (last["usd_rate_used"] / older["usd_rate_used"] - 1) * 100
    return {"usd_change": usd_change, "ounce_change": ounce_change,
            "gap": usd_change - ounce_change, "days": days,
            "older_date": older.get("date_jalali"), "last_date": last.get("date_jalali")}

def ounce_signal(fund):
    """سیگنال بر اساس انس (نه پرمیوم)"""
    records = sorted(fund.get("records", []), key=lambda r: r.get("date_gregorian", ""))
    if len(records) < 3: return "⚪ داده کافی نیست"
    last = records[-1]
    ounces = [r.get("ounce_price_usd", 0) for r in records if r.get("ounce_price_usd", 0) > 0]
    if not ounces: return "⚪ داده انس کافی نیست"
    avg = sum(ounces) / len(ounces)
    current = last.get("ounce_price_usd", 0)
    if current <= 0 or avg <= 0: return "⚪ داده معتبر نیست"
    diff = (current / avg - 1) * 100
    if diff > 5: return f"🔴 انس {diff:+.1f}% بالای میانگین — فروش"
    elif diff > 0: return f"🟡 انس {diff:+.1f}% بالای میانگین — کمی فروش"
    elif diff > -5: return f"🟢 انس {diff:+.1f}% زیر میانگین — کمی خرید"
    else: return f"🟢🟢 انس {diff:+.1f}% زیر میانگین — خرید قوی"

# ================== گرید آیکون ==================
def _icon_grid_picker(prefix, current, on_save):
    icons = load_fa_icons()
    all_cats = set()
    for ic in icons:
        for c in ic.get("categories", []): all_cats.add(c)
    cat_order = [k for k in CATEGORY_LABELS.keys() if k in all_cats]
    cat_order += sorted([c for c in all_cats if c not in CATEGORY_LABELS])
    cat_options = ["__all__"] + cat_order
    c1, c2 = st.columns([2, 3])
    cat = c1.selectbox("📂 دسته", cat_options,
                       format_func=lambda x: "🌐 همه" if x == "__all__" else CATEGORY_LABELS.get(x, x),
                       key=f"{prefix}_cat")
    s = c2.text_input("🔍", key=f"{prefix}_search", placeholder="جستجو...", label_visibility="collapsed")
    filtered = icons if cat == "__all__" else [i for i in icons if cat in i.get("categories", [])]
    if s:
        q = s.lower()
        filtered = [i for i in filtered if q in i["label"].lower() or q in i["class"].lower()]
    per_page = 48; total = len(filtered)
    pages = max(1, (total + per_page - 1) // per_page)
    pk = f"{prefix}_page"; catk = f"{prefix}_cat_prev"
    if catk not in st.session_state or st.session_state[catk] != cat:
        st.session_state[pk] = 0; st.session_state[catk] = cat
    if st.session_state.get(pk, 0) >= pages: st.session_state[pk] = 0
    page = st.session_state.get(pk, 0)
    display = filtered[page * per_page:(page + 1) * per_page]
    st.caption(f"**{total}** آیکون — صفحه **{page + 1}** از **{pages}**")
    if total == 0: st.info("آیکونی یافت نشد."); return
    for row in range(0, len(display), 8):
        cols = st.columns(8)
        for j, ic in enumerate(display[row:row + 8]):
            with cols[j]:
                is_cur = (ic["class"] == current)
                border = "3px solid #22c55e" if is_cur else "1px solid #e5e7eb"
                st.markdown(
                    f'<div style="text-align:center; padding:10px 4px; border:{border}; '
                    f'border-radius:8px; margin-bottom:4px; background:#f9fafb;">'
                    f'<i class="fa-solid {ic["class"]}" style="font-size:1.6rem; color:#3b82f6;"></i></div>',
                    unsafe_allow_html=True)
                lbl = "✅" if is_cur else "انتخاب"
                if st.button(lbl, key=f"{prefix}_btn_{ic['class']}", use_container_width=True, disabled=is_cur):
                    on_save(ic["class"]); st.rerun()
    if pages > 1:
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc1:
            if st.button("◀ قبلی", key=f"{prefix}_prev", use_container_width=True, disabled=(page == 0)):
                st.session_state[pk] = page - 1; st.rerun()
        with pc2:
            st.markdown(f'<div style="text-align:center; padding-top:8px; font-weight:600;">صفحه {page + 1} / {pages}</div>', unsafe_allow_html=True)
        with pc3:
            if st.button("بعدی ▶", key=f"{prefix}_next", use_container_width=True, disabled=(page >= pages - 1)):
                st.session_state[pk] = page + 1; st.rerun()

def _emoji_grid_picker(prefix, current, on_save):
    EMOJIS = ["📁", "🪙", "💎", "👑", "💰", "💵", "💴", "💶", "💷", "🏦",
              "🏠", "🏢", "🚗", "🚚", "📈", "📊", "📉", "⚡", "🔥", "💧",
              "🌾", "🏭", "🎁", "🥇", "🥈", "🥉", "🌱", "💼", "🏪", "🧾",
              "🏷️", "⚖️", "🛡️", "⛽", "🔐", "👛", "💲", "₿", "Ξ", "📦",
              "🎯", "🎨", "🌍", "⭐", "❤️", "💡", "🔑", "🎓", "🎵", "🎮"]
    for row in range(0, len(EMOJIS), 10):
        cols = st.columns(10)
        for j, em in enumerate(EMOJIS[row:row + 10]):
            with cols[j]:
                is_cur = (em == current)
                lbl = f"{'✅' if is_cur else ''}{em}"
                if st.button(lbl, key=f"{prefix}_em_{row + j}", use_container_width=True):
                    on_save(em); st.rerun()
    st.divider()
    c1, c2 = st.columns([3, 1])
    custom = c1.text_input("ایموجی دلخواه", value=current or "", max_chars=8, key=f"{prefix}_custom")
    if c2.button("💾 ذخیره", key=f"{prefix}_save_custom", use_container_width=True):
        on_save(custom.strip()[:8]); st.rerun()
    if st.button("🔄 خودکار", key=f"{prefix}_clear", use_container_width=True):
        on_save(""); st.rerun()

# ================== مقداردهی ==================
if "data" not in st.session_state:
    st.session_state.data = load_all()
st.session_state.data = migrate_data(st.session_state.data)
data = st.session_state.data
data.setdefault("assets", []); data.setdefault("usd_rates", []); data.setdefault("gold_funds", [])

inject_app(data)
_dark = get_settings(data)["dark_mode"]
assets = data.get("assets", [])

# ================== سایدبار ==================
with st.sidebar:
    c_date, c_mode, c_logout = st.columns([3, 1, 1])
    with c_date: st.markdown(f"### 🗓️ {today_jalali_str()}")
    with c_mode:
        if st.button("☀️" if _dark else "🌙", key="dark_toggle_btn", help="روز/شب", use_container_width=True):
            data["settings"]["dark_mode"] = not _dark
            st.session_state.data = data; save_all(data); st.rerun()
    with c_logout:
        if st.button("🚪", key="logout_btn", help="خروج", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.pop("data", None)
            st.query_params.clear(); st.rerun()
    st.divider()

    rate, rate_date = get_current_usd_rate(data)
    if rate:
        bg_card = "#1f6feb" if _dark else "#3b82f6"
        bg_grad = "linear-gradient(135deg, #1a2332 0%, #1f2937 100%)" if _dark else "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)"
        title_col = "#8b949e" if _dark else "#6b7280"
        value_col = "#58a6ff" if _dark else "#1e40af"
        st.markdown(f"""
        <div style="background: {bg_grad}; padding: 14px 16px; border-radius: 10px; border-right: 4px solid {bg_card}; margin-bottom: 12px; direction: rtl; text-align: right;">
            <div style="font-size: 0.82rem; color: {title_col}; margin-bottom: 6px;">💵 نرخ فعلی دلار</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: {value_col};">{rate:,.0f}<span style="font-size: 0.95rem; color: {title_col};"> ریال</span></div>
            <div style="font-size: 0.72rem; color: {title_col}; margin-top: 6px;">آخرین: {rate_date}</div>
        </div>
        """, unsafe_allow_html=True)
    else: st.info("💡 هنوز نرخی ثبت نشده.")

    st.divider()
    st.markdown("**💾 وضعیت ذخیره‌سازی**")
    if data.get("last_saved"): st.caption(f"✅ آخرین ذخیره: {data.get('last_saved_jalali', '—')}")
    else: st.caption("⚠️ هنوز ذخیره نشده")
    local_ok = os.path.exists(DATA_FILE)
    gh_status, gh_message = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
    c1, c2 = st.columns(2)
    c1.caption(f"{'✅' if local_ok else '❌'} محلی")
    c2.caption(f"{'✅' if gh_status == 'ok' else '❌'} GitHub")
    if gh_status != "ok": st.error(f"⚠️ {gh_message}")
    if st.button("💾 ذخیره فوری + تأیید", use_container_width=True, key="force_save"):
        if save_all(data): st.rerun()

    st.divider()
    with st.expander("📥 پشتیبان / 📤 بازیابی", expanded=False):
        st.download_button("📥 دانلود JSON", data=json.dumps(data, ensure_ascii=False, indent=2),
                          file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                          mime="application/json", use_container_width=True)
        uploaded = st.file_uploader("📤 آپلود JSON", type=["json"], key="uploader")
        if uploaded is not None:
            try:
                imported = migrate_data(json.loads(uploaded.read().decode("utf-8")))
                if st.button("✅ اعمال", use_container_width=True):
                    st.session_state.data = imported; save_all(imported); st.rerun()
            except Exception as e: st.error(f"فایل معتبر نیست: {e}")

# ================== ناوبری ==================
nav_options = ["overview", "journal", "usd", "gold"] + [f"asset_{a['id']}" for a in assets] + ["settings"]
nav_labels = {
    "overview": f"{NAV_EMOJI['overview']} {NAV_LABELS['overview']}",
    "journal": f"{NAV_EMOJI['journal']} {NAV_LABELS['journal']}",
    "usd": f"{NAV_EMOJI['usd']} {NAV_LABELS['usd']}",
    "gold": f"{NAV_EMOJI['gold']} {NAV_LABELS['gold']}",
    "settings": f"{NAV_EMOJI['settings']} {NAV_LABELS['settings']}",
}
for a in assets: nav_labels[f"asset_{a['id']}"] = f"{asset_overview_emoji(a)} {a['name']}"

if "nav_version" not in st.session_state: st.session_state.nav_version = 0
if "pending_nav" in st.session_state:
    pending = st.session_state.pending_nav
    del st.session_state.pending_nav
    if pending in nav_options:
        st.session_state.nav_version += 1
        st.session_state[f"nav_pills_v{st.session_state.nav_version}"] = pending

_widget_key = f"nav_pills_v{st.session_state.nav_version}"
if _widget_key not in st.session_state: st.session_state[_widget_key] = "overview"
if st.session_state[_widget_key] not in nav_options: st.session_state[_widget_key] = "overview"

if hasattr(st, "pills"):
    selected = st.pills("ناوبری", options=nav_options, format_func=lambda x: nav_labels.get(x, x),
                       selection_mode="single", label_visibility="collapsed", key=_widget_key)
    if selected is None: selected = st.session_state[_widget_key]
else:
    selected = st.radio("ناوبری", options=nav_options, format_func=lambda x: nav_labels.get(x, x),
                       horizontal=True, label_visibility="collapsed", key=_widget_key + "_radio")

# ================== صفحه تنظیمات ==================
def render_settings_page(data):
    st.header("⚙️ تنظیمات")
    settings = get_settings(data)
    all_fonts = get_all_fonts(data)
    dark = settings["dark_mode"]
    t_font, t_nav, t_assets, t_emoji, t_lib, t_verify, t_storage = st.tabs([
        "🔤 فونت", "🎨 آیکون منو", "📦 آیکون دارایی", "😀 ایموجی", "📚 کتابخانه", "🔍 تأیید ذخیره", "💾 وضعیت"])

    with t_font:
        st.subheader("🔤 فونت برنامه")
        font_keys = list(all_fonts.keys())
        cur_font = settings["font"] if settings["font"] in font_keys else "vazirmatn"
        c1, c2 = st.columns([3, 1])
        new_font = c1.selectbox("فونت", font_keys, index=font_keys.index(cur_font),
                               format_func=lambda k: all_fonts[k]["name"] + (" (سفارشی)" if not all_fonts[k]["builtin"] else ""),
                               key="font_select_v2")
        if c2.button("💾 ذخیره فونت", use_container_width=True, key="apply_font_btn"):
            data["settings"]["font"] = new_font
            st.session_state.data = data; save_all(data); st.rerun()
        preview_family = all_fonts[new_font]["family"]
        bg_prev = "#161b22" if dark else "#f9fafb"; border_prev = "#30363d" if dark else "#3b82f6"
        st.markdown(
            f'<div style="padding:20px; border:2px solid {border_prev}; border-radius:10px; margin:16px 0; background:{bg_prev}; direction:rtl;">'
            f'<div style="font-family:\'{preview_family}\', Tahoma; font-size:1.8rem;">داشبورد مالی — ۱۲۳۴۵</div>'
            f'<div style="font-family:\'{preview_family}\', Tahoma; font-size:1.05rem;">متن نمونه: ۱۲۳۴۵۶۷۸۹۰ | 1234567890</div></div>',
            unsafe_allow_html=True)
        st.divider()
        st.subheader("📤 بارگذاری فونت سفارشی")
        st.caption("TTF, OTF, WOFF, WOFF2 — حداکثر ۱۰MB")
        with st.form("upload_font_form", clear_on_submit=True):
            uploaded_file = st.file_uploader("فایل", type=["ttf", "otf", "woff", "woff2"], key="custom_font_uploader")
            display_name = st.text_input("نام نمایشی")
            if st.form_submit_button("📤 بارگذاری", use_container_width=True):
                if uploaded_file is None: st.error("فایل انتخاب کنید.")
                elif uploaded_file.size > 10 * 1024 * 1024: st.error("حجم بیش از ۱۰MB.")
                else:
                    try:
                        fb = uploaded_file.read()
                        ext = uploaded_file.name.lower().rsplit(".", 1)[-1]
                        fmap = {"ttf": "truetype", "otf": "opentype", "woff": "woff", "woff2": "woff2"}
                        mmap = {"ttf": "font/ttf", "otf": "font/otf", "woff": "font/woff", "woff2": "font/woff2"}
                        base_name = uploaded_file.name.rsplit(".", 1)[0]
                        safe = re.sub(r"[^a-z0-9_]", "_", base_name.lower())[:40]
                        fkey = f"custom_{safe}"; c = 1; orig = fkey
                        existing = data["settings"].get("custom_fonts", {})
                        while fkey in existing: c += 1; fkey = f"{orig}_{c}"
                        data["settings"].setdefault("custom_fonts", {})[fkey] = {
                            "display_name": (display_name.strip() or base_name)[:60],
                            "data": base64.b64encode(fb).decode(),
                            "format": fmap.get(ext, "truetype"), "mime": mmap.get(ext, "font/ttf"),
                            "filename": uploaded_file.name, "size_bytes": len(fb),
                            "uploaded_at": datetime.now().isoformat()}
                        st.session_state.data = data; save_all(data)
                        st.success("✅ بارگذاری شد."); st.rerun()
                    except Exception as e: st.error(f"خطا: {e}")
        custom_fonts = data["settings"].get("custom_fonts", {})
        if custom_fonts:
            st.divider(); st.subheader("📚 فونت‌های سفارشی")
            for key, info in list(custom_fonts.items()):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
                    c1.markdown(f'<div style="text-align:center; font-family:\'{key}\', Tahoma; font-size:2.2rem; color:#3b82f6;">آ</div>', unsafe_allow_html=True)
                    c2.markdown(f"**{info.get('display_name', key)}**")
                    c2.caption(f"{info.get('size_bytes', 0) // 1024:,} KB")
                    c3.success("✅ فعال") if settings["font"] == key else c3.caption(f"`{key[:25]}`")
                    if c4.button("🗑️", key=f"del_font_{key}"):
                        del data["settings"]["custom_fonts"][key]
                        if data["settings"]["font"] == key: data["settings"]["font"] = "vazirmatn"
                        st.session_state.data = data; save_all(data); st.rerun()

    with t_nav:
        st.subheader("🎨 آیکون منو")
        st.caption("روی هر آیکون کلیک کنید. ✅ = فعلی")
        for nav_key in ["overview", "journal", "usd", "gold", "settings"]:
            cfg = settings["nav_icons"].get(nav_key, DEFAULT_NAV_ICONS[nav_key])
            with st.container(border=True):
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.markdown(f'<div style="text-align:center; padding:10px;"><i class="fa-solid {cfg["icon"]}" style="color:{cfg["color"]}; font-size:2.5rem;"></i></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{NAV_LABELS[nav_key]}**")
                    new_color = st.color_picker("رنگ", value=cfg["color"], key=f"color_nav_{nav_key}")
                with st.expander("🖼️ انتخاب آیکون از گرید"):
                    def _save_nav(icon_class, _k=nav_key):
                        current_color = data["settings"]["nav_icons"].get(_k, DEFAULT_NAV_ICONS[_k])["color"]
                        data["settings"]["nav_icons"][_k] = {"icon": icon_class, "color": current_color}
                        st.session_state.data = data; save_all(data)
                    _icon_grid_picker(f"nav_{nav_key}", cfg["icon"], _save_nav)
                if st.button("💾 ذخیره رنگ", key=f"save_nav_{nav_key}", use_container_width=True):
                    data["settings"]["nav_icons"][nav_key] = {"icon": cfg["icon"], "color": new_color}
                    st.session_state.data = data; save_all(data); st.rerun()

    with t_assets:
        st.subheader("📦 آیکون دارایی‌ها")
        if not assets: st.info("هنوز دارایی‌ای ثبت نشده.")
        else:
            for a in assets:
                cur_ic, cur_col = asset_icon(a), asset_color(a)
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        st.markdown(f'<div style="text-align:center; padding:10px;"><i class="fa-solid {cur_ic}" style="color:{cur_col}; font-size:2.5rem;"></i></div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**{a['name']}**")
                        new_color = st.color_picker("رنگ", value=cur_col, key=f"color_asset_{a['id']}")
                    with st.expander("🖼️ انتخاب آیکون از گرید"):
                        def _save_asset(icon_class, _id=a["id"]):
                            for i, x in enumerate(data["assets"]):
                                if x["id"] == _id: data["assets"][i]["icon"] = icon_class; break
                            st.session_state.data = data; save_all(data)
                        _icon_grid_picker(f"asset_{a['id']}", cur_ic, _save_asset)
                    if st.button("💾 ذخیره رنگ", key=f"save_asset_{a['id']}", use_container_width=True):
                        for i, x in enumerate(data["assets"]):
                            if x["id"] == a["id"]: data["assets"][i]["color"] = new_color; break
                        st.session_state.data = data; save_all(data); st.rerun()

    with t_emoji:
        st.subheader("😀 ایموجی نمای کلی")
        if not assets: st.info("هنوز دارایی‌ای ثبت نشده.")
        else:
            for a in assets:
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        st.markdown(f'<div style="text-align:center; font-size:2.8rem; padding:8px;">{asset_overview_emoji(a)}</div>', unsafe_allow_html=True)
                    with c2:
                        status = f"`{a['overview_emoji']}`" if a.get("overview_emoji") else "خودکار"
                        st.markdown(f"**{a['name']}** — {status}")
                    with st.expander("🖼️ انتخاب ایموجی"):
                        def _save_em(v, _id=a["id"]):
                            for i, x in enumerate(data["assets"]):
                                if x["id"] == _id: data["assets"][i]["overview_emoji"] = v; break
                            st.session_state.data = data; save_all(data)
                        _emoji_grid_picker(f"emoji_{a['id']}", a.get("overview_emoji", ""), _save_em)

    with t_lib:
        icons = load_fa_icons()
        st.caption(f"**{len(icons)}** آیکون FA")
        s = st.text_input("🔍 جستجو", key="fa_lib_search")
        filtered = [ic for ic in icons if s.lower() in ic["label"].lower() or s.lower() in ic["class"].lower()] if s else icons
        display = filtered[:120]
        for i in range(0, len(display), 8):
            cols = st.columns(8)
            for j, ic in enumerate(display[i:i + 8]):
                with cols[j]:
                    st.markdown(
                        f'<div style="text-align:center; padding:8px; border:1px solid #e5e7eb; border-radius:6px;" title="{ic["class"]}">'
                        f'<i class="fa-solid {ic["class"]}" style="font-size:1.4rem; color:#3b82f6;"></i>'
                        f'<div style="font-size:0.6rem; color:#6b7280; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{ic["label"]}</div></div>',
                        unsafe_allow_html=True)

    with t_verify:
        st.subheader("🔍 تأیید ذخیره")
        if data.get("last_saved"): st.info(f"📅 آخرین: {data.get('last_saved_jalali', '—')}")
        else: st.warning("هنوز ذخیره‌ای انجام نشده")
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔍 تأیید", use_container_width=True, key="verify_gh_btn"):
                v_ok, v_msg, sha = verify_github_save(data)
                (st.success if v_ok else st.error)(f"{'✅' if v_ok else '❌'} {v_msg}")
        with col2:
            if st.button("🔄 بارگذاری از GitHub", use_container_width=True, key="force_load_btn"):
                gh = load_github_file()
                if gh:
                    st.session_state.data = migrate_data(gh)
                    save_local_file(st.session_state.data)
                    st.success("✅ بارگذاری شد"); st.rerun()
                else: st.error("❌ ناموفق")
        with col3:
            if st.button("💾 ذخیره فوری", use_container_width=True, key="force_save_btn"):
                if save_all(data): st.rerun()
        st.divider()
        gh = load_github_file()
        if gh:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**حافظه:**")
                st.caption(f"دارایی: {len(data.get('assets', []))}")
                st.caption(f"صندوق طلا: {len(data.get('gold_funds', []))}")
                st.caption(f"last_saved: {data.get('last_saved', '—')[:19]}")
            with c2:
                st.markdown("**GitHub:**")
                st.caption(f"دارایی: {len(gh.get('assets', []))}")
                st.caption(f"صندوق طلا: {len(gh.get('gold_funds', []))}")
                st.caption(f"last_saved: {gh.get('last_saved', '—')[:19]}")
            if data.get("last_saved") == gh.get("last_saved"): st.success("✅ یکسان")
            else: st.warning("⚠️ متفاوت — ذخیره فوری بزنید")

    with t_storage:
        st.subheader("💾 وضعیت")
        local_ok = os.path.exists(DATA_FILE)
        if local_ok:
            _sz = os.path.getsize(DATA_FILE); _sz_kb = _sz / 1024; _est_gz = _sz_kb * 0.1
            if _sz_kb > 10240: st.error(f"⚠️ فایل {_sz_kb:,.0f} KB — بسیار بزرگ! GitHub gz: ~{_est_gz:,.0f} KB")
            elif _sz_kb > 5120: st.warning(f"⚠️ فایل {_sz_kb:,.0f} KB — بزرگ. GitHub gz: ~{_est_gz:,.0f} KB")
            else: st.info(f"📦 فایل محلی: **{_sz_kb:,.1f} KB** — GitHub gz تخمینی: **~{_est_gz:,.1f} KB**")
        gh_status, gh_msg = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📁 محلی**")
            st.success(f"✅ ({os.path.getsize(DATA_FILE):,} بایت)") if local_ok else st.error("❌ یافت نشد")
        with c2:
            st.markdown("**☁️ GitHub (gzip)**")
            st.success(f"✅ {gh_msg}") if gh_status == "ok" else st.error(f"❌ {gh_msg}")
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("دارایی‌ها", len(data.get("assets", [])))
        c2.metric("رکوردها", sum(len(a.get("records", [])) for a in data.get("assets", [])))
        c3.metric("نرخ دلار", len(data.get("usd_rates", [])))
        c4.metric("صندوق طلا", len(data.get("gold_funds", [])))

# ================== صفحه نمای کلی ==================
if selected == "overview":
    st.header("📊 نمای کلی دارایی‌ها")
    rate, _ = get_current_usd_rate(data)
    if not assets: st.info("هنوز دارایی‌ای ثبت نشده.")
    else:
        rows = []; total_usd = 0.0
        for a in assets:
            value, usd_val, rec = compute_asset_value(a, rate)
            if usd_val is not None: total_usd += usd_val
            rows.append({"دارایی": f"{asset_overview_emoji(a)} {a['name']}", "ارز": currency_label(a["currency"]),
                         "تعداد": rec["quantity"] if rec else 0, "قیمت واحد": rec["unit_price"] if rec else 0,
                         "ارزش": value, "معادل_دلاری": usd_val, "آخرین_تاریخ": rec["date_jalali"] if rec else "—"})
        df = pd.DataFrame(rows)
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 کل ارزش (دلاری)", f"${total_usd:,.2f}")
        c2.metric("📁 دارایی‌ها", len(assets))
        c3.metric("💵 نرخ دلار", f"{rate:,.0f} ریال" if rate else "ثبت نشده")
        st.subheader("🥧 ترکیب")
        pie_df = df.dropna(subset=["معادل_دلاری"]); pie_df = pie_df[pie_df["معادل_دلاری"] > 0]
        if not pie_df.empty:
            fig = px.pie(pie_df, values="معادل_دلاری", names="دارایی", hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=14, color="#e6edf3" if _dark else "#1f2937"),
                             legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                             margin=dict(t=20, b=20, l=10, r=10),
                             paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                             plot_bgcolor="rgba(0,0,0,0)" if _dark else "white")
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("📈 روند رشد")
        timeline = build_portfolio_timeline(data)
        if len(timeline) >= 2:
            for metric_key, title, color in [("total_usd", "💵 ارزش به دلار", "#3b82f6"), ("total_irr", "🇮🇷 ارزش به ریال", "#10b981")]:
                fig = px.line(timeline, x="date_jalali", y=metric_key, markers=True,
                             labels={"date_jalali": "تاریخ", metric_key: title}, color_discrete_sequence=[color])
                fig.update_traces(line=dict(width=3), marker=dict(size=7))
                fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13, color="#e6edf3" if _dark else "#1f2937"),
                                 yaxis=dict(tickformat=",.0f"), xaxis=dict(title="تاریخ"),
                                 margin=dict(t=30, b=20), hovermode="x unified",
                                 paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                                 plot_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                                 title=dict(text=title, font=dict(size=14)))
                st.plotly_chart(fig, use_container_width=True)
            fu, lu = timeline["total_usd"].iloc[0], timeline["total_usd"].iloc[-1]
            fi, li = timeline["total_irr"].iloc[0], timeline["total_irr"].iloc[-1]
            g1, g2 = st.columns(2)
            g1.metric("تغییر دلاری", f"${lu:,.2f}", delta=f"{lu-fu:+,.2f}")
            g2.metric("تغییر ریالی", f"{li:,.0f}", delta=f"{li-fi:+,.0f}")
        else: st.info("حداقل دو رکورد لازم است.")
        st.subheader("📋 جدول دارایی‌ها")
        disp = df.copy()
        disp["تعداد"] = disp["تعداد"].apply(fmt_num)
        disp["قیمت واحد"] = disp.apply(lambda r: f"{fmt_num(r['قیمت واحد'])} {r['ارز']}" if r['قیمت واحد'] else "—", axis=1)
        disp["ارزش"] = disp.apply(lambda r: f"{fmt_num(r['ارزش'])} {r['ارز']}" if r['ارزش'] else "—", axis=1)
        disp["معادل_دلاری"] = disp["معادل_دلاری"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
        disp = disp[["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل_دلاری", "آخرین_تاریخ"]]
        disp.columns = ["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل دلاری", "آخرین بروزرسانی"]
        render_html_table(disp, dark=_dark)

# ================== صفحه افزودن دارایی ==================
elif selected == "journal":
    st.header("+ افزودن دارایی")
    all_icons = load_fa_icons()
    all_classes = [ic["class"] for ic in all_icons]
    labels_map = {ic["class"]: f'{ic["label"]} ({ic["class"]})' for ic in all_icons}
    with st.container(border=True):
        st.subheader("➕ ثبت دارایی جدید")
        with st.form("add_asset_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            name = c1.text_input("نام", placeholder="طلا، سهام...")
            cur = c2.selectbox("ارز", ["IRR", "USD"], format_func=lambda x: "ریال" if x == "IRR" else "دلار")
            init_icon = c3.selectbox("آیکون", all_classes,
                                     index=all_classes.index("fa-coins") if "fa-coins" in all_classes else 0,
                                     format_func=lambda c: labels_map.get(c, c), key="new_asset_icon")
            init_color = st.color_picker("رنگ آیکون", value="#3b82f6", key="new_asset_color")
            st.markdown("**📝 رکورد اولیه (اختیاری)**")
            c6, c7, c8 = st.columns([2, 2, 3])
            q0 = c6.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
            p0 = c7.number_input("قیمت واحد", min_value=0.0, format="%.2f", step=1000.0)
            note0 = c8.text_input("توضیح")
            if st.form_submit_button("💾 ایجاد", use_container_width=True):
                if not name.strip(): st.error("نام را وارد کنید.")
                else:
                    aid = _short_id()
                    records = []
                    if q0 > 0 and p0 > 0:
                        records.append({"id": aid + "_r0", "date_gregorian": datetime.now().isoformat(), "date_jalali": today_jalali_str(),
                                       "quantity": q0, "unit_price": p0, "note": note0.strip() or "رکورد اولیه"})
                    data.setdefault("assets", []).append({
                        "id": aid, "name": name.strip(), "icon": init_icon, "color": init_color,
                        "overview_emoji": "", "currency": cur,
                        "created_at_gregorian": datetime.now().isoformat(), "created_at_jalali": today_jalali_str(),
                        "records": records})
                    st.session_state.data = data; save_all(data)
                    st.session_state.pending_nav = f"asset_{aid}"; st.rerun()
    if assets:
        st.subheader("📝 لیست دارایی‌ها")
        rate, _ = get_current_usd_rate(data)
        for a in assets:
            value, _, rec = compute_asset_value(a, rate)
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 3, 2, 1])
                c1.markdown(f'**<i class="fa-solid {asset_icon(a)}" style="color:{asset_color(a)};"></i> {a["name"]}**', unsafe_allow_html=True)
                c2.caption(currency_label(a["currency"]))
                c3.caption(f"آخرین: {rec['date_jalali'] if rec else '—'}")
                c4.write(f"{fmt_num(value)} {currency_label(a['currency'])}" if value else "—")
                if c5.button("🗑️", key=f"del_asset_{a['id']}"):
                    data["assets"] = [x for x in data["assets"] if x["id"] != a["id"]]
                    st.session_state.data = data; save_all(data)
                    st.session_state.pending_nav = "overview"; st.rerun()

# ================== صفحه دلار ==================
elif selected == "usd":
    st.header("💵 نرخ دلار")
    st.caption(f"📅 {today_jalali_str()}")
    with st.container(border=True):
        st.subheader("➕ ثبت نرخ")
        with st.form("usd_rate_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 3])
            new_rate = c1.number_input("نرخ (ریال)", min_value=0, step=1000, format="%d")
            note = c2.text_input("توضیح")
            if st.form_submit_button("💾 ثبت", use_container_width=True):
                if new_rate > 0:
                    now = datetime.now().isoformat()
                    data.setdefault("usd_rates", []).append({
                        "id": _short_id(), "rate": new_rate, "note": note.strip(),
                        "created_at": now, "created_at_jalali": today_jalali_str()})
                    _u, _m = sync_usd_rates_to_gold_funds(data)
                    if _u > 0: st.toast(f"🔄 {_u} رکورد صندوق طلا همگام شد", icon="✅")
                    st.session_state.data = data; save_all(data); st.rerun()
    rates = data.get("usd_rates", [])
    if rates:
        sorted_r = sorted(rates, key=lambda x: x.get("created_at", ""))
        current, current_date = get_current_usd_rate(data)
        c1, c2, c3 = st.columns(3)
        c1.metric("نرخ فعلی", f"{current:,.0f} ریال")
        c2.metric("تعداد", len(rates))
        c3.metric("آخرین", current_date or "—")
        st.subheader("📈 روند")
        chart_df = pd.DataFrame(sorted_r); chart_df["تاریخ"] = chart_df["created_at_jalali"]
        fig = px.line(chart_df, x="تاریخ", y="rate", markers=True, labels={"تاریخ": "تاریخ", "rate": "نرخ"})
        fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13, color="#e6edf3" if _dark else "#1f2937"),
                         margin=dict(t=20, b=20),
                         paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                         plot_bgcolor="rgba(0,0,0,0)" if _dark else "white")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 تاریخچه")
        for r in reversed(sorted_r):
            with st.container(border=True):
                c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 3, 3, 1, 1])
                c1.markdown(f"**{r['rate']:,.0f} ریال**")
                c2.caption(f"📅 {r.get('created_at_jalali', '—')}")
                c3.caption(r.get("note", "—") or "—")
                c4.caption(iso_to_jalali(r.get("created_at", ""), with_time=True))
                if c5.button("✏️", key=f"edit_btn_rate_{r['id']}"):
                    st.session_state[f"edit_open_rate_{r['id']}"] = not st.session_state.get(f"edit_open_rate_{r['id']}", False)
                if c6.button("🗑️", key=f"delrate_{r['id']}"):
                    data["usd_rates"] = [x for x in data["usd_rates"] if x["id"] != r["id"]]
                    _u, _m = sync_usd_rates_to_gold_funds(data)
                    if _u > 0: st.toast(f"🔄 {_u} رکورد صندوق طلا بازمحاسبه شد", icon="✅")
                    if _m > 0: st.warning(f"⚠️ {_m} رکورد صندوق طلا بدون نرخ معتبر")
                    st.session_state.data = data; save_all(data); st.rerun()
                if st.session_state.get(f"edit_open_rate_{r['id']}", False):
                    vk = f"v_rate_{r['id']}"
                    fk = f"edit_rate_{r['id']}_v{get_version(vk)}"
                    with st.form(fk):
                        ec1, ec2 = st.columns([2, 3])
                        er_date = ec1.text_input("تاریخ", value=r.get("created_at_jalali", today_jalali_str()))
                        er_rate = ec2.number_input("نرخ", value=int(r["rate"]), min_value=1, step=1000, format="%d")
                        er_note = st.text_input("توضیح", value=r.get("note", ""))
                        if st.form_submit_button("💾 ذخیره", use_container_width=True):
                            jd = parse_jalali(er_date)
                            if jd and er_rate > 0:
                                tp = r["created_at"][11:16] if len(r.get("created_at", "")) >= 16 else "00:00"
                                giso = jalali_to_gregorian_iso(jd, tp)
                                for i, x in enumerate(data["usd_rates"]):
                                    if x["id"] == r["id"]:
                                        data["usd_rates"][i] = {"id": r["id"], "rate": er_rate, "note": er_note.strip(),
                                                               "created_at": giso, "created_at_jalali": jd.strftime("%Y/%m/%d")}
                                        break
                                _u, _m = sync_usd_rates_to_gold_funds(data)
                                if _u > 0: st.toast(f"🔄 {_u} رکورد صندوق طلا همگام شد", icon="✅")
                                if _m > 0: st.warning(f"⚠️ {_m} رکورد بدون نرخ معتبر")
                                st.session_state.data = data
                                st.session_state[f"edit_open_rate_{r['id']}"] = False
                                bump_version(vk); save_all(data); st.rerun()

# ================== 🥇 صفحه صندوق‌های طلا ==================
elif selected == "gold":
    st.header("🥇 صندوق‌های طلا")
    st.caption(f"📅 {today_jalali_str()}")

    # ✅ اندازه فونت تابلوها = ۳۲px
        st.markdown("""
    <style>
        [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"],
        [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] *,
        [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] p,
        [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] div,
        [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] span {
            font-size: 2rem !important;
            line-height: 1.2 !important;
            font-weight: 600 !important;
        }
        [data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"],
        [data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] *,
        [data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] p {
            font-size: 0.8rem !important;
            font-weight: 500 !important;
        }
        [data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"],
        [data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"] *,
        [data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"] p {
            font-size: 0.72rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

    _sync_u, _sync_m = sync_usd_rates_to_gold_funds(data)
    if _sync_u > 0:
        st.session_state.data = data
    if _sync_m > 0:
        st.warning(f"⚠️ {_sync_m} رکورد تاریخشان قبل از اولین نرخ دلار ثبت شده است.")

    with st.container(border=True):
        st.subheader("➕ افزودن صندوق جدید")
        with st.form("add_gold_fund_form", clear_on_submit=True):
            c1, c2 = st.columns([3, 2])
            fund_name = c1.text_input("نام صندوق", placeholder="طلا، عیار، لوتوس، ...")
            fund_icon = c2.text_input("ایموجی", value="🥇", max_chars=4)
            if st.form_submit_button("💾 ایجاد صندوق", use_container_width=True):
                if not fund_name.strip():
                    st.error("نام صندوق را وارد کنید.")
                else:
                    fid = _short_id()
                    data.setdefault("gold_funds", []).append({
                        "id": fid, "name": fund_name.strip(),
                        "icon": (fund_icon.strip() or "🥇")[:4],
                        "created_at": datetime.now().isoformat(), "records": []})
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()

    gold_funds = data.get("gold_funds", [])
    usd_rate_current, usd_rate_date = get_current_usd_rate(data)

    if not gold_funds:
        st.info("هنوز صندوقی اضافه نشده.")
    else:
        for fund in gold_funds:
            st.markdown(f"### {fund.get('icon', '🥇')} {fund['name']}")
            records = fund.get("records", [])

            # ============ هشدار تله دلار ============
            _trap = dollar_trap_analysis(fund, days=30)
            if _trap and _trap["gap"] > 10:
                st.warning(f"""
⚠️ **هشدار تله دلار** — در {_trap['days']} روز گذشته ({_trap['older_date']} تا {_trap['last_date']}):
- نرخ دلار: **{_trap['usd_change']:+.1f}%**
- انس طلا: **{_trap['ounce_change']:+.1f}%**
- **شکاف: {_trap['gap']:+.1f}%**

🔴 **اگر الان صندوق را بفروشی و دلار نخری، سود دلاری‌ات از بین می‌رود.** برای فروش، **حتماً همزمان دلار بخر**.
""")

            # ============ متریک‌ها ============
            analytics = gold_fund_analytics(fund)
            prices = [r["unit_price"] for r in records if r.get("unit_price", 0) > 0]
            units_list = []
            for r in records:
                if r.get("unit_price", 0) > 0 and r.get("usd_rate_used", 0) > 0 and r.get("ounce_price_usd", 0) > 0:
                    units_list.append((r["ounce_price_usd"] * r["usd_rate_used"]) / r["unit_price"])

            if prices:
                st.markdown("**💰 قیمت واحد صندوق**")
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("📉 کمترین قیمت", f"{min(prices):,.0f} ریال")
                mc2.metric("📊 میانگین قیمت", f"{sum(prices) / len(prices):,.0f} ریال")
                mc3.metric("📈 بیشترین قیمت", f"{max(prices):,.0f} ریال")
                mc4.metric("📋 تعداد رکورد", len(records))

                if units_list:
                    st.markdown("**📦 تعداد واحد مورد نیاز (برای یک انس)**")
                    u1, u2, u3, u4 = st.columns(4)
                    u1.metric("📉 کمترین واحد", f"{min(units_list):,.0f}")
                    u2.metric("📊 میانگین واحد", f"{sum(units_list) / len(units_list):,.0f}")
                    u3.metric("📈 بیشترین واحد", f"{max(units_list):,.0f}")
                    avg_price = sum(prices) / len(prices)
                    avg_units = sum(units_list) / len(units_list)
                    u4.metric("📊 میانگین ارزش", f"{avg_units * avg_price:,.0f} ریال", help="میانگین واحد × میانگین قیمت")

                if analytics and analytics[-1]["usd_equivalent"] is not None:
                    st.markdown("**💵 تحلیل دلاری**")
                    a1, a2, a3, a4 = st.columns(4)
                    last_a = analytics[-1]
                    first_usd = analytics[0]["usd_equivalent"]
                    a1.metric("💵 معادل دلاری فعلی", f"${last_a['usd_equivalent']:,.4f}")
                    if last_a["usd_return_pct"] is not None:
                        a2.metric("📈 بازده دلاری از خرید", f"{last_a['usd_return_pct']:+.1f}%",
                                  delta=f"${last_a['usd_equivalent'] - first_usd:+.4f}" if first_usd else None)
                    if last_a["gram_per_unit"]:
                        avg_gram = sum([r["gram_per_unit"] for r in analytics if r["gram_per_unit"]]) / len([r for r in analytics if r["gram_per_unit"]])
                        premium_pct = (last_a["gram_per_unit"] / avg_gram - 1) * 100 if avg_gram else 0
                        a3.metric("⚖️ گرم/واحد", f"{last_a['gram_per_unit']*1000:.3f} mg",
                                  delta=f"{premium_pct:+.1f}% vs avg")
                    a4.metric("📊 سیگنال انس", ounce_signal(fund).split("—")[0].strip())
                    st.caption(f"**سیگنال فعلی:** {ounce_signal(fund)}")
            else:
                st.caption("هنوز رکوردی ثبت نشده.")

            # ============ ماشین‌حساب آربیتراژ ============
            if len(records) >= 1:
                with st.expander("🧮 ماشین‌حساب آربیتراژ دلاری (فروش صندوق → خرید دلار → خرید مجدد)"):
                    if usd_rate_current is None:
                        st.warning("ابتدا نرخ دلار را در صفحه «💵 دلار» ثبت کنید.")
                    else:
                        st.caption(f"نرخ دلار فعلی: **{usd_rate_current:,.0f} ریال**")
                        calc_c1, calc_c2, calc_c3, calc_c4 = st.columns(4)
                        calc_units = calc_c1.number_input("تعداد واحد برای فروش", min_value=0.0, value=1.0, step=1.0, key=f"calc_units_{fund['id']}")
                        calc_sell = calc_c2.number_input("قیمت فروش (ریال)", min_value=0.0,
                                                          value=float(records[-1]["unit_price"]), step=1000.0, key=f"calc_sell_{fund['id']}")
                        calc_rebuy_rate = calc_c3.number_input("نرخ دلار پیش‌بینی برای خرید مجدد", min_value=0.0,
                                                                value=float(usd_rate_current), step=1000.0, key=f"calc_rebuy_rate_{fund['id']}")
                        calc_rebuy = calc_c4.number_input("قیمت خرید مجدد (ریال)", min_value=0.0,
                                                           value=float(records[-1]["unit_price"]), step=1000.0, key=f"calc_rebuy_{fund['id']}")
                        st.markdown("**کارمزدها**")
                        fee_c1, fee_c2, fee_c3 = st.columns(3)
                        fee_sell_pct = fee_c1.number_input("کارمزد فروش صندوق (%)", min_value=0.0, value=0.5, step=0.1, key=f"fee_sell_{fund['id']}")
                        fee_usd_pct = fee_c2.number_input("اسپرد دلار (% هر طرف)", min_value=0.0, value=1.0, step=0.1, key=f"fee_usd_{fund['id']}")
                        fee_buy_pct = fee_c3.number_input("کارمزد خرید صندوق (%)", min_value=0.0, value=0.5, step=0.1, key=f"fee_buy_{fund['id']}")

                        if calc_units > 0 and calc_sell > 0 and calc_rebuy_rate > 0 and calc_rebuy > 0:
                            gross_irr = calc_units * calc_sell * (1 - fee_sell_pct / 100)
                            dollars = gross_irr / (calc_rebuy_rate * (1 + fee_usd_pct / 100))
                            irr_back = dollars * calc_rebuy_rate * (1 - fee_usd_pct / 100)
                            new_units = (irr_back / calc_rebuy) * (1 - fee_buy_pct / 100)
                            net_units = new_units - calc_units
                            net_irr = net_units * calc_rebuy
                            st.divider()
                            r1, r2, r3 = st.columns(3)
                            r1.metric("💵 دلار به‌دست‌آمده", f"${dollars:,.4f}")
                            r2.metric("📦 واحد پس از خرید مجدد", f"{new_units:,.4f}")
                            if net_units > 0:
                                r3.metric("✅ سود خالص", f"+{net_units:,.4f} واحد", delta=f"{net_irr:+,.0f} ریال")
                                st.success(f"✅ سودآور: **{net_units:,.4f} واحد** بیشتر (معادل {net_irr:,.0f} ریال)")
                            else:
                                r3.metric("❌ ضرر خالص", f"{net_units:,.4f} واحد", delta=f"{net_irr:+,.0f} ریال")
                                st.error(f"❌ ضرر: {abs(net_units):,.4f} واحد از دست می‌رود")
                            if 0 < net_units < calc_units * 0.05:
                                st.info("💡 سود کمتر از ۵٪ — با کارمزد واقعی، ارزش ریسک ندارد.")

            # ============ افزودن رکورد ============
            with st.expander(f"➕ افزودن رکورد برای {fund['name']}", expanded=(len(records) == 0)):
                if usd_rate_current is None:
                    st.warning("⚠️ ابتدا نرخ دلار را در صفحه «💵 دلار» ثبت کنید.")
                else:
                    st.caption(f"نرخ دلار فعلی: **{usd_rate_current:,.0f} ریال** ({usd_rate_date})")
                    cg1, cg2, cg3 = st.columns([2, 2, 2])
                    g_date = cg1.text_input("تاریخ (شمسی)", value=today_jalali_str(), key=f"gdate_{fund['id']}")
                    g_price = cg2.number_input("قیمت واحد (ریال)", min_value=0.0, format="%.0f", step=1000.0, key=f"gprice_{fund['id']}")
                    g_ounce = cg3.number_input("انس طلا (دلار)", min_value=0.0, format="%.2f", step=1.0, value=2000.0, key=f"gounce_{fund['id']}")
                    g_note = st.text_input("توضیح (اختیاری)", key=f"gnote_{fund['id']}")
                    if g_price > 0 and g_ounce > 0:
                        units_needed = (g_ounce * usd_rate_current) / g_price
                        usd_equiv = g_price / usd_rate_current if usd_rate_current > 0 else 0
                        st.success(f"📊 **واحد برای ۱ انس:** {units_needed:,.0f} واحد | **معادل دلاری:** ${usd_equiv:.4f}")
                    if st.button("💾 ثبت رکورد", key=f"gsave_{fund['id']}", use_container_width=True):
                        jd = parse_jalali(g_date)
                        if jd is None:
                            st.error("تاریخ نامعتبر.")
                        elif g_price <= 0 or g_ounce <= 0:
                            st.error("مقادیر باید > 0 باشند.")
                        else:
                            giso = jalali_to_gregorian_iso(jd, datetime.now().strftime("%H:%M"))
                            fund.setdefault("records", []).append({
                                "id": _short_id(), "date_gregorian": giso,
                                "date_jalali": jd.strftime("%Y/%m/%d"),
                                "unit_price": g_price, "ounce_price_usd": g_ounce,
                                "usd_rate_used": usd_rate_current, "note": g_note.strip()})
                            st.session_state.data = data
                            save_all(data)
                            for k in [f"gdate_{fund['id']}", f"gprice_{fund['id']}", f"gounce_{fund['id']}", f"gnote_{fund['id']}"]:
                                st.session_state.pop(k, None)
                            st.rerun()

            # ============ نمودار سه‌خطی نرمال‌شده ============
            if len(records) >= 2 and analytics:
                st.markdown("**📈 نمودار مقایسه‌ای (نرمال‌شده به ۱۰۰)**")
                st.caption("آبی بالا + سبز پایین = تله دلار | نارنجی نقطه‌چین = روند انس جهانی")
                valid = [a for a in analytics if a["usd_equivalent"] is not None and a["record"].get("ounce_price_usd", 0) > 0]
                if len(valid) >= 2:
                    base_irr = valid[0]["record"]["unit_price"]
                    base_usd = valid[0]["usd_equivalent"]
                    base_ounce = valid[0]["record"]["ounce_price_usd"]
                    dates = [a["record"]["date_jalali"] for a in valid]
                    irr_index = [(a["record"]["unit_price"] / base_irr) * 100 for a in valid]
                    usd_index = [(a["usd_equivalent"] / base_usd) * 100 for a in valid]
                    ounce_index = [(a["record"]["ounce_price_usd"] / base_ounce) * 100 for a in valid]
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=dates, y=irr_index, mode="lines+markers", name="قیمت ریالی",
                                             line=dict(color="#3b82f6", width=3), marker=dict(size=7)))
                    fig.add_trace(go.Scatter(x=dates, y=usd_index, mode="lines+markers", name="معادل دلاری",
                                             line=dict(color="#10b981", width=3), marker=dict(size=7)))
                    fig.add_trace(go.Scatter(x=dates, y=ounce_index, mode="lines+markers", name="انس طلا",
                                             line=dict(color="#f59e0b", width=2, dash="dot"), marker=dict(size=6)))
                    fig.update_layout(
                        font=dict(family="Vazirmatn, Tahoma", size=13, color="#e6edf3" if _dark else "#1f2937"),
                        yaxis=dict(title="شاخص (پایه=۱۰۰)", tickformat=".0f"),
                        xaxis=dict(title="تاریخ"), margin=dict(t=30, b=20),
                        hovermode="x unified",
                        paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                        plot_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5))
                    st.plotly_chart(fig, use_container_width=True)
                    last_irr = irr_index[-1]
                    last_usd = usd_index[-1]
                    if last_irr > 105 and last_usd < 95:
                        st.error(f"🔴 **تله دلار:** ریالی {last_irr-100:+.1f}% ولی دلاری {last_usd-100:+.1f}%. **فروش بدون خرید دلار = ضرر دلاری**")
                    elif last_usd > 105:
                        st.success(f"🟢 **سود دلاری واقعی:** {last_usd-100:+.1f}% رشد دلاری. فروش توجیه دارد.")

            # ============ تاریخچه با ۹ ستون ============
            if records and analytics:
                st.markdown("**📋 تاریخچه رکوردها**")

                hc = st.columns([2, 1.6, 1.6, 1.8, 1.8, 1.6, 1.6, 0.7, 0.7])
                hc[0].caption("**تاریخ**")
                hc[1].caption("**قیمت واحد**")
                hc[2].caption("**دلاری**")
                hc[3].caption("**انس**")
                hc[4].caption("**دلار**")
                hc[5].caption("**واحد/انس**")
                hc[6].caption("**بازده دلاری**")
                hc[7].caption("**✏️**")
                hc[8].caption("**🗑️**")
                st.divider()

                sorted_analytics = list(reversed(analytics))
                for a in sorted_analytics:
                    r = a["record"]
                    usd_eq = a["usd_equivalent"]
                    usd_ret = a["usd_return_pct"]
                    ounce_ch = a["ounce_change_pct"]
                    usd_ch = a["usd_change_pct"]

                    units_for_ounce = 0
                    if r.get("unit_price", 0) > 0 and r.get("usd_rate_used", 0) > 0:
                        units_for_ounce = (r["ounce_price_usd"] * r["usd_rate_used"]) / r["unit_price"]

                    rc = st.columns([2, 1.6, 1.6, 1.8, 1.8, 1.6, 1.6, 0.7, 0.7])
                    rc[0].markdown(f"📅 {r['date_jalali']}")
                    rc[1].markdown(f"{r['unit_price']:,.0f}")
                    rc[2].markdown(f"${usd_eq:,.4f}" if usd_eq else "—")

                    ounce_base = f"${r['ounce_price_usd']:,.0f}"
                    if ounce_ch is not None and abs(ounce_ch) >= 0.05:
                        color = "#10b981" if ounce_ch > 0 else "#ef4444"
                        arrow = "↑" if ounce_ch > 0 else "↓"
                        rc[3].markdown(
                            f'{ounce_base} <span style="color:{color};font-size:0.85em;">{arrow}{abs(ounce_ch):.1f}%</span>',
                            unsafe_allow_html=True)
                    else:
                        rc[3].markdown(ounce_base)

                    usd_base = f"{r.get('usd_rate_used', 0):,.0f}"
                    if usd_ch is not None and abs(usd_ch) >= 0.05:
                        color = "#10b981" if usd_ch > 0 else "#ef4444"
                        arrow = "↑" if usd_ch > 0 else "↓"
                        rc[4].markdown(
                            f'{usd_base} <span style="color:{color};font-size:0.85em;">{arrow}{abs(usd_ch):.1f}%</span>',
                            unsafe_allow_html=True)
                    else:
                        rc[4].markdown(usd_base)

                    rc[5].markdown(f"**{units_for_ounce:,.0f}**" if units_for_ounce else "—")

                    if usd_ret is not None and abs(usd_ret) >= 0.05:
                        color = "#10b981" if usd_ret > 0 else "#ef4444"
                        arrow = "↑" if usd_ret > 0 else "↓"
                        rc[6].markdown(
                            f'<span style="color:{color};font-weight:700;">{arrow}{abs(usd_ret):.1f}%</span>',
                            unsafe_allow_html=True)
                    else:
                        rc[6].markdown("—")

                    if rc[7].button("✏️", key=f"edit_btn_gold_{fund['id']}_{r['id']}"):
                        st.session_state[f"edit_open_gold_{r['id']}"] = not st.session_state.get(f"edit_open_gold_{r['id']}", False)
                    if rc[8].button("🗑️", key=f"del_gold_rec_{fund['id']}_{r['id']}"):
                        fund["records"] = [x for x in fund["records"] if x["id"] != r["id"]]
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()

                    if st.session_state.get(f"edit_open_gold_{r['id']}", False):
                        gvk = f"v_gold_rec_{r['id']}"
                        gfk = f"edit_gold_rec_{r['id']}_v{get_version(gvk)}"
                        with st.form(gfk):
                            ec1, ec2, ec3 = st.columns([2, 2, 2])
                            er_date = ec1.text_input("تاریخ", value=r["date_jalali"], key=f"g_ed_date_{r['id']}")
                            er_price = ec2.number_input("قیمت واحد", value=float(r["unit_price"]), min_value=0.0, format="%.0f", step=1000.0, key=f"g_ed_price_{r['id']}")
                            er_ounce = ec3.number_input("انس (دلار)", value=float(r["ounce_price_usd"]), min_value=0.0, format="%.2f", step=1.0, key=f"g_ed_ounce_{r['id']}")
                            ec4, ec5 = st.columns([2, 3])
                            er_rate = ec4.number_input("نرخ دلار", value=float(r.get("usd_rate_used", 0)), min_value=0.0, format="%.0f", step=1000.0, key=f"g_ed_rate_{r['id']}")
                            er_note = ec5.text_input("توضیح", value=r.get("note", ""), key=f"g_ed_note_{r['id']}")
                            if er_price > 0 and er_ounce > 0 and er_rate > 0:
                                new_u = (er_ounce * er_rate) / er_price
                                st.info(f"📊 واحد برای ۱ انس: **{new_u:,.0f}** واحد")
                            if st.form_submit_button("💾 ذخیره", use_container_width=True):
                                jd = parse_jalali(er_date)
                                if jd and er_price > 0 and er_ounce > 0 and er_rate > 0:
                                    tp = r["date_gregorian"][11:16] if len(r.get("date_gregorian", "")) >= 16 else "00:00"
                                    giso = jalali_to_gregorian_iso(jd, tp)
                                    for i, x in enumerate(fund["records"]):
                                        if x["id"] == r["id"]:
                                            fund["records"][i] = {"id": r["id"], "date_gregorian": giso,
                                                                  "date_jalali": jd.strftime("%Y/%m/%d"),
                                                                  "unit_price": er_price, "ounce_price_usd": er_ounce,
                                                                  "usd_rate_used": er_rate, "note": er_note.strip()}
                                            break
                                    st.session_state.data = data
                                    st.session_state[f"edit_open_gold_{r['id']}"] = False
                                    bump_version(gvk)
                                    save_all(data)
                                    st.rerun()
                                else:
                                    st.error("مقادیر معتبر وارد کنید.")
                    st.divider()

            with st.expander(f"⚠️ حذف صندوق {fund['name']}"):
                _fi = next((i for i, x in enumerate(data["gold_funds"]) if x["id"] == fund["id"]), 0)
                confirm = st.checkbox("مطمئنم", key=f"confirm_del_gold_{fund['id']}_{_fi}")
                if st.button("🗑️ حذف صندوق", disabled=not confirm, key=f"del_gold_fund_{fund['id']}_{_fi}", use_container_width=True):
                    data["gold_funds"] = [x for x in data["gold_funds"] if x["id"] != fund["id"]]
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()
            st.divider()

# ================== صفحه تنظیمات ==================
elif selected == "settings":
    render_settings_page(data)

# ================== صفحه دارایی اختصاصی ==================
elif selected.startswith("asset_"):
    aid = selected.replace("asset_", "")
    asset = next((a for a in assets if a["id"] == aid), None)
    if asset is None: st.error("یافت نشد.")
    else:
        rate, _ = get_current_usd_rate(data)
        value, usd_val, rec = compute_asset_value(asset, rate)
        st.markdown(f'<h1 style="text-align:right;"><i class="fa-solid {asset_icon(asset)}" style="color:{asset_color(asset)};"></i> {asset["name"]}</h1>', unsafe_allow_html=True)
        st.caption(f"ارز: **{currency_label(asset['currency'])}** | ایجاد: {asset.get('created_at_jalali', '—')}")
        avk = f"v_asset_{asset['id']}"
        afk = f"edit_asset_{asset['id']}_v{get_version(avk)}"
        with st.expander("⚙️ ویرایش نام و ارز"):
            with st.form(afk):
                ac1, ac2 = st.columns([3, 2])
                new_name = ac1.text_input("نام", value=asset["name"])
                new_cur = ac2.selectbox("ارز", ["IRR", "USD"], index=0 if asset["currency"] == "IRR" else 1,
                                       format_func=lambda x: "ریال" if x == "IRR" else "دلار")
                if st.form_submit_button("💾 ذخیره", use_container_width=True):
                    if new_name.strip():
                        for i, a in enumerate(data["assets"]):
                            if a["id"] == asset["id"]:
                                data["assets"][i]["name"] = new_name.strip()
                                data["assets"][i]["currency"] = new_cur; break
                        st.session_state.data = data; bump_version(avk); save_all(data); st.rerun()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 تعداد", fmt_num(rec["quantity"]) if rec else "—")
        c2.metric("💲 قیمت", f"{fmt_num(rec['unit_price'])} {currency_label(asset['currency'])}" if rec else "—")
        c3.metric("💰 ارزش", f"{fmt_num(value)} {currency_label(asset['currency'])}" if rec else "—")
        c4.metric("💵 دلاری", f"${usd_val:,.2f}" if usd_val is not None else "—")
        with st.container(border=True):
            st.subheader("➕ ثبت رکورد روزانه")
            with st.form(f"add_record_{asset['id']}", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
                dtext = c1.text_input("تاریخ", value=today_jalali_str())
                qty = c2.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
                price = c3.number_input(f"قیمت ({currency_label(asset['currency'])})", min_value=0.0, format="%.2f", step=1000.0)
                note = c4.text_input("توضیح")
                if st.form_submit_button("💾 ثبت", use_container_width=True):
                    jd = parse_jalali(dtext)
                    if jd and qty > 0 and price > 0:
                        giso = jalali_to_gregorian_iso(jd, datetime.now().strftime("%H:%M"))
                        asset.setdefault("records", []).append({
                            "id": _short_id(), "date_gregorian": giso,
                            "date_jalali": jd.strftime("%Y/%m/%d"),
                            "quantity": qty, "unit_price": price, "note": note.strip()})
                        st.session_state.data = data; save_all(data); st.rerun()
                    else: st.error("مقادیر معتبر وارد کنید.")
        records = sorted(asset.get("records", []), key=lambda r: r.get("date_gregorian", ""))
        if len(records) >= 2:
            st.subheader("📈 روند")
            chart_rows = [{"تاریخ": r["date_jalali"], "ارزش": r["quantity"] * r["unit_price"]} for r in records]
            cdf = pd.DataFrame(chart_rows)
            fig = px.line(cdf, x="تاریخ", y="ارزش", markers=True,
                         labels={"تاریخ": "تاریخ", "ارزش": currency_label(asset['currency'])})
            fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13, color="#e6edf3" if _dark else "#1f2937"),
                             margin=dict(t=20, b=20),
                             paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                             plot_bgcolor="rgba(0,0,0,0)" if _dark else "white")
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("📋 تاریخچه رکوردها")
        for r in reversed(records):
            with st.container(border=True):
                c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 2, 3, 3, 2, 1, 1])
                c1.markdown(f"**📅 {r['date_jalali']}**")
                c2.caption(f"تعداد: {fmt_num(r['quantity'])}")
                c3.caption(f"قیمت: {fmt_num(r['unit_price'])} {currency_label(asset['currency'])}")
                val = r['quantity'] * r['unit_price']
                c4.markdown(f"**{fmt_num(val)} {currency_label(asset['currency'])}**")
                c5.caption(r.get("note", "—") or "—")
                if c6.button("✏️", key=f"edit_btn_rec_{r['id']}", help="ویرایش"):
                    st.session_state[f"edit_open_rec_{r['id']}"] = not st.session_state.get(f"edit_open_rec_{r['id']}", False)
                if c7.button("🗑️", key=f"del_rec_{r['id']}", help="حذف"):
                    asset["records"] = [x for x in asset["records"] if x["id"] != r["id"]]
                    st.session_state.data = data; save_all(data); st.rerun()
                if st.session_state.get(f"edit_open_rec_{r['id']}", False):
                    rvk = f"v_rec_{r['id']}"
                    rfk = f"edit_rec_{r['id']}_v{get_version(rvk)}"
                    with st.form(rfk):
                        ec1, ec2, ec3 = st.columns([2, 2, 2])
                        ed_date = ec1.text_input("تاریخ", value=r["date_jalali"])
                        ed_qty = ec2.number_input("تعداد", value=float(r["quantity"]), min_value=0.0, format="%.4f", step=1.0)
                        ed_price = ec3.number_input("قیمت", value=float(r["unit_price"]), min_value=0.0, format="%.2f", step=1000.0)
                        ed_note = st.text_input("توضیح", value=r.get("note", ""))
                        if st.form_submit_button("💾 ذخیره", use_container_width=True):
                            jd = parse_jalali(ed_date)
                            if jd and ed_qty > 0 and ed_price > 0:
                                tp = r["date_gregorian"][11:16] if len(r.get("date_gregorian", "")) >= 16 else "00:00"
                                giso = jalali_to_gregorian_iso(jd, tp)
                                for i, x in enumerate(asset["records"]):
                                    if x["id"] == r["id"]:
                                        asset["records"][i] = {"id": r["id"], "date_gregorian": giso,
                                                              "date_jalali": jd.strftime("%Y/%m/%d"),
                                                              "quantity": ed_qty, "unit_price": ed_price, "note": ed_note.strip()}
                                        break
                                st.session_state.data = data
                                st.session_state[f"edit_open_rec_{r['id']}"] = False
                                bump_version(rvk); save_all(data); st.rerun()
        st.divider()
        with st.expander("⚠️ حذف کل دارایی"):
            _idx = next((i for i, x in enumerate(data["assets"]) if x["id"] == asset["id"]), 0)
            ok = st.checkbox("مطمئنم", key=f"confirm_del_{asset['id']}_{_idx}")
            if st.button("🗑️ حذف", disabled=not ok, key=f"del_btn_{asset['id']}_{_idx}"):
                data["assets"] = [x for x in data["assets"] if x["id"] != asset["id"]]
                st.session_state.data = data; save_all(data)
                st.session_state.pending_nav = "overview"; st.rerun()
