import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import re
import requests
import base64
import hashlib
from datetime import datetime
import jdatetime

from styles import FONTS, inject_login, inject_app

# ================== تنظیمات پایه ==================
st.set_page_config(page_title="داشبورد مالی", layout="wide", initial_sidebar_state="expanded")
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
APP_PASSWORD = st.secrets.get("APP_PASSWORD")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"

def get_auth_token():
    return hashlib.sha256((APP_PASSWORD + "_salt_v2_2024").encode()).hexdigest()

AUTH_TOKEN = get_auth_token()

# ================== آیکون‌های FA ==================
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
    {"class": "fa-sack-dollar", "label": "Sack"}, {"class": "fa-receipt", "label": "Receipt"},
    {"class": "fa-tag", "label": "Tag"}, {"class": "fa-fire", "label": "Fire"},
    {"class": "fa-bolt", "label": "Bolt"}, {"class": "fa-box", "label": "Box"},
    {"class": "fa-gear", "label": "Gear"}, {"class": "fa-circle-plus", "label": "Circle Plus"},
]

@st.cache_data(ttl=86400, show_spinner=False)
@st.cache_data(ttl=86400, show_spinner=False)
def load_fa_icons():
    try:
        r = requests.get("https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/metadata/icons.json", timeout=15)
        if r.status_code == 200:
            meta = r.json()
            icons = [{"class": f"fa-{name}", "label": info.get("label", name),
                      "categories": info.get("categories", [])}
                     for name, info in meta.items() if "solid" in info.get("free", [])]
            if icons:
                return sorted(icons, key=lambda x: x["label"].lower())
    except Exception:
        pass
    return [{"class": x["class"], "label": x["label"], "categories": []} for x in FALLBACK_ICONS]

EMOJI_FALLBACK = {
    "fa-folder": "📁", "fa-coins": "🪙", "fa-wallet": "👛", "fa-dollar-sign": "💲",
    "fa-building-columns": "🏦", "fa-gem": "💎", "fa-crown": "👑", "fa-house": "🏠",
    "fa-car": "🚗", "fa-chart-line": "📈", "fa-chart-pie": "📊", "fa-bitcoin-sign": "₿",
    "fa-briefcase": "💼", "fa-store": "🏪", "fa-sack-dollar": "💰", "fa-fire": "🔥",
    "fa-bolt": "⚡", "fa-box": "📦", "fa-gear": "⚙️", "fa-circle-plus": "➕",
}

def icon_emoji(fa_class):
    return EMOJI_FALLBACK.get(fa_class, "📁")

DEFAULT_NAV_ICONS = {
    "overview": {"icon": "fa-chart-pie", "color": "#3b82f6"},
    "journal": {"icon": "fa-circle-plus", "color": "#10b981"},
    "usd": {"icon": "fa-dollar-sign", "color": "#f59e0b"},
    "settings": {"icon": "fa-gear", "color": "#6b7280"},
}
NAV_LABELS = {"overview": "نمای کلی", "journal": "افزودن دارایی", "usd": "دلار", "settings": "تنظیمات"}
NAV_EMOJI = {"overview": "📊", "journal": "➕", "usd": "💵", "settings": "⚙️"}

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

# ================== 🔐 احراز هویت ==================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    qp_auth = st.query_params.get("auth")
    if qp_auth and qp_auth == AUTH_TOKEN:
        st.session_state.authenticated = True

