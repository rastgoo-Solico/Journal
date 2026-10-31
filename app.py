import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import requests
import base64
import hashlib
from datetime import datetime
import jdatetime

# ================== تنظیمات پایه ==================
st.set_page_config(page_title="داشبورد مالی", layout="wide", initial_sidebar_state="expanded")
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
APP_PASSWORD = st.secrets.get("APP_PASSWORD") or "S@mnet11970"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"

def get_auth_token():
    return hashlib.sha256((APP_PASSWORD + "_salt_v2_2024").encode()).hexdigest()

# ================== فونت‌ها ==================
FONTS = {
    "vazirmatn": ("Vazirmatn", "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css"),
    "sahel":     ("Sahel",    "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@v3.4.0/dist/font-face.css"),
    "samim":     ("Samim",    "https://cdn.jsdelivr.net/gh/rastikerdar/samim-font@v4.0.5/dist/font-face.css"),
    "shabnam":   ("Shabnam",  "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@v5.0.1/dist/font-face.css"),
    "markazi":   ("Markazi Text", "https://fonts.googleapis.com/css2?family=Markazi+Text:wght@400;700&display=swap"),
    "noto":      ("Noto Naskh Arabic", "https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;700&display=swap"),
}

# ================== آیکون‌های FA (fallback) ==================
FALLBACK_ICONS = [
    {"class": "fa-folder", "label": "Folder"}, {"class": "fa-coins", "label": "Coins"},
    {"class": "fa-wallet", "label": "Wallet"}, {"class": "fa-money-bill-wave", "label": "Money Bill"},
    {"class": "fa-dollar-sign", "label": "Dollar"}, {"class": "fa-euro-sign", "label": "Euro"},
    {"class": "fa-building-columns", "label": "Bank"}, {"class": "fa-piggy-bank", "label": "Piggy Bank"},
    {"class": "fa-vault", "label": "Vault"}, {"class": "fa-gem", "label": "Gem"},
    {"class": "fa-crown", "label": "Crown"}, {"class": "fa-house", "label": "House"},
    {"class": "fa-building", "label": "Building"}, {"class": "fa-warehouse", "label": "Warehouse"},
    {"class": "fa-car", "label": "Car"}, {"class": "fa-truck", "label": "Truck"},
    {"class": "fa-chart-line", "label": "Chart Line"}, {"class": "fa-chart-pie", "label": "Chart Pie"},
    {"class": "fa-arrow-trend-up", "label": "Trend Up"}, {"class": "fa-bitcoin-sign", "label": "Bitcoin"},
    {"class": "fa-ethereum", "label": "Ethereum"}, {"class": "fa-landmark", "label": "Landmark"},
    {"class": "fa-hand-holding-dollar", "label": "Hand Dollar"}, {"class": "fa-industry", "label": "Industry"},
    {"class": "fa-seedling", "label": "Seedling"}, {"class": "fa-briefcase", "label": "Briefcase"},
    {"class": "fa-store", "label": "Store"}, {"class": "fa-sack-dollar", "label": "Sack Dollar"},
    {"class": "fa-receipt", "label": "Receipt"}, {"class": "fa-tag", "label": "Tag"},
    {"class": "fa-file-invoice-dollar", "label": "Invoice"}, {"class": "fa-percent", "label": "Percent"},
    {"class": "fa-scale-balanced", "label": "Scale"}, {"class": "fa-shield-halved", "label": "Shield"},
    {"class": "fa-fire", "label": "Fire"}, {"class": "fa-droplet", "label": "Droplet"},
    {"class": "fa-gas-pump", "label": "Gas Pump"}, {"class": "fa-bolt", "label": "Bolt"},
    {"class": "fa-wheat-awn", "label": "Wheat"}, {"class": "fa-folder-open", "label": "Folder Open"},
    {"class": "fa-box", "label": "Box"}, {"class": "fa-cubes", "label": "Cubes"},
    {"class": "fa-gear", "label": "Gear"}, {"class": "fa-plus", "label": "Plus"},
    {"class": "fa-circle-plus", "label": "Circle Plus"}, {"class": "fa-list", "label": "List"},
]

@st.cache_data(ttl=86400, show_spinner=False)
def load_fa_icons():
    try:
        r = requests.get("https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/metadata/icons.json", timeout=15)
        if r.status_code == 200:
            meta = r.json()
            icons = []
            for name, info in meta.items():
                if "solid" in info.get("free", []):
                    icons.append({
                        "class": f"fa-{name}",
                        "label": info.get("label", name.replace("-", " ").title()),
                        "categories": info.get("categories", []),
                    })
            if icons:
                return sorted(icons, key=lambda x: x["label"].lower())
    except Exception:
        pass
    return FALLBACK_ICONS

EMOJI_FALLBACK = {
    "fa-folder": "📁", "fa-coins": "🪙", "fa-wallet": "👛", "fa-money-bill-wave": "💵",
    "fa-dollar-sign": "💲", "fa-building-columns": "🏦", "fa-gem": "💎", "fa-crown": "👑",
    "fa-house": "🏠", "fa-building": "🏢", "fa-warehouse": "🏭", "fa-car": "🚗",
    "fa-truck": "🚚", "fa-chart-line": "📈", "fa-chart-pie": "📊", "fa-arrow-trend-up": "📈",
    "fa-bitcoin-sign": "₿", "fa-ethereum": "Ξ", "fa-landmark": "🏛️", "fa-industry": "🏭",
    "fa-seedling": "🌱", "fa-briefcase": "💼", "fa-store": "🏪", "fa-sack-dollar": "💰",
    "fa-receipt": "🧾", "fa-tag": "🏷️", "fa-shield-halved": "🛡️", "fa-fire": "🔥",
    "fa-bolt": "⚡", "fa-box": "📦", "fa-piggy-bank": "🐷", "fa-vault": "🔐",
}

def icon_emoji(fa_class):
    return EMOJI_FALLBACK.get(fa_class, "📁")

# ================== پیش‌فرض‌های تنظیمات ==================
DEFAULT_NAV_ICONS = {
    "overview": {"icon": "fa-chart-pie", "color": "#3b82f6"},
    "journal": {"icon": "fa-circle-plus", "color": "#10b981"},
    "usd": {"icon": "fa-dollar-sign", "color": "#f59e0b"},
    "settings": {"icon": "fa-gear", "color": "#6b7280"},
}
NAV_LABELS = {"overview": "نمای کلی", "journal": "افزودن دارایی", "usd": "دلار", "settings": "تنظیمات"}

# ================== توابع تاریخ ==================
def today_jalali_str():
    return jdatetime.date.today().strftime("%Y/%m/%d")

def iso_to_jalali(iso_str, with_time=True):
    if not iso_str:
        return "—"
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
        if len(parts) != 3:
            return None
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

# ================== CSS ==================
_font_imports = "\n".join(f"@import url('{url}');" for _, (_, url) in FONTS.items())
st.markdown(f"""
<style>
    {_font_imports}
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

    * {{ font-family: 'Vazirmatn', Tahoma, sans-serif !important; }}
    .fa, .fas, .far, .fal, .fat, .fab, .fad, .fa-solid, .fa-regular, .fa-brands {{
        font-family: "Font Awesome 6 Free", "Font Awesome 6 Brands" !important;
        font-feature-settings: normal !important;
    }}
    .material-symbols-rounded, .material-symbols-outlined, .material-symbols-sharp,
    .material-icons, .material-icons-round, .material-icons-outlined, .material-icons-two-tone, .material-icons-sharp,
    span[data-testid="stExpanderToggleIcon"], span[data-testid="stTooltipIcon"], span[data-testid="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        font-feature-settings: 'liga' !important;
    }}
    .stApp {{ direction: rtl; }}
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stCaption, .stText {{ text-align: right !important; }}
    input, textarea, select {{ direction: rtl !important; text-align: right !important; }}
    table {{ direction: rtl !important; }}
    table th, table td {{ text-align: right !important; }}
    .block-container {{ padding-top: 4.5rem !important; padding-bottom: 2.5rem !important; max-width: 1250px !important; }}
    header[data-testid="stHeader"] {{ z-index: 999 !important; }}
    section[data-testid="stSidebar"] {{ direction: rtl !important; }}
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label {{ text-align: right !important; }}
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {{ font-size: 1.3rem !important; white-space: normal !important; overflow: visible !important; word-break: break-word !important; }}
    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button {{ width: 100% !important; }}

    /* ===== ناوبری سفارشی با FA ===== */
    .fa-nav {{
        display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
        border-bottom: 1px solid #e5e7eb; margin-bottom: 1.5rem;
        padding-bottom: 0; direction: rtl;
    }}
    .fa-nav-btn {{
        display: inline-flex; align-items: center; gap: 6px;
        padding: 10px 14px; text-decoration: none;
        color: #4b5563 !important;
        border-bottom: 3px solid transparent;
        font-weight: 500; font-size: 0.95rem;
        transition: all 0.15s; white-space: nowrap;
    }}
    .fa-nav-btn:hover {{ background: #f3f4f6; color: #1d4ed8 !important; }}
    .fa-nav-btn.active {{ border-bottom-color: #3b82f6; color: #1d4ed8 !important; font-weight: 700; }}
    .fa-nav-btn i {{ font-size: 1.15rem; }}

    @media (max-width: 768px) {{
        .block-container {{ padding-top: 4rem !important; padding-left: 0.6rem !important; padding-right: 0.6rem !important; padding-bottom: 2rem !important; }}
        h1 {{ font-size: 1.35rem !important; }} h2 {{ font-size: 1.1rem !important; }}
        h3 {{ font-size: 0.98rem !important; }} h4 {{ font-size: 0.92rem !important; }}
        [data-testid="stMetricValue"] {{ font-size: 1.05rem !important; }}
        [data-testid="stMetricLabel"] {{ font-size: 0.78rem !important; }}
        [data-testid="stMetricDelta"] {{ font-size: 0.72rem !important; }}
        [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; }}
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {{ flex: 1 1 100% !important; min-width: 100% !important; width: 100% !important; }}
        [data-testid="stDataFrame"] {{ font-size: 0.8rem !important; }}
        [data-testid="stMainBlockContainer"] .stButton > button {{ width: 100% !important; }}
        .fa-nav {{ overflow-x: auto; flex-wrap: nowrap; -webkit-overflow-scrolling: touch; }}
        .fa-nav-btn {{ flex-shrink: 0; font-size: 0.85rem; padding: 8px 10px; }}
    }}
    @media (max-width: 400px) {{
        .block-container {{ padding-left: 0.4rem !important; padding-right: 0.4rem !important; }}
        h1 {{ font-size: 1.2rem !important; }}
    }}
</style>
""", unsafe_allow_html=True)

# ================== 🔐 احراز هویت ==================
AUTH_TOKEN = get_auth_token()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# بازیابی auth از URL (پس از بارگذاری صفحه یا کلیک لینک)
if not st.session_state.authenticated:
    qp_auth = st.query_params.get("auth")
    if qp_auth and qp_auth == AUTH_TOKEN:
        st.session_state.authenticated = True

def render_login():
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
                        st.session_state.login_attempts = 0
                        st.query_params["auth"] = AUTH_TOKEN
                        st.rerun()
                    else:
                        st.session_state.login_attempts = st.session_state.get("login_attempts", 0) + 1
                        st.error("❌ رمز عبور اشتباه است.")

if not st.session_state.authenticated:
    render_login()
    st.stop()

# ================== GitHub ==================
def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