if not st.session_state.authenticated:
    inject_login()
    st.markdown("<div style='height: 6vh;'></div>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("""
        <div style="text-align:center; padding: 24px 0 16px 0; direction: rtl;">
            <div style="font-size: 3.2rem; line-height: 1; margin-bottom: 8px;">🔐</div>
            <h1 style="margin: 0; color: #1e40af;">داشبورد مالی</h1>
            <p style="color: #6b7280; margin-top: 8px; font-size: 0.95rem;">لطفاً برای مشاهده، رمز عبور را وارد کنید</p>
        </div>
        """, unsafe_allow_html=True)
        with st.container(border=True):
            with st.form("login_form", clear_on_submit=False):
                password = st.text_input("رمز عبور", type="password", placeholder="••••••••", label_visibility="collapsed")
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
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None

def save_local_file(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def load_github_file():
    if not GITHUB_TOKEN or not GITHUB_REPO: return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(url, headers=github_headers(), timeout=20)
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
    except Exception:
        pass
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
    payload = {
        "message": f"update {today_jalali_str()} {datetime.now().strftime('%H:%M')}",
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha: payload["sha"] = sha
    try:
        r = requests.put(url, headers=github_headers(), json=payload, timeout=30)
        if r.status_code in (200, 201): return True, ""
        if r.status_code == 401: return False, "توکن نامعتبر (401)"
        if r.status_code == 403: return False, "دسترسی write ندارد (403)"
        if r.status_code == 404: return False, "مخزن یا branch یافت نشد (404)"
        if r.status_code == 409: return False, "تضاد SHA (409)"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"خطای شبکه: {str(e)[:50]}"

def verify_github_save(expected_data):
    if not GITHUB_TOKEN or not GITHUB_REPO: return False, "GitHub تنظیم نشده", None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(url, headers=github_headers(), timeout=20)
        if r.status_code != 200: return False, f"HTTP {r.status_code}", None
        info = r.json()
        gh_data = json.loads(base64.b64decode(info["content"]).decode("utf-8"))
        sha = info.get("sha", "")[:8]
        size = info.get("size", 0)
        if gh_data.get("last_saved") != expected_data.get("last_saved"):
            return False, "timestamp متفاوت", sha
        return True, f"تأیید شد — {size:,} بایت", sha
    except Exception as e:
        return False, str(e)[:50], None

# ================== مهاجرت ==================
def migrate_data(data):
    if not isinstance(data, dict) or not data:
        return {"assets": [], "usd_rates": [], "settings": {"font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy(), "custom_fonts": {}, "dark_mode": False}}
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list):
        old = data.get("usd_rate")
        data["usd_rates"] = []
        if old:
            data["usd_rates"].append({"id": datetime.now().isoformat(), "rate": old, "note": "منتقل‌شده",
                                     "created_at": datetime.now().isoformat(), "created_at_jalali": today_jalali_str()})
        data.pop("usd_rate", None)
    if "journals" in data and isinstance(data.get("journals"), list):
        if "assets" not in data or not isinstance(data.get("assets"), list): data["assets"] = []
        for j in data.get("journals", []):
            aid = j.get("id") or datetime.now().isoformat()
            ciso = j.get("created_at_gregorian") or j.get("created_at") or datetime.now().isoformat()
            cjal = j.get("created_at_jalali") or iso_to_jalali(ciso, with_time=False)
            data["assets"].append({"id": aid, "name": j.get("asset_name", "بدون نام"),
                                  "icon": "fa-folder", "color": "#3b82f6", "overview_emoji": "",
                                  "currency": j.get("currency", "IRR"),
                                  "created_at_gregorian": ciso, "created_at_jalali": cjal,
                                  "records": [{"id": aid + "_r", "date_gregorian": ciso, "date_jalali": cjal,
                                              "quantity": j.get("amount", 0), "unit_price": 1, "note": "منتقل‌شده"}]})
        data.pop("journals", None)
    if "assets" not in data or not isinstance(data.get("assets"), list): data["assets"] = []
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list): data["usd_rates"] = []
    if "settings" not in data or not isinstance(data.get("settings"), dict):
        data["settings"] = {"font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy(), "custom_fonts": {}, "dark_mode": False}
    data["settings"].setdefault("font", "vazirmatn")
    data["settings"].setdefault("dark_mode", False)
    if "nav_icons" not in data["settings"] or not isinstance(data["settings"].get("nav_icons"), dict):
        data["settings"]["nav_icons"] = DEFAULT_NAV_ICONS.copy()
    for k, v in DEFAULT_NAV_ICONS.items():
        data["settings"]["nav_icons"].setdefault(k, v.copy())
    if "custom_fonts" not in data["settings"] or not isinstance(data["settings"].get("custom_fonts"), dict):
        data["settings"]["custom_fonts"] = {}
    for a in data["assets"]:
        if not isinstance(a.get("icon"), str) or not a["icon"].startswith("fa-"):
            a["icon"] = "fa-folder"
        a.setdefault("color", "#3b82f6")
        a.setdefault("overview_emoji", "")
    return data

def load_all():
    local = load_local_file()
    gh = load_github_file()
    l_has = local and (local.get("assets") or local.get("usd_rates"))
    g_has = gh and (gh.get("assets") or gh.get("usd_rates"))
    if l_has and g_has:
        l_saved = local.get("last_saved", "")
        g_saved = gh.get("last_saved", "")
        chosen = (local if l_saved > g_saved else gh) if (l_saved and g_saved) else gh
        save_local_file(chosen)
        return migrate_data(chosen)
    if g_has:
        save_local_file(gh)
        return migrate_data(gh)
    if l_has:
        return migrate_data(local)
    return {"assets": [], "usd_rates": [], "settings": {"font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy(), "custom_fonts": {}, "dark_mode": False}}

def save_all(data, verify=True):
    data["last_saved"] = datetime.now().isoformat()
    data["last_saved_jalali"] = jdatetime.datetime.fromgregorian(datetime=datetime.now()).strftime("%Y/%m/%d - %H:%M")
    local_ok = save_local_file(data)
    gh_ok, gh_err = save_github_file(data)
    if gh_ok:
        if verify:
            v_ok, v_msg, _ = verify_github_save(data)
            if v_ok:
                st.toast("✅ ذخیره و تأیید شد", icon="✅")
                return True
            st.warning(f"⚠️ ذخیره شد ولی تأیید ناقص: {v_msg}")
            return False
        st.toast("✅ ذخیره شد")
        return True
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
    for k, (name, url) in FONTS.items():
        fonts[k] = {"name": name, "family": name, "builtin": True, "url": url}
    custom = (data.get("settings") or {}).get("custom_fonts", {}) or {}
    for k, info in custom.items():
        fonts[k] = {"name": info.get("display_name", k), "family": k, "builtin": False, "url": None}
    return fonts

def asset_icon(asset):
    ic = asset.get("icon", "fa-folder")
    return ic if isinstance(ic, str) and ic.startswith("fa-") else "fa-folder"

def asset_color(asset):
    return asset.get("color", "#3b82f6")

def asset_icon_emoji(asset):
    return icon_emoji(asset_icon(asset))

def asset_overview_emoji(asset):
    custom = (asset.get("overview_emoji") or "").strip()
    if custom:
        return custom
    return icon_emoji(asset_icon(asset))

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

def currency_label(cur):
    return "ریال" if cur == "IRR" else "دلار"

def get_version(key):
    if key not in st.session_state: st.session_state[key] = 0
    return st.session_state[key]

def bump_version(key):
    st.session_state[key] = st.session_state.get(key, 0) + 1

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
        except Exception:
            jd = d
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

# ================== گرید آیکون و ایموجی ==================
CATEGORY_LABELS_FA = {
    "money": "💰 پول و مالی", "business": "💼 کسب و کار",
    "charts-diagrams": "📊 نمودار", "buildings": "🏢 ساختمان",
    "shopping": "🛒 خرید", "security": "🔒 امنیت",
    "transportation": "🚗 حمل و نقل", "nature": "🌿 طبیعت",
    "food-beverage": "🍔 غذا و نوشیدنی", "education": "🎓 آموزش",
    "users-people": "👥 افراد", "time": "⏰ زمان",
    "weather": "☁️ آب و هوا", "medical-health": "🏥 پزشکی",
    "science": "🔬 علم", "computers": "💻 کامپیوتر",
    "animals": "🐾 حیوانات", "arrows": "➡️ فلش‌ها",
    "communication": "💬 ارتباطات", "design": "🎨 طراحی",
    "files": "📁 فایل‌ها", "interfaces": "🖱️ رابط کاربری",
    "maps": "🗺️ نقشه", "mathematics": "🔢 ریاضیات",
    "media-playback": "▶️ رسانه", "music-audio": "🎵 موسیقی",
    "photography": "📷 عکاسی", "sports-fitness": "⚽ ورزش",
    "travel-hotel": "✈️ سفر", "energy": "⚡ انرژی",
    "household": "🏠 خانه", "logistics": "📦 لجستیک",
    "marketing": "📢 بازاریابی", "shapes": "🔷 اشکال",
    "text-formatting": "📝 متن", "games": "🎮 بازی",
    "holiday": "🎉 تعطیلات", "religion": "🕌 مذهب",
    "political": "🏛️ سیاسی", "charity": "❤️ خیریه",
    "accessibility": "♿ دسترسی‌پذیری", "construction": "🏗️ ساخت",
    "fruits-vegetables": "🍎 میوه", "hands": "👋 دست‌ها",
}
def _icon_grid_picker(prefix, current, on_save):
    icons = load_fa_icons()

    # استخراج دسته‌های موجود
    all_cats = set()
    for ic in icons:
        for c in ic.get("categories", []):
            all_cats.add(c)
    cat_options = ["__all__"] + sorted(all_cats)

    c1, c2 = st.columns([2, 3])
    cat = c1.selectbox(
        "📂 دسته",
        cat_options,
        format_func=lambda x: "🌐 همه" if x == "__all__" else CATEGORY_LABELS_FA.get(x, x),
        key=f"{prefix}_cat",
    )
    s = c2.text_input("🔍", key=f"{prefix}_search",
                     placeholder="جستجو در آیکون‌ها...", label_visibility="collapsed")

    filtered = icons if cat == "__all__" else [i for i in icons if cat in i.get("categories", [])]
    if s:
        q = s.lower()
        filtered = [i for i in filtered if q in i["label"].lower() or q in i["class"].lower()]

    per_page = 48
    total = len(filtered)
    pages = max(1, (total + per_page - 1) // per_page)
    pk = f"{prefix}_page"
    catk = f"{prefix}_cat_prev"

    # با تغییر دسته، به صفحه ۱ برگرد
    if catk not in st.session_state or st.session_state[catk] != cat:
        st.session_state[pk] = 0
        st.session_state[catk] = cat
    if st.session_state.get(pk, 0) >= pages:
        st.session_state[pk] = 0

    page = st.session_state.get(pk, 0)
    display = filtered[page * per_page:(page + 1) * per_page]

    st.caption(f"**{total}** آیکون — صفحه **{page + 1}** از **{pages}**")

    if total == 0:
        st.info("آیکونی یافت نشد.")
        return

    for row in range(0, len(display), 8):
        cols = st.columns(8)
        for j, ic in enumerate(display[row:row + 8]):
            with cols[j]:
                is_cur = (ic["class"] == current)
                border = "3px solid #22c55e" if is_cur else "1px solid #e5e7eb"
                st.markdown(
                    f'<div style="text-align:center; padding:10px 4px; border:{border}; '
                    f'border-radius:8px; margin-bottom:4px; background:#f9fafb;">'
                    f'<i class="fa-solid {ic["class"]}" style="font-size:1.6rem; color:#3b82f6;"></i>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                lbl = "✅" if is_cur else "انتخاب"
                if st.button(lbl, key=f"{prefix}_btn_{ic['class']}",
                            use_container_width=True, disabled=is_cur):
                    on_save(ic["class"])
                    st.rerun()

    if pages > 1:
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc1:
            if st.button("◀ قبلی", key=f"{prefix}_prev",
                        use_container_width=True, disabled=(page == 0)):
                st.session_state[pk] = page - 1
                st.rerun()
        with pc2:
            st.markdown(
                f'<div style="text-align:center; padding-top:8px; font-weight:600;">'
                f'صفحه {page + 1} / {pages}</div>',
                unsafe_allow_html=True,
            )
        with pc3:
            if st.button("بعدی ▶", key=f"{prefix}_next",
                        use_container_width=True, disabled=(page >= pages - 1)):
                st.session_state[pk] = page + 1
                st.rerun()
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
                is_current = (em == current)
                btn_label = f"{'✅' if is_current else ''}{em}"
                if st.button(btn_label, key=f"{prefix}_em_{row + j}", use_container_width=True):
                    on_save(em)
                    st.rerun()
    st.divider()
    c1, c2 = st.columns([3, 1])
    custom = c1.text_input("یا ایموجی دلخواه", value=current or "", max_chars=8, key=f"{prefix}_custom", placeholder="مثلاً: 🥇")
    if c2.button("💾 ذخیره", key=f"{prefix}_save_custom", use_container_width=True):
        on_save(custom.strip()[:8])
        st.rerun()
    if st.button("🔄 خودکار (خالی کردن)", key=f"{prefix}_clear", use_container_width=True):
        on_save("")
        st.rerun()

# ================== مقداردهی + اعمال استایل ==================
if "data" not in st.session_state:
    st.session_state.data = load_all()
st.session_state.data = migrate_data(st.session_state.data)
data = st.session_state.data
data.setdefault("assets", [])
data.setdefault("usd_rates", [])

# حذف دارایی‌های با id تکراری (در صورت خرابی داده)
_seen_ids = set()
_unique = []
for _a in data.get("assets", []):
    if _a.get("id") and _a["id"] not in _seen_ids:
        _seen_ids.add(_a["id"])
        _unique.append(_a)
if len(_unique) != len(data.get("assets", [])):
    st.warning(f"⚠️ {len(data['assets']) - len(_unique)} دارایی تکراری حذف شد.")
    data["assets"] = _unique
    save_local_file(data)
    
inject_app(data)
_dark = get_settings(data)["dark_mode"]
assets = data.get("assets", [])

# ================== سایدبار ==================
with st.sidebar:
    c_date, c_mode = st.columns([3, 1])
    with c_date:
        st.markdown(f"### 🗓️ {today_jalali_str()}")
    with c_mode:
        _mode_icon = "☀️" if _dark else "🌙"
        if st.button(_mode_icon, key="dark_toggle_btn", help="حالت روز / شب", use_container_width=True):
            data["settings"]["dark_mode"] = not _dark
            st.session_state.data = data
            save_all(data)
            st.rerun()
    if st.button("🚪 خروج", use_container_width=True, key="logout_btn"):
        st.session_state.authenticated = False
        st.session_state.pop("data", None)
        st.query_params.clear()
        st.rerun()
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
            <div style="font-size: 1.5rem; font-weight: 700; color: {value_col}; line-height: 1.2;">{rate:,.0f}<span style="font-size: 0.95rem; color: {title_col};"> ریال</span></div>
            <div style="font-size: 0.72rem; color: {title_col}; margin-top: 6px;">آخرین: {rate_date}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("💡 هنوز نرخی ثبت نشده.")

    st.divider()
    st.markdown("**💾 وضعیت ذخیره‌سازی**")
    if data.get("last_saved"):
        st.caption(f"✅ آخرین ذخیره: {data.get('last_saved_jalali', '—')}")
    else:
        st.caption("⚠️ هنوز ذخیره نشده")
    local_ok = os.path.exists(DATA_FILE)
    gh_status, gh_message = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
    c1, c2 = st.columns(2)
    c1.caption(f"{'✅' if local_ok else '❌'} محلی")
    c2.caption(f"{'✅' if gh_status == 'ok' else '❌'} GitHub")
    if gh_status != "ok":
        st.error(f"⚠️ {gh_message}")
    if st.button("💾 ذخیره فوری + تأیید", use_container_width=True, key="force_save"):
        if save_all(data):
            st.rerun()

    st.divider()
    with st.expander("📥 پشتیبان / 📤 بازیابی", expanded=False):
        st.download_button("📥 دانلود JSON", data=json.dumps(data, ensure_ascii=False, indent=2),
                          file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                          mime="application/json", use_container_width=True)
        uploaded = st.file_uploader("📤 آپلود JSON", type=["json"], key="uploader")
        if uploaded is not None:
            try:
                imported = json.loads(uploaded.read().decode("utf-8"))
                imported = migrate_data(imported)
                if st.button("✅ اعمال", use_container_width=True):
                    st.session_state.data = imported
                    save_all(imported)
                    st.rerun()
            except Exception as e:
                st.error(f"فایل معتبر نیست: {e}")

# ================== ناوبری با نسخه‌بندی ==================
nav_options = ["overview", "journal", "usd"] + [f"asset_{a['id']}" for a in assets] + ["settings"]

nav_labels = {
    "overview": f"{NAV_EMOJI['overview']} {NAV_LABELS['overview']}",
    "journal": f"{NAV_EMOJI['journal']} {NAV_LABELS['journal']}",
    "usd": f"{NAV_EMOJI['usd']} {NAV_LABELS['usd']}",
    "settings": f"{NAV_EMOJI['settings']} {NAV_LABELS['settings']}",
}
for a in assets:
    nav_labels[f"asset_{a['id']}"] = f"{asset_overview_emoji(a)} {a['name']}"

if "nav_version" not in st.session_state:
    st.session_state.nav_version = 0

if "pending_nav" in st.session_state:
    pending = st.session_state.pending_nav
    del st.session_state.pending_nav
    if pending in nav_options:
        st.session_state.nav_version += 1
        st.session_state[f"nav_pills_v{st.session_state.nav_version}"] = pending

_widget_key = f"nav_pills_v{st.session_state.nav_version}"
if _widget_key not in st.session_state:
    st.session_state[_widget_key] = "overview"
if st.session_state[_widget_key] not in nav_options:
    st.session_state[_widget_key] = "overview"

if hasattr(st, "pills"):
    selected = st.pills(
        "ناوبری",
        options=nav_options,
        format_func=lambda x: nav_labels.get(x, x),
        selection_mode="single",
        label_visibility="collapsed",
        key=_widget_key,
    )
    if selected is None:
        selected = st.session_state[_widget_key]
else:
    selected = st.radio(
        "ناوبری",
        options=nav_options,
        format_func=lambda x: nav_labels.get(x, x),
        horizontal=True,
        label_visibility="collapsed",
        key=_widget_key + "_radio",
    )
    if selected is None:
        selected = "overview"

# ================== صفحه تنظیمات ==================
def render_settings_page(data):
    st.header("⚙️ تنظیمات")
    settings = get_settings(data)
    all_fonts = get_all_fonts(data)
    dark = settings["dark_mode"]

    t_font, t_nav, t_assets, t_emoji, t_lib, t_verify, t_storage = st.tabs([
        "🔤 فونت", "🎨 آیکون منو", "📦 آیکون دارایی", "😀 ایموجی نمای کلی", "📚 کتابخانه", "🔍 تأیید ذخیره", "💾 وضعیت"
    ])

    with t_font:
        st.subheader("🔤 فونت برنامه")
        font_keys = list(all_fonts.keys())
        cur_font = settings["font"] if settings["font"] in font_keys else "vazirmatn"
        c1, c2 = st.columns([3, 1])
        new_font = c1.selectbox("انتخاب فونت", font_keys, index=font_keys.index(cur_font),
                               format_func=lambda k: all_fonts[k]["name"] + (" (سفارشی)" if not all_fonts[k]["builtin"] else ""),
                               key="font_select_v2")
        if c2.button("💾 ذخیره فونت", use_container_width=True, key="apply_font_btn"):
            data["settings"]["font"] = new_font
            st.session_state.data = data
            save_all(data)
            st.rerun()
        preview_family = all_fonts[new_font]["family"]
        bg_prev = "#161b22" if dark else "#f9fafb"
        border_prev = "#30363d" if dark else "#3b82f6"
        st.markdown(
            f'<div style="padding:20px; border:2px solid {border_prev}; border-radius:10px; margin:16px 0; background:{bg_prev}; direction:rtl;">'
            f'<div style="font-size:0.85rem; color:#6b7280; margin-bottom:10px;">پیش‌نمایش: <b>{all_fonts[new_font]["name"]}</b></div>'
            f'<div style="font-family:\'{preview_family}\', Tahoma; font-size:1.8rem; margin-bottom:12px;">داشبورد مالی — ۱۲۳۴۵</div>'
            f'<div style="font-family:\'{preview_family}\', Tahoma; font-size:1.05rem;">این یک متن نمونه است. اعداد: ۱۲۳۴۵۶۷۸۹۰ | 1234567890</div>'
            f'</div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("📤 بارگذاری فونت سفارشی")
        st.caption("فرمت‌ها: **TTF, OTF, WOFF, WOFF2** — حداکثر **۱۰ مگابایت**")
        with st.form("upload_font_form", clear_on_submit=True):
            uploaded_file = st.file_uploader("فایل فونت", type=["ttf", "otf", "woff", "woff2"], key="custom_font_uploader")
            display_name = st.text_input("نام نمایشی", placeholder="مثلاً: فونت شخصی من")
            if st.form_submit_button("📤 بارگذاری", use_container_width=True):
                if uploaded_file is None:
                    st.error("فایل انتخاب کنید.")
                elif uploaded_file.size > 10 * 1024 * 1024:
                    st.error(f"حجم ({uploaded_file.size // 1024:,} KB) بیش از ۱۰MB است.")
                else:
                    try:
                        fb = uploaded_file.read()
                        b64 = base64.b64encode(fb).decode()
                        ext = uploaded_file.name.lower().rsplit(".", 1)[-1]
                        fmap = {"ttf": "truetype", "otf": "opentype", "woff": "woff", "woff2": "woff2"}
                        mmap = {"ttf": "font/ttf", "otf": "font/otf", "woff": "font/woff", "woff2": "font/woff2"}
                        base_name = uploaded_file.name.rsplit(".", 1)[0]
                        safe = re.sub(r"[^a-z0-9_]", "_", base_name.lower())[:40]
                        fkey = f"custom_{safe}"
                        c = 1
                        orig = fkey
                        existing = data["settings"].get("custom_fonts", {})
                        while fkey in existing:
                            c += 1
                            fkey = f"{orig}_{c}"
                        data["settings"].setdefault("custom_fonts", {})[fkey] = {
                            "display_name": (display_name.strip() or base_name)[:60],
                            "data": b64, "format": fmap.get(ext, "truetype"), "mime": mmap.get(ext, "font/ttf"),
                            "filename": uploaded_file.name, "size_bytes": len(fb),
                            "uploaded_at": datetime.now().isoformat(),
                        }
                        st.session_state.data = data
                        save_all(data)
                        st.success(f"✅ فونت «{display_name or base_name}» بارگذاری شد.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطا: {e}")

        st.divider()
        st.subheader("📚 فونت‌های سفارشی من")
        custom_fonts = data["settings"].get("custom_fonts", {})
        if not custom_fonts:
            st.info("هنوز فونت سفارشی بارگذاری نشده.")
        else:
            for key, info in list(custom_fonts.items()):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
                    c1.markdown(f'<div style="text-align:center; font-family:\'{key}\', Tahoma; font-size:2.2rem; color:#3b82f6; padding:6px;">آ</div>', unsafe_allow_html=True)
                    c2.markdown(f"**{info.get('display_name', key)}**")
                    c2.caption(f"`{info.get('filename', '—')}` — {info.get('size_bytes', 0) // 1024:,} KB")
                    if settings["font"] == key:
                        c3.success("✅ فعال")
                    else:
                        c3.caption(f"`{key[:30]}`")
                    if c4.button("🗑️", key=f"del_font_{key}"):
                        del data["settings"]["custom_fonts"][key]
                        if data["settings"]["font"] == key:
                            data["settings"]["font"] = "vazirmatn"
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()

    with t_nav:
        st.subheader("🎨 آیکون و رنگ منو")
        st.caption("روی هر آیکون کلیک کنید تا انتخاب شود. ✅ = آیکون فعلی")
        for nav_key in ["overview", "journal", "usd", "settings"]:
            cfg = settings["nav_icons"].get(nav_key, DEFAULT_NAV_ICONS[nav_key])
            with st.container(border=True):
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.markdown(f'<div style="text-align:center; padding:10px;"><i class="fa-solid {cfg["icon"]}" style="color:{cfg["color"]}; font-size:2.5rem;"></i></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{NAV_LABELS[nav_key]}** — `{cfg['icon']}`")
                    new_color = st.color_picker("رنگ", value=cfg["color"], key=f"color_nav_{nav_key}")

                with st.expander("🖼️ انتخاب آیکون از گرید", expanded=False):
                    def _save_nav(icon_class, _k=nav_key):
                        current_color = data["settings"]["nav_icons"].get(_k, DEFAULT_NAV_ICONS[_k])["color"]
                        data["settings"]["nav_icons"][_k] = {"icon": icon_class, "color": current_color}
                        st.session_state.data = data
                        save_all(data)
                    _icon_grid_picker(f"nav_{nav_key}", cfg["icon"], _save_nav)

                if st.button("💾 ذخیره رنگ", key=f"save_nav_{nav_key}", use_container_width=True):
                    data["settings"]["nav_icons"][nav_key] = {"icon": cfg["icon"], "color": new_color}
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()

    with t_assets:
        st.subheader("📦 آیکون و رنگ دارایی‌ها")
        st.caption("روی هر آیکون کلیک کنید تا انتخاب شود. ✅ = آیکون فعلی")
        if not assets:
            st.info("هنوز دارایی‌ای ثبت نشده.")
        else:
            for a in assets:
                cur_ic, cur_col = asset_icon(a), asset_color(a)
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        st.markdown(f'<div style="text-align:center; padding:10px;"><i class="fa-solid {cur_ic}" style="color:{cur_col}; font-size:2.5rem;"></i></div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**{a['name']}** — `{cur_ic}`")
                        new_color = st.color_picker("رنگ", value=cur_col, key=f"color_asset_{a['id']}")

                    with st.expander("🖼️ انتخاب آیکون از گرید", expanded=False):
                        def _save_asset(icon_class, _id=a["id"]):
                            for i, x in enumerate(data["assets"]):
                                if x["id"] == _id:
                                    data["assets"][i]["icon"] = icon_class
                                    break
                            st.session_state.data = data
                            save_all(data)
                        _icon_grid_picker(f"asset_{a['id']}", cur_ic, _save_asset)

                    if st.button("💾 ذخیره رنگ", key=f"save_asset_{a['id']}", use_container_width=True):
                        for i, x in enumerate(data["assets"]):
                            if x["id"] == a["id"]:
                                data["assets"][i]["color"] = new_color
                                break
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()

    with t_emoji:
        st.subheader("😀 ایموجی نمایش در نمای کلی")
        st.caption("روی ایموجی کلیک کنید تا انتخاب شود. ✅ = انتخاب فعلی")
        st.caption("اگر خالی بگذارید، از ایموجی خودکار (بر اساس آیکون FA) استفاده می‌شود.")
        st.divider()
        if not assets:
            st.info("هنوز دارایی‌ای ثبت نشده.")
        else:
            for a in assets:
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    cur_emoji = asset_overview_emoji(a)
                    with c1:
                        st.markdown(f'<div style="text-align:center; font-size:2.8rem; padding:8px;">{cur_emoji}</div>', unsafe_allow_html=True)
                    with c2:
                        status = f"`{a['overview_emoji']}`" if a.get("overview_emoji") else "خودکار"
                        st.markdown(f"**{a['name']}** — {status}")

                    with st.expander("🖼️ انتخاب ایموجی از گرید", expanded=False):
                        def _save_em(v, _id=a["id"]):
                            for i, x in enumerate(data["assets"]):
                                if x["id"] == _id:
                                    data["assets"][i]["overview_emoji"] = v
                                    break
                            st.session_state.data = data
                            save_all(data)
                        _emoji_grid_picker(f"emoji_{a['id']}",
                                          a.get("overview_emoji", "") if a.get("overview_emoji") else "",
                                          _save_em)

    with t_lib:
        all_icons = load_fa_icons()
        st.caption(f"مجموعاً **{len(all_icons)}** آیکون FA رایگان")
        search_lib = st.text_input("🔍 جستجو", key="fa_lib_search", placeholder="مثلاً: money, chart...")
        filtered = [ic for ic in all_icons if search_lib.lower() in ic["label"].lower() or search_lib.lower() in ic["class"].lower()] if search_lib else all_icons
        display = filtered[:120]
        st.caption(f"**{len(filtered)}** یافت شد — نمایش {len(display)}")
        for i in range(0, len(display), 8):
            cols = st.columns(8)
            for j, ic in enumerate(display[i:i+8]):
                with cols[j]:
                    st.markdown(
                        f'<div style="text-align:center; padding:8px; border:1px solid #e5e7eb; border-radius:6px; margin:2px;" title="{ic["class"]}">'
                        f'<i class="fa-solid {ic["class"]}" style="font-size:1.4rem; color:#3b82f6;"></i>'
                        f'<div style="font-size:0.6rem; margin-top:4px; color:#6b7280; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{ic["label"]}</div></div>',
                        unsafe_allow_html=True)

    with t_verify:
        st.subheader("🔍 تأیید ذخیره‌سازی")
        if data.get("last_saved"):
            st.info(f"📅 **آخرین ذخیره:** {data.get('last_saved_jalali', '—')}")
        else:
            st.warning("⚠️ هنوز ذخیره‌ای انجام نشده!")
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔍 تأیید ذخیره", use_container_width=True, key="verify_gh_btn"):
                v_ok, v_msg, sha = verify_github_save(data)
                (st.success if v_ok else st.error)(f"{'✅' if v_ok else '❌'} {v_msg}")
                if sha: st.caption(f"SHA: `{sha}`")
        with col2:
            if st.button("🔄 بارگذاری از GitHub", use_container_width=True, key="force_load_btn"):
                gh = load_github_file()
                if gh:
                    st.session_state.data = migrate_data(gh)
                    save_local_file(st.session_state.data)
                    st.success(f"✅ بارگذاری شد — {len(gh.get('assets', []))} دارایی")
                    st.rerun()
                else:
                    st.error("❌ خواندن ناموفق")
        with col3:
            if st.button("💾 ذخیره فوری", use_container_width=True, key="force_save_btn"):
                if save_all(data):
                    st.success("✅ ذخیره شد")
                    st.rerun()
        st.divider()
        st.markdown("**📊 مقایسه داده حافظه با GitHub**")
        gh = load_github_file()
        if gh:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**در حافظه:**")
                st.caption(f"دارایی‌ها: {len(data.get('assets', []))}")
                st.caption(f"رکوردها: {sum(len(a.get('records', [])) for a in data.get('assets', []))}")
                st.caption(f"last_saved: {data.get('last_saved', '—')[:19]}")
            with c2:
                st.markdown("**در GitHub:**")
                st.caption(f"دارایی‌ها: {len(gh.get('assets', []))}")
                st.caption(f"رکوردها: {sum(len(a.get('records', [])) for a in gh.get('assets', []))}")
                st.caption(f"last_saved: {gh.get('last_saved', '—')[:19]}")
            if data.get("last_saved") == gh.get("last_saved"):
                st.success("✅ یکسان هستند")
            else:
                st.warning("⚠️ متفاوت هستند — روی «ذخیره فوری» بزنید")
        else:
            st.error("❌ خواندن از GitHub ناموفق!")

    with t_storage:
        st.subheader("💾 وضعیت اتصال")
        local_ok = os.path.exists(DATA_FILE)
        gh_status, gh_msg = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📁 فایل محلی**")
            if local_ok:
                st.success(f"✅ ({os.path.getsize(DATA_FILE):,} بایت)")
            else:
                st.error("❌ یافت نشد")
        with c2:
            st.markdown("**☁️ GitHub**")
            if gh_status == "ok":
                st.success(f"✅ {gh_msg}")
            else:
                st.error(f"❌ {gh_msg}")
                with st.expander("🔧 راهنما"):
                    st.code('GITHUB_TOKEN = "ghp_..."\nGITHUB_REPO = "user/repo"\nAPP_PASSWORD = "..."', language="toml")
        st.divider()
        st.subheader("📊 آمار")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("دارایی‌ها", len(data.get("assets", [])))
        c2.metric("رکوردها", sum(len(a.get("records", [])) for a in data.get("assets", [])))
        c3.metric("نرخ دلار", len(data.get("usd_rates", [])))
        c4.metric("فونت سفارشی", len(data.get("settings", {}).get("custom_fonts", {})))

# ================== صفحه نمای کلی ==================
if selected == "overview":
    st.header("📊 نمای کلی دارایی‌ها")
    rate, _ = get_current_usd_rate(data)
    if not assets:
        st.info("هنوز دارایی‌ای ثبت نشده. از تب «افزودن دارایی» اضافه کنید.")
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
        st.subheader("🥧 ترکیب دارایی‌ها")
        pie_df = df.dropna(subset=["معادل_دلاری"])
        pie_df = pie_df[pie_df["معادل_دلاری"] > 0]
        if not pie_df.empty:
            fig = px.pie(pie_df, values="معادل_دلاری", names="دارایی", hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=14),
                             legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                             margin=dict(t=20, b=20, l=10, r=10),
                             paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                             plot_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                             font_color="#e6edf3" if _dark else "#1f2937")
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("📈 روند رشد ارزش کل")
        timeline = build_portfolio_timeline(data)
        if len(timeline) >= 2:
            fig_usd = px.line(timeline, x="date_jalali", y="total_usd", markers=True,
                             labels={"date_jalali": "تاریخ", "total_usd": "دلار"},
                             color_discrete_sequence=["#3b82f6"])
            fig_usd.update_traces(hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
                                 line=dict(width=3), marker=dict(size=7))
            fig_usd.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13, color="#e6edf3" if _dark else "#1f2937"),
                                 yaxis=dict(tickformat=",.0f"), xaxis=dict(title="تاریخ"),
                                 margin=dict(t=30, b=20, l=10, r=10), hovermode="x unified",
                                 paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                                 plot_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                                 title=dict(text="💵 ارزش کل به دلار", font=dict(size=14)))
            st.plotly_chart(fig_usd, use_container_width=True)
            fig_irr = px.line(timeline, x="date_jalali", y="total_irr", markers=True,
                             labels={"date_jalali": "تاریخ", "total_irr": "ریال"},
                             color_discrete_sequence=["#10b981"])
            fig_irr.update_traces(hovertemplate="%{x}<br>%{y:,.0f} ریال<extra></extra>",
                                 line=dict(width=3), marker=dict(size=7))
            fig_irr.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13, color="#e6edf3" if _dark else "#1f2937"),
                                 yaxis=dict(tickformat=",.0f"), xaxis=dict(title="تاریخ"),
                                 margin=dict(t=30, b=20, l=10, r=10), hovermode="x unified",
                                 paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                                 plot_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                                 title=dict(text="🇮🇷 ارزش کل به ریال", font=dict(size=14)))
            st.plotly_chart(fig_irr, use_container_width=True)
            fu, lu = timeline["total_usd"].iloc[0], timeline["total_usd"].iloc[-1]
            fi, li = timeline["total_irr"].iloc[0], timeline["total_irr"].iloc[-1]
            g1, g2 = st.columns(2)
            g1.metric("تغییر (دلاری)", f"${lu:,.2f}", delta=f"{lu-fu:+,.2f}")
            g2.metric("تغییر (ریالی)", f"{li:,.0f}", delta=f"{li-fi:+,.0f}")
        else:
            st.info("📊 حداقل دو رکورد لازم است.")
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
                if not name.strip():
                    st.error("نام را وارد کنید.")
                else:
                    aid = datetime.now().isoformat()
                    records = []
                    if q0 > 0 and p0 > 0:
                        records.append({"id": aid + "_r0", "date_gregorian": aid, "date_jalali": today_jalali_str(),
                                       "quantity": q0, "unit_price": p0, "note": note0.strip() or "رکورد اولیه"})
                    data.setdefault("assets", []).append({
                        "id": aid, "name": name.strip(), "icon": init_icon, "color": init_color,
                        "overview_emoji": "",
                        "currency": cur, "created_at_gregorian": aid, "created_at_jalali": today_jalali_str(),
                        "records": records})
                    st.session_state.data = data
                    save_all(data)
                    st.session_state.pending_nav = f"asset_{aid}"
                    st.rerun()
    if assets:
        st.subheader("📝 لیست دارایی‌ها")
        rate, _ = get_current_usd_rate(data)
        for a in assets:
            value, usd_val, rec = compute_asset_value(a, rate)
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 3, 2, 1])
                c1.markdown(f'**<i class="fa-solid {asset_icon(a)}" style="color:{asset_color(a)};"></i> {a["name"]}**', unsafe_allow_html=True)
                c2.caption(currency_label(a["currency"]))
                c3.caption(f"آخرین: {rec['date_jalali'] if rec else '—'}")
                c4.write(f"{fmt_num(value)} {currency_label(a['currency'])}" if value else "—")
                if c5.button("🗑️", key=f"del_asset_{a['id']}"):
                    data["assets"] = [x for x in data["assets"] if x["id"] != a["id"]]
                    st.session_state.data = data
                    save_all(data)
                    st.session_state.pending_nav = "overview"
                    st.rerun()

# ================== صفحه دلار ==================
elif selected == "usd":
    st.header("💵 نرخ دلار")
    st.caption(f"📅 امروز: **{today_jalali_str()}**")
    with st.container(border=True):
        st.subheader("➕ ثبت نرخ")
        with st.form("usd_rate_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 3])
            new_rate = c1.number_input("نرخ (ریال)", min_value=0, step=1000, format="%d")
            note = c2.text_input("توضیح", placeholder="بازار آزاد")
            if st.form_submit_button("💾 ثبت", use_container_width=True):
                if new_rate > 0:
                    now = datetime.now().isoformat()
                    data.setdefault("usd_rates", []).append({
                        "id": now, "rate": new_rate, "note": note.strip(),
                        "created_at": now, "created_at_jalali": today_jalali_str()})
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()

    rates = data.get("usd_rates", [])
    if rates:
        sorted_r = sorted(rates, key=lambda x: x.get("created_at", ""))
        current, current_date = get_current_usd_rate(data)
        c1, c2, c3 = st.columns(3)
        c1.metric("نرخ فعلی", f"{current:,.0f} ریال")
        c2.metric("تعداد", len(rates))
        c3.metric("آخرین", current_date or "—")
        st.subheader("📈 روند")
        chart_df = pd.DataFrame(sorted_r)
        chart_df["تاریخ"] = chart_df["created_at_jalali"]
        fig = px.line(chart_df, x="تاریخ", y="rate", markers=True,
                     labels={"تاریخ": "تاریخ", "rate": "نرخ"})
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
                if c5.button("✏️", key=f"edit_btn_rate_{r['id']}", help="ویرایش"):
                    st.session_state[f"edit_open_rate_{r['id']}"] = not st.session_state.get(f"edit_open_rate_{r['id']}", False)
                if c6.button("🗑️", key=f"delrate_{r['id']}", help="حذف"):
                    data["usd_rates"] = [x for x in data["usd_rates"] if x["id"] != r["id"]]
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()
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
                                st.session_state.data = data
                                st.session_state[f"edit_open_rate_{r['id']}"] = False
                                bump_version(vk)
                                save_all(data)
                                st.rerun()
# ================== صفحه تنظیمات ==================
elif selected == "settings":
    render_settings_page(data)

# ================== صفحه دارایی اختصاصی ==================
elif selected.startswith("asset_"):
    aid = selected.replace("asset_", "")
    asset = next((a for a in assets if a["id"] == aid), None)
    if asset is None:
        st.error("یافت نشد.")
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
                                data["assets"][i]["currency"] = new_cur
                                break
                        st.session_state.data = data
                        bump_version(avk)
                        save_all(data)
                        st.rerun()
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
                            "id": datetime.now().isoformat(), "date_gregorian": giso,
                            "date_jalali": jd.strftime("%Y/%m/%d"),
                            "quantity": qty, "unit_price": price, "note": note.strip()})
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()
                    else:
                        st.error("مقادیر معتبر وارد کنید.")
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
            st.session_state.data = data
            save_all(data)
            st.rerun()

        if st.session_state.get(f"edit_open_rec_{r['id']}", False):
            rvk = f"v_rec_{r['id']}"
            rfk = f"edit_rec_{r['id']}_v{get_version(rvk)}"
            with st.form(rfk):
                ec1, ec2, ec3 = st.columns([2, 2, 2])
                ed_date = ec1.text_input("تاریخ", value=r["date_jalali"])
                ed_qty = ec2.number_input("تعداد", value=float(r["quantity"]), min_value=0.0, format="%.4f", step=1.0)
                ed_price = ec3.number_input(f"قیمت", value=float(r["unit_price"]), min_value=0.0, format="%.2f", step=1000.0)
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
                        bump_version(rvk)
                        save_all(data)
                        st.rerun()
        st.divider()
        with st.expander("⚠️ حذف کل دارایی"):
            ok = st.checkbox("مطمئنم", key=f"confirm_del_{asset['id']}")
            if st.button("🗑️ حذف", disabled=not ok, key=f"del_btn_{asset['id']}"):
                data["assets"] = [x for x in data["assets"] if x["id"] != asset["id"]]
                st.session_state.data = data
                save_all(data)
                st.session_state.pending_nav = "overview"
                st.rerun()