@st.cache_data(ttl=120, show_spinner=False)
def check_github_status(token, repo):
    if not token and not repo: return "no_config", "تنظیم نشده"
    if not token: return "no_token", "توکن ندارد"
    if not repo: return "no_repo", "مخزن ندارد"
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}",
                         headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}, timeout=8)
        if r.status_code == 200: return "ok", f"متصل به {repo}"
        if r.status_code == 401: return "error", "توکن نامعتبر (401)"
        if r.status_code == 404: return "error", f"مخزن یافت نشد (404)"
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
    except Exception as e:
        st.warning(f"⚠️ ذخیره محلی ناموفق: {e}")
        return False

def load_github_file():
    if not GITHUB_TOKEN or not GITHUB_REPO: return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(url, headers=github_headers(), timeout=10)
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
    except Exception:
        pass
    return None

def save_github_file(data):
    if not GITHUB_TOKEN or not GITHUB_REPO: return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    sha = None
    try:
        r = requests.get(url, headers=github_headers(), timeout=10)
        if r.status_code == 200:
            sha = r.json()["sha"]
    except Exception:
        pass
    payload = {
        "message": f"update {today_jalali_str()} {datetime.now().strftime('%H:%M')}",
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    try:
        r = requests.put(url, headers=github_headers(), json=payload, timeout=15)
        return r.status_code in (200, 201)
    except Exception:
        return False

# ================== مهاجرت ==================
def migrate_data(data):
    if not isinstance(data, dict) or not data:
        return {"assets": [], "usd_rates": [], "settings": {"font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy()}}
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list):
        old = data.get("usd_rate")
        data["usd_rates"] = []
        if old:
            data["usd_rates"].append({"id": datetime.now().isoformat(), "rate": old, "note": "منتقل‌شده",
                                     "created_at": datetime.now().isoformat(), "created_at_jalali": today_jalali_str()})
        data.pop("usd_rate", None)
    if "journals" in data and isinstance(data.get("journals"), list):
        if "assets" not in data or not isinstance(data.get("assets"), list):
            data["assets"] = []
        for j in data.get("journals", []):
            aid = j.get("id") or datetime.now().isoformat()
            ciso = j.get("created_at_gregorian") or j.get("created_at") or datetime.now().isoformat()
            cjal = j.get("created_at_jalali") or iso_to_jalali(ciso, with_time=False)
            data["assets"].append({
                "id": aid, "name": j.get("asset_name", "بدون نام"), "icon": "fa-folder", "color": "#3b82f6",
                "currency": j.get("currency", "IRR"), "created_at_gregorian": ciso, "created_at_jalali": cjal,
                "records": [{"id": aid + "_r", "date_gregorian": ciso, "date_jalali": cjal,
                             "quantity": j.get("amount", 0), "unit_price": 1, "note": "منتقل‌شده"}],
            })
        data.pop("journals", None)
    if "assets" not in data or not isinstance(data.get("assets"), list): data["assets"] = []
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list): data["usd_rates"] = []

    # settings
    if "settings" not in data or not isinstance(data.get("settings"), dict):
        data["settings"] = {"font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy()}
    data["settings"].setdefault("font", "vazirmatn")
    if "nav_icons" not in data["settings"] or not isinstance(data["settings"]["nav_icons"], dict):
        data["settings"]["nav_icons"] = DEFAULT_NAV_ICONS.copy()
    for k, v in DEFAULT_NAV_ICONS.items():
        if k not in data["settings"]["nav_icons"] or not isinstance(data["settings"]["nav_icons"][k], dict):
            data["settings"]["nav_icons"][k] = v.copy()
        else:
            data["settings"]["nav_icons"][k].setdefault("icon", v["icon"])
            data["settings"]["nav_icons"][k].setdefault("color", v["color"])

    # نرمال‌سازی آیکون و رنگ دارایی‌ها
    for a in data["assets"]:
        if not isinstance(a.get("icon"), str):
            a["icon"] = "fa-folder"
        elif not a["icon"].startswith("fa-"):
            # ایموجی قدیمی → آیکون FA
            a["icon"] = "fa-folder"
        a.setdefault("color", "#3b82f6")
    return data

def load_all():
    local = load_local_file()
    if local and (local.get("assets") or local.get("journals") or local.get("usd_rates")):
        return migrate_data(local)
    gh = load_github_file()
    if gh:
        return migrate_data(gh)
    return {"assets": [], "usd_rates": [], "settings": {"font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy()}}

def save_all(data):
    l_ok = save_local_file(data)
    g_ok = save_github_file(data)
    if l_ok and g_ok: st.toast("ذخیره شد (محلی + GitHub)", icon="✅")
    elif l_ok: st.toast("ذخیره محلی ✅", icon="💾")
    elif g_ok: st.toast("ذخیره GitHub ✅", icon="☁️")
    else: st.error("⚠️ ذخیره ناموفق!")

# ================== توابع کمکی ==================
def get_settings(data):
    s = data.get("settings") or {}
    return {"font": s.get("font", "vazirmatn"), "nav_icons": s.get("nav_icons", DEFAULT_NAV_ICONS)}

def asset_icon(asset):
    ic = asset.get("icon", "fa-folder")
    return ic if isinstance(ic, str) and ic.startswith("fa-") else "fa-folder"

def asset_color(asset):
    return asset.get("color", "#3b82f6")

def asset_icon_emoji(asset):
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
    if key not in st.session_state:
        st.session_state[key] = 0
    return st.session_state[key]

def bump_version(key):
    st.session_state[key] = st.session_state.get(key, 0) + 1

def build_portfolio_timeline(data):
    assets = data.get("assets", [])
    usd_rates = sorted(data.get("usd_rates", []), key=lambda x: x.get("created_at", ""))
    all_dates = set()
    for a in assets:
        for r in a.get("records", []):
            if r.get("date_gregorian"):
                all_dates.add(r["date_gregorian"][:10])
    for r in usd_rates:
        if r.get("created_at"):
            all_dates.add(r["created_at"][:10])
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

# ================== مقداردهی ==================
if "data" not in st.session_state:
    st.session_state.data = load_all()
st.session_state.data = migrate_data(st.session_state.data)
data = st.session_state.data
data.setdefault("assets", [])
data.setdefault("usd_rates", [])

# ================== اعمال فونت ==================
_settings = get_settings(data)
_fkey = _settings["font"] if _settings["font"] in FONTS else "vazirmatn"
_fname = FONTS[_fkey][0]
st.markdown(f"""
<style>
    * {{ font-family: '{_fname}', 'Vazirmatn', Tahoma, sans-serif !important; }}
    .fa, .fas, .far, .fal, .fat, .fab, .fad, .fa-solid, .fa-regular, .fa-brands {{
        font-family: "Font Awesome 6 Free", "Font Awesome 6 Brands" !important;
    }}
    .material-symbols-rounded, .material-symbols-outlined, .material-icons,
    span[data-testid="stExpanderToggleIcon"], span[data-testid="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    }}
</style>
""", unsafe_allow_html=True)

# ================== سایدبار ==================
with st.sidebar:
    st.markdown(f"### 🗓️ امروز: **{today_jalali_str()}**")
    st.caption(f"میلادی: {datetime.now().strftime('%Y-%m-%d')}")
    if st.button("🚪 خروج از حساب", use_container_width=True, key="logout_btn"):
        st.session_state.authenticated = False
        st.session_state.login_attempts = 0
        st.session_state.pop("data", None)
        st.query_params.clear()
        st.rerun()
    st.divider()

    rate, rate_date = get_current_usd_rate(data)
    if rate:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); padding: 14px 16px; border-radius: 10px; border-right: 4px solid #3b82f6; margin-bottom: 12px; direction: rtl; text-align: right;">
            <div style="font-size: 0.82rem; color: #6b7280; margin-bottom: 6px;">💵 نرخ فعلی دلار</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #1e40af; line-height: 1.2;">{rate:,.0f}<span style="font-size: 0.95rem; color: #6b7280;"> ریال</span></div>
            <div style="font-size: 0.72rem; color: #9ca3af; margin-top: 6px;">آخرین بروزرسانی: {rate_date}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("💡 هنوز نرخی ثبت نشده. از تب «دلار» ثبت کنید.")

    st.divider()
    st.markdown("**💾 وضعیت ذخیره‌سازی**")
    local_ok = os.path.exists(DATA_FILE)
    gh_status, gh_message = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
    c1, c2 = st.columns(2)
    c1.caption(f"{'✅' if local_ok else '❌'} محلی")
    c2.caption(f"{'✅' if gh_status == 'ok' else '❌'} GitHub")
    if gh_status != "ok":
        st.warning(f"{gh_message}", icon="⚠️")
    st.divider()

    with st.expander("📥 پشتیبان‌گیری / 📤 بازیابی", expanded=False):
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

# ================== ناوبری HTML با FA ==================
assets = data.get("assets", [])
# ترتیب: overview → journal → usd → دارایی‌ها → settings (تنظیمات همیشه آخر)
nav_options = ["overview", "journal", "usd"]
for a in assets:
    nav_options.append(f"asset_{a['id']}")
nav_options.append("settings")

# خواندن انتخاب فعلی
qp_nav = st.query_params.get("nav")
if "pending_nav" in st.session_state:
    st.session_state.nav_tab = st.session_state.pending_nav
    st.query_params["nav"] = st.session_state.pending_nav
    del st.session_state.pending_nav
elif qp_nav and qp_nav in nav_options:
    st.session_state.nav_tab = qp_nav
elif "nav_tab" not in st.session_state or st.session_state.nav_tab not in nav_options:
    st.session_state.nav_tab = "overview"

selected = st.session_state.nav_tab

# رندر نوار ناوبری
_nav_icons = _settings["nav_icons"]
_nav_html = ['<div class="fa-nav">']
for opt in nav_options:
    if opt in ("overview", "journal", "usd", "settings"):
        cfg = _nav_icons.get(opt, DEFAULT_NAV_ICONS[opt])
        ic, col, lbl = cfg["icon"], cfg["color"], NAV_LABELS[opt]
    else:
        aid = opt.replace("asset_", "")
        a = next((x for x in assets if x["id"] == aid), None)
        if a is None: continue
        ic, col, lbl = asset_icon(a), asset_color(a), a["name"]
    active_cls = " active" if opt == selected else ""
    _nav_html.append(
        f'<a href="?nav={opt}&auth={AUTH_TOKEN}" class="fa-nav-btn{active_cls}" target="_self">'
        f'<i class="fa-solid {ic}" style="color:{col};"></i>'
        f'<span class="nav-label">{lbl}</span></a>'
    )
_nav_html.append("</div>")
st.markdown("".join(_nav_html), unsafe_allow_html=True)

# ================== صفحه تنظیمات ==================
def render_settings_page(data):
    st.header("⚙️ تنظیمات")
    settings = get_settings(data)

    # تقسیم به تب‌های داخلی
    t_font, t_nav, t_assets, t_lib, t_storage = st.tabs([
        "🔤 فونت", "🎨 آیکون‌های منو", "📦 آیکون دارایی‌ها", "📚 کتابخانه آیکون", "💾 وضعیت"
    ])

    # ----- فونت -----
    with t_font:
        st.subheader("فونت برنامه")
        font_keys = list(FONTS.keys())
        cur_idx = font_keys.index(settings["font"]) if settings["font"] in font_keys else 0
        new_font = st.selectbox("انتخاب فونت", options=font_keys, index=cur_idx,
                               format_func=lambda k: FONTS[k][0], key="settings_font_select")
        st.markdown(
            f'<div style="padding:16px; border:1px solid #e5e7eb; border-radius:8px; margin-top:12px; font-family:\'{FONTS[new_font][0]}\', Tahoma;">'
            f'<div style="font-size:1.4rem; margin-bottom:8px;">نمونه متن با فونت {FONTS[new_font][0]}</div>'
            f'<div>این یک متن آزمایشی فارسی است. اعداد: ۱۲۳۴۵۶۷۸۹۰</div>'
            f'</div>', unsafe_allow_html=True)
        if st.button("💾 ذخیره فونت", use_container_width=True, key="save_font_btn"):
            data["settings"]["font"] = new_font
            st.session_state.data = data
            save_all(data)
            st.rerun()

    # ----- آیکون‌های منو -----
    with t_nav:
        st.subheader("آیکون و رنگ منو")
        st.caption("هر آیتم منو را با آیکون و رنگ دلخواه سفارشی کنید.")
        all_icons = load_fa_icons()
        all_classes = [ic["class"] for ic in all_icons]
        labels_map = {ic["class"]: f'{ic["label"]} ({ic["class"]})' for ic in all_icons}

        for nav_key in ["overview", "journal", "usd", "settings"]:
            cfg = settings["nav_icons"].get(nav_key, DEFAULT_NAV_ICONS[nav_key])
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 2, 3, 2])
                c1.markdown(
                    f'<div style="text-align:center; padding:10px;">'
                    f'<i class="fa-solid {cfg["icon"]}" style="color:{cfg["color"]}; font-size:2.2rem;"></i></div>',
                    unsafe_allow_html=True)
                c2.markdown(f"**{NAV_LABELS[nav_key]}**")
                search_n = c3.text_input("جستجو", key=f"search_nav_{nav_key}",
                                        placeholder="جستجوی آیکون...", label_visibility="collapsed")
                if search_n:
                    q = search_n.lower()
                    filtered = [c for c in all_classes if q in c.lower() or q in labels_map.get(c, "").lower()]
                else:
                    filtered = all_classes
                if cfg["icon"] not in filtered:
                    filtered = [cfg["icon"]] + filtered[:200]
                else:
                    filtered = filtered[:200]
                idx = filtered.index(cfg["icon"]) if cfg["icon"] in filtered else 0
                new_icon = c3.selectbox("آیکون جدید", options=filtered, index=idx,
                                       format_func=lambda c: labels_map.get(c, c),
                                       key=f"pick_nav_{nav_key}", label_visibility="collapsed")
                new_color = c4.color_picker("رنگ", value=cfg["color"], key=f"color_nav_{nav_key}")
                if st.button("💾 ذخیره", key=f"save_nav_{nav_key}", use_container_width=True):
                    data["settings"]["nav_icons"][nav_key] = {"icon": new_icon, "color": new_color}
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()

    # ----- آیکون دارایی‌ها -----
    with t_assets:
        st.subheader("آیکون و رنگ دارایی‌ها")
        if not assets:
            st.info("هنوز دارایی‌ای ثبت نشده.")
        else:
            all_icons = load_fa_icons()
            all_classes = [ic["class"] for ic in all_icons]
            labels_map = {ic["class"]: f'{ic["label"]} ({ic["class"]})' for ic in all_icons}
            for a in assets:
                cur_ic = asset_icon(a); cur_col = asset_color(a)
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1, 2, 3, 2])
                    c1.markdown(
                        f'<div style="text-align:center; padding:10px;">'
                        f'<i class="fa-solid {cur_ic}" style="color:{cur_col}; font-size:2.2rem;"></i></div>',
                        unsafe_allow_html=True)
                    c2.markdown(f"**{a['name']}**")
                    search_a = c3.text_input("جستجو", key=f"search_asset_{a['id']}",
                                            placeholder="جستجوی آیکون...", label_visibility="collapsed")
                    if search_a:
                        q = search_a.lower()
                        filtered = [c for c in all_classes if q in c.lower() or q in labels_map.get(c, "").lower()]
                    else:
                        filtered = all_classes
                    if cur_ic not in filtered:
                        filtered = [cur_ic] + filtered[:200]
                    else:
                        filtered = filtered[:200]
                    idx = filtered.index(cur_ic) if cur_ic in filtered else 0
                    new_icon = c3.selectbox("آیکون", options=filtered, index=idx,
                                           format_func=lambda c: labels_map.get(c, c),
                                           key=f"pick_asset_{a['id']}", label_visibility="collapsed")
                    new_color = c4.color_picker("رنگ", value=cur_col, key=f"color_asset_{a['id']}")
                    if st.button("💾 ذخیره", key=f"save_asset_{a['id']}", use_container_width=True):
                        for i, x in enumerate(data["assets"]):
                            if x["id"] == a["id"]:
                                data["assets"][i]["icon"] = new_icon
                                data["assets"][i]["color"] = new_color
                                break
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()

    # ----- کتابخانه -----
    with t_lib:
        st.subheader("📚 کتابخانه کامل آیکون‌های Font Awesome")
        all_icons = load_fa_icons()
        st.caption(f"مجموعاً **{len(all_icons)}** آیکون رایگان Font Awesome در دسترس.")
        search_lib = st.text_input("🔍 جستجو", key="fa_lib_search", placeholder="مثلاً: money, chart, home...")
        if search_lib:
            q = search_lib.lower()
            filtered = [ic for ic in all_icons if q in ic["label"].lower() or q in ic["class"].lower()]
        else:
            filtered = all_icons
        display = filtered[:120]
        st.caption(f"**{len(filtered)}** یافت شد — نمایش {len(display)} مورد اول.")
        for i in range(0, len(display), 8):
            cols = st.columns(8)
            for j, ic in enumerate(display[i:i+8]):
                with cols[j]:
                    st.markdown(
                        f'<div style="text-align:center; padding:8px; border:1px solid #e5e7eb; border-radius:6px; margin:2px;" title="{ic["class"]}">'
                        f'<i class="fa-solid {ic["class"]}" style="font-size:1.4rem; color:#3b82f6;"></i>'
                        f'<div style="font-size:0.6rem; margin-top:4px; color:#6b7280; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{ic["label"]}</div>'
                        f'</div>', unsafe_allow_html=True)

    # ----- وضعیت -----
    with t_storage:
        st.subheader("💾 وضعیت اتصال و ذخیره‌سازی")
        local_ok = os.path.exists(DATA_FILE)
        gh_status, gh_msg = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📁 فایل محلی**")
            if local_ok:
                st.success(f"✅ فعال ({os.path.getsize(DATA_FILE):,} بایت)")
            else:
                st.error("❌ فایل یافت نشد")
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
        c1, c2, c3 = st.columns(3)
        c1.metric("دارایی‌ها", len(data.get("assets", [])))
        c2.metric("رکوردها", sum(len(a.get("records", [])) for a in data.get("assets", [])))
        c3.metric("نرخ دلار", len(data.get("usd_rates", [])))

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
            rows.append({"دارایی": f"{asset_icon_emoji(a)} {a['name']}", "ارز": currency_label(a["currency"]),
                         "تعداد": rec["quantity"] if rec else 0, "قیمت واحد": rec["unit_price"] if rec else 0,
                         "ارزش": value, "معادل_دلاری": usd_val, "آخرین_تاریخ": rec["date_jalali"] if rec else "—"})
        df = pd.DataFrame(rows)
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 کل ارزش (دلاری)", f"${total_usd:,.2f}")
        c2.metric("📁 تعداد دارایی‌ها", len(assets))
        c3.metric("💵 نرخ دلار", f"{rate:,.0f} ریال" if rate else "ثبت نشده")

        st.subheader("🥧 ترکیب دارایی‌ها")
        pie_df = df.dropna(subset=["معادل_دلاری"])
        pie_df = pie_df[pie_df["معادل_دلاری"] > 0]
        if not pie_df.empty:
            fig = px.pie(pie_df, values="معادل_دلاری", names="دارایی", hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=14),
                             legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                             margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("برای پای‌چارت، ابتدا نرخ دلار را ثبت کنید.")

        st.subheader("📈 روند رشد ارزش کل دارایی")
        timeline = build_portfolio_timeline(data)
        if len(timeline) >= 2:
            fig_usd = px.line(timeline, x="date_jalali", y="total_usd", markers=True,
                             labels={"date_jalali": "تاریخ", "total_usd": "دلار"},
                             color_discrete_sequence=["#3b82f6"])
            fig_usd.update_traces(hovertemplate="تاریخ: %{x}<br>$%{y:,.2f}<extra></extra>",
                                 line=dict(width=3), marker=dict(size=7))
            fig_usd.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13),
                                 yaxis=dict(tickformat=",.0f"), xaxis=dict(title="تاریخ"),
                                 margin=dict(t=30, b=20, l=10, r=10), hovermode="x unified",
                                 title=dict(text="💵 ارزش کل به دلار", font=dict(size=14)))
            st.plotly_chart(fig_usd, use_container_width=True)

            fig_irr = px.line(timeline, x="date_jalali", y="total_irr", markers=True,
                             labels={"date_jalali": "تاریخ", "total_irr": "ریال"},
                             color_discrete_sequence=["#10b981"])
            fig_irr.update_traces(hovertemplate="تاریخ: %{x}<br>%{y:,.0f} ریال<extra></extra>",
                                 line=dict(width=3), marker=dict(size=7))
            fig_irr.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13),
                                 yaxis=dict(tickformat=",.0f"), xaxis=dict(title="تاریخ"),
                                 margin=dict(t=30, b=20, l=10, r=10), hovermode="x unified",
                                 title=dict(text="🇮🇷 ارزش کل به ریال", font=dict(size=14)))
            st.plotly_chart(fig_irr, use_container_width=True)

            fu, lu = timeline["total_usd"].iloc[0], timeline["total_usd"].iloc[-1]
            fi, li = timeline["total_irr"].iloc[0], timeline["total_irr"].iloc[-1]
            pu = ((lu/fu - 1)*100) if fu else 0
            pi = ((li/fi - 1)*100) if fi else 0
            g1, g2 = st.columns(2)
            g1.metric("تغییر (دلاری)", f"${lu:,.2f}", delta=f"{lu-fu:+,.2f} ({pu:+.1f}%)")
            g2.metric("تغییر (ریالی)", f"{li:,.0f} ریال", delta=f"{li-fi:+,.0f} ({pi:+.1f}%)")
        elif len(timeline) == 1:
            st.info("📊 حداقل دو رکورد در تاریخ‌های مختلف لازم است.")
        else:
            st.info("📊 هنوز رکوردی ثبت نشده.")

        st.subheader("📋 جدول دارایی‌ها")
        disp = df.copy()
        disp["تعداد"] = disp["تعداد"].apply(fmt_num)
        disp["قیمت واحد"] = disp.apply(lambda r: f"{fmt_num(r['قیمت واحد'])} {r['ارز']}" if r['قیمت واحد'] else "—", axis=1)
        disp["ارزش"] = disp.apply(lambda r: f"{fmt_num(r['ارزش'])} {r['ارز']}" if r['ارزش'] else "—", axis=1)
        disp["معادل_دلاری"] = disp["معادل_دلاری"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
        disp = disp[["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل_دلاری", "آخرین_تاریخ"]]
        disp.columns = ["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل دلاری", "آخرین بروزرسانی"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

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
            name = c1.text_input("نام دارایی", placeholder="طلا، سهام، بیت‌کوین...")
            cur = c2.selectbox("ارز", ["IRR", "USD"], format_func=lambda x: "ریال" if x == "IRR" else "دلار")
            init_icon = c3.selectbox("آیکون اولیه", options=all_classes, index=all_classes.index("fa-coins"),
                                     format_func=lambda c: labels_map.get(c, c), key="new_asset_icon")
            c4, c5 = st.columns(2)
            init_color = c4.color_picker("رنگ آیکون", value="#3b82f6", key="new_asset_color")
            st.markdown("**📝 رکورد اولیه (اختیاری)**")
            c6, c7, c8 = st.columns([2, 2, 3])
            q0 = c6.number_input("تعداد اولیه", min_value=0.0, format="%.4f", step=1.0)
            p0 = c7.number_input("قیمت واحد اولیه", min_value=0.0, format="%.2f", step=1000.0)
            note0 = c8.text_input("توضیح", placeholder="اختیاری")
            if st.form_submit_button("💾 ایجاد دارایی", use_container_width=True):
                if not name.strip():
                    st.error("نام دارایی را وارد کنید.")
                else:
                    aid = datetime.now().isoformat()
                    records = []
                    if q0 > 0 and p0 > 0:
                        records.append({"id": aid + "_r0", "date_gregorian": aid, "date_jalali": today_jalali_str(),
                                       "quantity": q0, "unit_price": p0, "note": note0.strip() or "رکورد اولیه"})
                    data.setdefault("assets", []).append({
                        "id": aid, "name": name.strip(), "icon": init_icon, "color": init_color,
                        "currency": cur, "created_at_gregorian": aid, "created_at_jalali": today_jalali_str(),
                        "records": records,
                    })
                    st.session_state.data = data
                    save_all(data)
                    st.session_state.pending_nav = f"asset_{aid}"
                    st.rerun()

    if not assets:
        st.info("هنوز دارایی‌ای ثبت نشده.")
    else:
        st.subheader("📝 لیست دارایی‌ها")
        rate, _ = get_current_usd_rate(data)
        for a in assets:
            value, usd_val, rec = compute_asset_value(a, rate)
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 3, 2, 1])
                c1.markdown(
                    f'**<i class="fa-solid {asset_icon(a)}" style="color:{asset_color(a)};"></i> {a["name"]}**',
                    unsafe_allow_html=True)
                c2.caption(currency_label(a["currency"]))
                c3.caption(f"آخرین رکورد: {rec['date_jalali'] if rec else '—'}")
                c4.write(f"{fmt_num(value)} {currency_label(a['currency'])}" if value else "—")
                if c5.button("🗑️", key=f"del_asset_{a['id']}", help="حذف"):
                    data["assets"] = [x for x in data["assets"] if x["id"] != a["id"]]
                    st.session_state.data = data
                    save_all(data)
                    st.session_state.pending_nav = "overview"
                    st.rerun()

# ================== صفحه دلار ==================
elif selected == "usd":
    st.header("💵 نرخ دلار به ریال")
    st.caption(f"📅 امروز — شمسی: **{today_jalali_str()}**")
    with st.container(border=True):
        st.subheader("➕ ثبت نرخ جدید")
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
                else:
                    st.error("نرخ باید بزرگتر از صفر باشد.")
    rates = data.get("usd_rates", [])
    if not rates:
        st.info("هنوز نرخی ثبت نشده.")
    else:
        sorted_r = sorted(rates, key=lambda x: x.get("created_at", ""))
        current, current_date = get_current_usd_rate(data)
        c1, c2, c3 = st.columns(3)
        c1.metric("نرخ فعلی", f"{current:,.0f} ریال")
        c2.metric("تعداد ثبت", len(rates))
        c3.metric("آخرین بروزرسانی", current_date or "—")
        st.subheader("📈 روند نرخ دلار")
        chart_df = pd.DataFrame(sorted_r)
        chart_df["تاریخ"] = chart_df["created_at_jalali"]
        fig = px.line(chart_df, x="تاریخ", y="rate", markers=True,
                     labels={"تاریخ": "تاریخ", "rate": "نرخ (ریال)"})
        fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13), margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("📋 تاریخچه نرخ‌ها")
        for r in reversed(sorted_r):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 3, 1])
                c1.markdown(f"**{r['rate']:,.0f} ریال**")
                c2.caption(f"📅 {r.get('created_at_jalali', '—')}")
                c3.caption(r.get("note", "—") or "—")
                c4.caption(iso_to_jalali(r.get("created_at", ""), with_time=True))
                if c5.button("🗑️", key=f"delrate_{r['id']}", help="حذف"):
                    data["usd_rates"] = [x for x in data["usd_rates"] if x["id"] != r["id"]]
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()
                vk = f"v_rate_{r['id']}"
                fk = f"edit_rate_{r['id']}_v{get_version(vk)}"
                with st.expander("✏️ ویرایش"):
                    with st.form(fk):
                        ec1, ec2 = st.columns([2, 3])
                        er_date = ec1.text_input("تاریخ (شمسی)", value=r.get("created_at_jalali", today_jalali_str()))
                        er_rate = ec2.number_input("نرخ", value=int(r["rate"]), min_value=1, step=1000, format="%d")
                        er_note = st.text_input("توضیح", value=r.get("note", ""))
                        if st.form_submit_button("💾 ذخیره", use_container_width=True):
                            jd = parse_jalali(er_date)
                            if jd is None:
                                st.error("تاریخ نامعتبر.")
                            elif er_rate <= 0:
                                st.error("نرخ باید > 0 باشد.")
                            else:
                                tp = r["created_at"][11:16] if len(r.get("created_at", "")) >= 16 else "00:00"
                                giso = jalali_to_gregorian_iso(jd, tp)
                                for i, x in enumerate(data["usd_rates"]):
                                    if x["id"] == r["id"]:
                                        data["usd_rates"][i] = {"id": r["id"], "rate": er_rate, "note": er_note.strip(),
                                                               "created_at": giso, "created_at_jalali": jd.strftime("%Y/%m/%d")}
                                        break
                                st.session_state.data = data
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
        st.error("دارایی یافت نشد.")
    else:
        rate, _ = get_current_usd_rate(data)
        value, usd_val, rec = compute_asset_value(asset, rate)
        st.markdown(
            f'<h1 style="text-align:right;"><i class="fa-solid {asset_icon(asset)}" style="color:{asset_color(asset)};"></i> {asset["name"]}</h1>',
            unsafe_allow_html=True)
        st.caption(f"ارز: **{currency_label(asset['currency'])}** | ایجاد: {asset.get('created_at_jalali', '—')}")
        st.caption("💡 برای تغییر آیکون و رنگ، به تب «⚙️ تنظیمات» → «📦 آیکون دارایی‌ها» بروید.")

        avk = f"v_asset_{asset['id']}"
        afk = f"edit_asset_{asset['id']}_v{get_version(avk)}"
        with st.expander("⚙️ ویرایش نام و ارز"):
            with st.form(afk):
                ac1, ac2 = st.columns([3, 2])
                new_name = ac1.text_input("نام", value=asset["name"])
                new_cur = ac2.selectbox("ارز", ["IRR", "USD"],
                                       index=0 if asset["currency"] == "IRR" else 1,
                                       format_func=lambda x: "ریال" if x == "IRR" else "دلار")
                if st.form_submit_button("💾 ذخیره", use_container_width=True):
                    if not new_name.strip():
                        st.error("نام خالی است.")
                    else:
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
        c2.metric("💲 قیمت واحد", f"{fmt_num(rec['unit_price'])} {currency_label(asset['currency'])}" if rec else "—")
        c3.metric("💰 ارزش", f"{fmt_num(value)} {currency_label(asset['currency'])}" if rec else "—")
        c4.metric("💵 دلاری", f"${usd_val:,.2f}" if usd_val is not None else "—")

        with st.container(border=True):
            st.subheader("➕ ثبت رکورد روزانه")
            with st.form(f"add_record_{asset['id']}", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
                dtext = c1.text_input("تاریخ (شمسی)", value=today_jalali_str(), placeholder="1405/08/09")
                qty = c2.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
                price = c3.number_input(f"قیمت ({currency_label(asset['currency'])})", min_value=0.0, format="%.2f", step=1000.0)
                note = c4.text_input("توضیح")
                if st.form_submit_button("💾 ثبت", use_container_width=True):
                    jd = parse_jalali(dtext)
                    if jd is None:
                        st.error("تاریخ نامعتبر.")
                    elif qty <= 0 or price <= 0:
                        st.error("تعداد و قیمت باید > 0 باشند.")
                    else:
                        giso = jalali_to_gregorian_iso(jd, datetime.now().strftime("%H:%M"))
                        asset.setdefault("records", []).append({
                            "id": datetime.now().isoformat(), "date_gregorian": giso,
                            "date_jalali": jd.strftime("%Y/%m/%d"),
                            "quantity": qty, "unit_price": price, "note": note.strip()})
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()

        records = sorted(asset.get("records", []), key=lambda r: r.get("date_gregorian", ""))
        if len(records) >= 2:
            st.subheader("📈 روند ارزش دارایی")
            chart_rows = [{"تاریخ": r["date_jalali"], "ارزش": r["quantity"] * r["unit_price"]} for r in records]
            cdf = pd.DataFrame(chart_rows)
            fig = px.line(cdf, x="تاریخ", y="ارزش", markers=True,
                         labels={"تاریخ": "تاریخ", "ارزش": f"ارزش ({currency_label(asset['currency'])})"})
            fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13), margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 تاریخچه رکوردها")
        if not records:
            st.info("هنوز رکوردی ثبت نشده.")
        else:
            for r in reversed(records):
                with st.container(border=True):
                    c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 3, 3, 2, 1])
                    c1.markdown(f"**📅 {r['date_jalali']}**")
                    c2.caption(f"تعداد: {fmt_num(r['quantity'])}")
                    c3.caption(f"قیمت: {fmt_num(r['unit_price'])} {currency_label(asset['currency'])}")
                    val = r['quantity'] * r['unit_price']
                    c4.markdown(f"**{fmt_num(val)} {currency_label(asset['currency'])}**")
                    c5.caption(r.get("note", "—") or "—")
                    if c6.button("🗑️", key=f"del_rec_{r['id']}", help="حذف"):
                        asset["records"] = [x for x in asset["records"] if x["id"] != r["id"]]
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()
                    rvk = f"v_rec_{r['id']}"
                    rfk = f"edit_rec_{r['id']}_v{get_version(rvk)}"
                    with st.expander("✏️ ویرایش"):
                        with st.form(rfk):
                            ec1, ec2, ec3 = st.columns([2, 2, 2])
                            ed_date = ec1.text_input("تاریخ", value=r["date_jalali"])
                            ed_qty = ec2.number_input("تعداد", value=float(r["quantity"]), min_value=0.0, format="%.4f", step=1.0)
                            ed_price = ec3.number_input(f"قیمت ({currency_label(asset['currency'])})",
                                                        value=float(r["unit_price"]), min_value=0.0, format="%.2f", step=1000.0)
                            ed_note = st.text_input("توضیح", value=r.get("note", ""))
                            if st.form_submit_button("💾 ذخیره", use_container_width=True):
                                jd = parse_jalali(ed_date)
                                if jd is None:
                                    st.error("تاریخ نامعتبر.")
                                elif ed_qty <= 0 or ed_price <= 0:
                                    st.error("مقادیر باید > 0 باشند.")
                                else:
                                    tp = r["date_gregorian"][11:16] if len(r.get("date_gregorian", "")) >= 16 else "00:00"
                                    giso = jalali_to_gregorian_iso(jd, tp)
                                    for i, x in enumerate(asset["records"]):
                                        if x["id"] == r["id"]:
                                            asset["records"][i] = {"id": r["id"], "date_gregorian": giso,
                                                                  "date_jalali": jd.strftime("%Y/%m/%d"),
                                                                  "quantity": ed_qty, "unit_price": ed_price, "note": ed_note.strip()}
                                            break
                                    st.session_state.data = data
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
