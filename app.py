import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import requests
import base64
from datetime import datetime
import jdatetime

# ================== تنظیمات صفحه ==================
st.set_page_config(page_title="داشبورد مالی", layout="wide", initial_sidebar_state="expanded")

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
APP_PASSWORD = st.secrets.get("APP_PASSWORD") or "S@mnet11970"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"

# ================== آیکون‌ها و فونت‌ها ==================
FA_ICONS = [
    ("fa-folder", "پوشه"), ("fa-coins", "سکه"), ("fa-wallet", "کیف پول"),
    ("fa-money-bill-wave", "پول"), ("fa-dollar-sign", "دلار"), ("fa-euro-sign", "یورو"),
    ("fa-building-columns", "بانک"), ("fa-piggy-bank", "پس‌انداز"), ("fa-vault", "گاوصندوق"),
    ("fa-gem", "الماس"), ("fa-crown", "تاج"), ("fa-house", "خانه"),
    ("fa-building", "ساختمان"), ("fa-warehouse", "انبار"), ("fa-car", "خودرو"),
    ("fa-truck", "کامیون"), ("fa-chart-line", "نمودار خطی"), ("fa-chart-pie", "نمودار دایره"),
    ("fa-arrow-trend-up", "رشد"), ("fa-bitcoin-sign", "بیت‌کوین"), ("fa-ethereum", "اتریوم"),
    ("fa-landmark", "بنای تاریخی"), ("fa-hand-holding-dollar", "سرمایه"), ("fa-industry", "صنعت"),
    ("fa-seedling", "کشت"), ("fa-briefcase", "کیف کار"), ("fa-store", "فروشگاه"),
    ("fa-sack-dollar", "کیسه پول"), ("fa-receipt", "رسید"), ("fa-tag", "برچسب"),
    ("fa-file-invoice-dollar", "فاکتور"), ("fa-percent", "درصد"), ("fa-scale-balanced", "ترازو"),
    ("fa-shield-halved", "سپر"), ("fa-fire", "آتش"), ("fa-droplet", "قطره"),
    ("fa-gas-pump", "بنزین"), ("fa-bolt", "برق"), ("fa-wheat-awn", "گندم"),
    ("fa-folder-open", "پوشه باز"), ("fa-box", "جعبه"), ("fa-cubes", "مکعب‌ها"),
]
FA_TO_EMOJI = {
    "fa-folder": "📁", "fa-coins": "🪙", "fa-wallet": "👛", "fa-money-bill-wave": "💵",
    "fa-dollar-sign": "💲", "fa-euro-sign": "€", "fa-building-columns": "🏦",
    "fa-piggy-bank": "🐷", "fa-vault": "🔐", "fa-gem": "💎", "fa-crown": "👑",
    "fa-house": "🏠", "fa-building": "🏢", "fa-warehouse": "🏭", "fa-car": "🚗",
    "fa-truck": "🚚", "fa-chart-line": "📈", "fa-chart-pie": "📊",
    "fa-arrow-trend-up": "📈", "fa-bitcoin-sign": "₿", "fa-ethereum": "Ξ",
    "fa-landmark": "🏛️", "fa-hand-holding-dollar": "🤲", "fa-industry": "🏭",
    "fa-seedling": "🌱", "fa-briefcase": "💼", "fa-store": "🏪", "fa-sack-dollar": "💰",
    "fa-receipt": "🧾", "fa-tag": "🏷️", "fa-file-invoice-dollar": "🧾",
    "fa-percent": "%", "fa-scale-balanced": "⚖️", "fa-shield-halved": "🛡️",
    "fa-fire": "🔥", "fa-droplet": "💧", "fa-gas-pump": "⛽",
    "fa-bolt": "⚡", "fa-wheat-awn": "🌾", "fa-folder-open": "📂",
    "fa-box": "📦", "fa-cubes": "🧊",
}
EMOJI_TO_FA = {v: k for k, v in FA_TO_EMOJI.items()}
EMOJI_TO_FA.update({"🥇": "fa-coins", "📦": "fa-box", "🪙": "fa-coins"})

FONTS = {
    "vazirmatn": ("Vazirmatn", "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css"),
    "sahel":     ("Sahel",    "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@v3.4.0/dist/font-face.css"),
    "samim":     ("Samim",    "https://cdn.jsdelivr.net/gh/rastikerdar/samim-font@v4.0.5/dist/font-face.css"),
    "shabnam":   ("Shabnam",  "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@v5.0.1/dist/font-face.css"),
    "markazi":   ("Markazi Text", "https://fonts.googleapis.com/css2?family=Markazi+Text:wght@400;700&display=swap"),
    "noto":      ("Noto Naskh Arabic", "https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;700&display=swap"),
}

def normalize_icon(icon):
    if not icon:
        return "fa-folder"
    if isinstance(icon, str) and icon.startswith("fa-"):
        return icon
    return EMOJI_TO_FA.get(icon, "fa-folder")

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

# ================== CSS پایه (فونت پیش‌فرض Vazirmatn) ==================
_font_imports = "\n".join(f"@import url('{url}');" for _, (_, url) in FONTS.items())
st.markdown(f"""
<style>
    {_font_imports}
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

    * {{ font-family: 'Vazirmatn', Tahoma, sans-serif !important; }}
    .fa, .fas, .far, .fal, .fat, .fab, .fad,
    .fa-solid, .fa-regular, .fa-brands {{ font-family: "Font Awesome 6 Free", "Font Awesome 6 Brands" !important; font-feature-settings: normal !important; }}
    .material-symbols-rounded, .material-symbols-outlined, .material-symbols-sharp,
    .material-icons, .material-icons-round, .material-icons-outlined, .material-icons-two-tone, .material-icons-sharp,
    span[data-testid="stExpanderToggleIcon"], span[data-testid="stTooltipIcon"], span[data-testid="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important; font-feature-settings: 'liga' !important;
    }}
    .stApp {{ direction: rtl; }}
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stCaption, .stText {{ text-align: right !important; }}
    input, textarea, select {{ direction: rtl !important; text-align: right !important; }}
    table {{ direction: rtl !important; }} table th, table td {{ text-align: right !important; }}
    .block-container {{ padding-top: 4.5rem !important; padding-bottom: 2.5rem !important; max-width: 1250px !important; }}
    header[data-testid="stHeader"] {{ z-index: 999 !important; }}
    section[data-testid="stSidebar"] {{ direction: rtl !important; }}
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label {{ text-align: right !important; }}
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {{ font-size: 1.3rem !important; white-space: normal !important; overflow: visible !important; word-break: break-word !important; }}
    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button {{ width: 100% !important; }}
    @media (max-width: 768px) {{
        .block-container {{ padding-top: 4rem !important; padding-left: 0.6rem !important; padding-right: 0.6rem !important; padding-bottom: 2rem !important; }}
        h1 {{ font-size: 1.35rem !important; }} h2 {{ font-size: 1.1rem !important; }}
        h3 {{ font-size: 0.98rem !important; }} h4 {{ font-size: 0.92rem !important; }}
        [data-testid="stMetricValue"] {{ font-size: 1.05rem !important; }}
        [data-testid="stMetricLabel"] {{ font-size: 0.78rem !important; }}
        [data-testid="stMetricDelta"] {{ font-size: 0.72rem !important; }}
        [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; }}
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {{ flex: 1 1 100% !important; min-width: 100% !important; width: 100% !important; }}
        [data-testid="stPills"] {{ width: 100% !important; }}
        [data-testid="stDataFrame"] {{ font-size: 0.8rem !important; }}
        [data-testid="stMainBlockContainer"] .stButton > button {{ width: 100% !important; }}
    }}
    @media (max-width: 400px) {{
        .block-container {{ padding-left: 0.4rem !important; padding-right: 0.4rem !important; }}
        h1 {{ font-size: 1.2rem !important; }} [data-testid="stMetricValue"] {{ font-size: 0.95rem !important; }}
    }}
    .asset-icon {{ display: inline-block; width: 1.4em; text-align: center; }}
</style>
""", unsafe_allow_html=True)

# ================== 🔐 صفحه لاگین ==================
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
                        st.rerun()
                    else:
                        st.session_state.login_attempts = st.session_state.get("login_attempts", 0) + 1
                        st.error("❌ رمز عبور اشتباه است.")
                        if st.session_state.login_attempts >= 5:
                            st.warning("⚠️ تعداد تلاش‌های ناموفق زیاد شده. لطفاً صفحه را ببندید و دوباره باز کنید.")
        st.caption("💡 این صفحه از دسترسی افراد ناشناس به داده‌های مالی جلوگیری می‌کند.")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    render_login()
    st.stop()

# ================== GitHub ==================
def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

@st.cache_data(ttl=120, show_spinner=False)
def check_github_status(token, repo):
    if not token and not repo: return "no_config", "هیچ‌کدام از GITHUB_TOKEN و GITHUB_REPO تنظیم نشده‌اند."
    if not token: return "no_token", "فقط GITHUB_REPO تنظیم شده — GITHUB_TOKEN وجود ندارد."
    if not repo: return "no_repo", "فقط GITHUB_TOKEN تنظیم شده — GITHUB_REPO وجود ندارد."
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}",
                         headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}, timeout=8)
        if r.status_code == 200: return "ok", f"متصل به {repo}"
        if r.status_code == 401: return "error", "توکن نامعتبر یا منقضی است (401)."
        if r.status_code == 404: return "error", f"مخزن «{repo}» پیدا نشد (404)."
        return "error", f"HTTP {r.status_code}"
    except Exception as e:
        return "error", f"خطای شبکه: {str(e)[:60]}"

def load_local_file():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: pass
    return None

def save_local_file(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.warning(f"⚠️ ذخیره محلی ناموفق: {e}"); return False

def load_github_file():
    if not GITHUB_TOKEN or not GITHUB_REPO: return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(url, headers=github_headers(), timeout=10)
        if r.status_code == 200: return json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
    except Exception: pass
    return None

def save_github_file(data):
    if not GITHUB_TOKEN or not GITHUB_REPO: return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    sha = None
    try:
        r = requests.get(url, headers=github_headers(), timeout=10)
        if r.status_code == 200: sha = r.json()["sha"]
    except Exception: pass
    payload = {
        "message": f"update {today_jalali_str()} {datetime.now().strftime('%H:%M')}",
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha: payload["sha"] = sha
    try:
        r = requests.put(url, headers=github_headers(), json=payload, timeout=15)
        return r.status_code in (200, 201)
    except Exception: return False

# ================== مهاجرت داده ==================
def migrate_data(data):
    if not isinstance(data, dict) or not data: return {"assets": [], "usd_rates": []}
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list):
        old_rate = data.get("usd_rate"); data["usd_rates"] = []
        if old_rate:
            data["usd_rates"].append({"id": datetime.now().isoformat(), "rate": old_rate, "note": "منتقل‌شده",
                                     "created_at": datetime.now().isoformat(), "created_at_jalali": today_jalali_str()})
        data.pop("usd_rate", None)
    if "journals" in data and isinstance(data.get("journals"), list):
        if "assets" not in data or not isinstance(data.get("assets"), list): data["assets"] = []
        for j in data.get("journals", []):
            asset_id = j.get("id") or datetime.now().isoformat()
            created_iso = j.get("created_at_gregorian") or j.get("created_at") or datetime.now().isoformat()
            created_jalali = j.get("created_at_jalali") or iso_to_jalali(created_iso, with_time=False)
            data["assets"].append({
                "id": asset_id, "name": j.get("asset_name", "بدون نام"), "icon": "fa-folder",
                "currency": j.get("currency", "IRR"), "created_at_gregorian": created_iso, "created_at_jalali": created_jalali,
                "records": [{"id": asset_id + "_r", "date_gregorian": created_iso, "date_jalali": created_jalali,
                             "quantity": j.get("amount", 0), "unit_price": 1, "note": "منتقل‌شده"}],
            })
        data.pop("journals", None)
    if "assets" not in data or not isinstance(data.get("assets"), list): data["assets"] = []
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list): data["usd_rates"] = []
    data.setdefault("settings", {"font": "vazirmatn"})
    for a in data["assets"]:
        a["icon"] = normalize_icon(a.get("icon"))
    return data

def load_all():
    local = load_local_file()
    if local and (local.get("assets") or local.get("journals") or local.get("usd_rates")):
        return migrate_data(local)
    gh = load_github_file()
    if gh: return migrate_data(gh)
    return {"assets": [], "usd_rates": []}

def save_all(data):
    local_ok = save_local_file(data)
    gh_ok = save_github_file(data)
    if local_ok and gh_ok: st.toast("ذخیره شد (محلی + GitHub)", icon="✅")
    elif local_ok: st.toast("ذخیره محلی ✅ (GitHub متصل نیست)", icon="💾")
    elif gh_ok: st.toast("ذخیره در GitHub ✅", icon="☁️")
    else: st.error("⚠️ ذخیره‌سازی ناموفق بود!")

# ================== توابع کمکی ==================
def get_settings(data):
    s = data.get("settings") or {}
    return {"font": s.get("font", "vazirmatn")}

def asset_icon_class(asset):
    return normalize_icon(asset.get("icon"))

def asset_icon_emoji(asset):
    return FA_TO_EMOJI.get(asset_icon_class(asset), "📁")

def asset_icon_html(asset):
    return f'<i class="fa-solid {asset_icon_class(asset)}"></i>'

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
    sorted_dates = sorted(all_dates)
    rows = []
    for d in sorted_dates:
        rate_at_date = None
        for ur in usd_rates:
            if ur.get("created_at", "")[:10] <= d: rate_at_date = ur["rate"]
            else: break
        total_irr = 0.0; total_usd = 0.0
        for a in assets:
            recs = [r for r in a.get("records", []) if r.get("date_gregorian", "")[:10] <= d]
            if not recs: continue
            latest = max(recs, key=lambda r: r.get("date_gregorian", ""))
            val = latest["quantity"] * latest["unit_price"]
            if a["currency"] == "IRR":
                total_irr += val
                if rate_at_date and rate_at_date > 0: total_usd += val / rate_at_date
            else:
                total_usd += val
                if rate_at_date and rate_at_date > 0: total_irr += val * rate_at_date
        try:
            dt = datetime.fromisoformat(d + "T00:00:00")
            jd = jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d")
        except Exception: jd = d
        rows.append({"date_gregorian": d, "date_jalali": jd, "total_irr": total_irr, "total_usd": total_usd})
    return pd.DataFrame(rows)

# ================== مقداردهی داده ==================
if "data" not in st.session_state:
    st.session_state.data = load_all()
st.session_state.data = migrate_data(st.session_state.data)
data = st.session_state.data
data.setdefault("assets", [])
data.setdefault("usd_rates", [])

# ================== اعمال فونت انتخابی کاربر ==================
_settings = get_settings(data)
_font_key = _settings["font"] if _settings["font"] in FONTS else "vazirmatn"
_font_family = FONTS[_font_key][0]
st.markdown(f"""
<style>
    * {{ font-family: '{_font_family}', 'Vazirmatn', Tahoma, sans-serif !important; }}
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
        st.info("💡 هنوز نرخی ثبت نشده. از تب «💵 دلار» ثبت کنید.")

    st.divider()
    st.markdown("**💾 وضعیت ذخیره‌سازی**")
    local_ok = os.path.exists(DATA_FILE)
    gh_status, gh_message = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
    c_local, c_gh = st.columns(2)
    c_local.caption(f"{'✅' if local_ok else '❌'} محلی")
    c_gh.caption(f"{'✅' if gh_status == 'ok' else '❌'} GitHub")
    if gh_status != "ok":
        st.warning(f"GitHub: {gh_message}", icon="⚠️")
        st.caption("برای تنظیم، به تب «⚙️ تنظیمات» بروید.")
    else:
        st.caption(f"✅ {gh_message}")

    st.divider()
    with st.expander("📥 پشتیبان‌گیری / 📤 بازیابی", expanded=False):
        st.download_button("📥 دانلود فایل JSON", data=json.dumps(data, ensure_ascii=False, indent=2),
                          file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                          mime="application/json", use_container_width=True)
        uploaded = st.file_uploader("📤 آپلود فایل پشتیبان", type=["json"], key="uploader")
        if uploaded is not None:
            try:
                imported = json.loads(uploaded.read().decode("utf-8"))
                imported = migrate_data(imported)
                if st.button("✅ اعمال و ذخیره بازیابی", use_container_width=True):
                    st.session_state.data = imported
                    save_all(imported)
                    st.rerun()
            except Exception as e:
                st.error(f"فایل معتبر نیست: {e}")

# ================== ناوبری ==================
nav_options = ["overview", "journal", "usd", "settings"]
for a in data.get("assets", []):
    nav_options.append(f"asset_{a['id']}")

nav_labels = {"overview": "📊 نمای کلی", "journal": "+ افزودن دارایی", "usd": "💵 دلار", "settings": "⚙️ تنظیمات"}
for a in data.get("assets", []):
    nav_labels[f"asset_{a['id']}"] = f"{asset_icon_emoji(a)} {a['name']}"

if "pending_nav" in st.session_state:
    st.session_state.nav_tab = st.session_state.pending_nav
    del st.session_state.pending_nav
if "nav_tab" not in st.session_state or st.session_state.nav_tab not in nav_options:
    st.session_state.nav_tab = "overview"

if hasattr(st, "pills"):
    selected = st.pills("ناوبری", options=nav_options, format_func=lambda x: nav_labels.get(x, x),
                       selection_mode="single", label_visibility="collapsed", key="nav_tab")
    if selected is None: selected = "overview"
else:
    selected = st.radio("ناوبری", options=nav_options, format_func=lambda x: nav_labels.get(x, x),
                       horizontal=True, label_visibility="collapsed", key="nav_tab")

# ================== صفحه تنظیمات ==================
def render_settings_page(data):
    st.header("⚙️ تنظیمات")
    settings = get_settings(data)

    st.subheader("🔤 فونت برنامه")
    font_keys = list(FONTS.keys())
    current_idx = font_keys.index(settings["font"]) if settings["font"] in font_keys else 0
    new_font = st.selectbox("انتخاب فونت", options=font_keys, index=current_idx,
                           format_func=lambda k: FONTS[k][0], key="settings_font_select")
    if st.button("💾 ذخیره فونت", key="save_font_btn", use_container_width=True):
        data.setdefault("settings", {})["font"] = new_font
        st.session_state.data = data
        save_all(data)
        st.rerun()

    st.divider()
    st.subheader("🎨 آیکون دارایی‌ها (Font Awesome)")
    assets = data.get("assets", [])
    if not assets:
        st.info("هنوز دارایی‌ای ثبت نشده.")
    else:
        fa_names = [name for name, _ in FA_ICONS]
        fa_labels = {name: label for name, label in FA_ICONS}

        with st.expander("📖 راهنمای آیکون‌های موجود", expanded=False):
            st.caption(f"مجموعاً {len(FA_ICONS)} آیکون آماده:")
            for i in range(0, len(FA_ICONS), 6):
                cols = st.columns(6)
                for j, (name, label) in enumerate(FA_ICONS[i:i+6]):
                    with cols[j]:
                        st.markdown(
                            f'<div style="text-align:center; padding:8px; border:1px solid #e5e7eb; border-radius:8px;">'
                            f'<i class="fa-solid {name}" style="font-size:1.8rem; color:#3b82f6;"></i>'
                            f'<div style="font-size:0.7rem; margin-top:6px; color:#6b7280;">{label}</div></div>',
                            unsafe_allow_html=True,
                        )

        st.markdown("##### تغییر آیکون هر دارایی")
        for asset in assets:
            current_icon = asset_icon_class(asset)
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 2, 2])
                with c1:
                    st.markdown(f'<div style="text-align:center; padding:12px;">'
                                f'<i class="fa-solid {current_icon}" style="font-size:2.5rem; color:#1e40af;"></i></div>',
                                unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{asset['name']}**")
                    st.caption(f"آیکون فعلی: `{current_icon}`")
                with c3:
                    current_i = fa_names.index(current_icon) if current_icon in fa_names else 0
                    selected_icon = st.selectbox("آیکون جدید", options=fa_names, index=current_i,
                                                format_func=lambda n: f"{fa_labels.get(n, n)} — {n}",
                                                key=f"icon_pick_{asset['id']}", label_visibility="collapsed")
                    if st.button("💾 ذخیره آیکون", key=f"save_icon_{asset['id']}", use_container_width=True):
                        for i, a in enumerate(data["assets"]):
                            if a["id"] == asset["id"]:
                                data["assets"][i]["icon"] = selected_icon
                                break
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()

    st.divider()
    st.subheader("💾 وضعیت اتصال و ذخیره‌سازی")
    local_ok = os.path.exists(DATA_FILE)
    gh_status, gh_msg = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
    gh_ok = gh_status == "ok"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📁 فایل محلی**")
        if local_ok:
            size = os.path.getsize(DATA_FILE)
            st.success(f"✅ فعال — {size:,} بایت")
            st.caption(f"`{DATA_FILE}`")
        else:
            st.error("❌ فایل `data.json` پیدا نشد")
    with c2:
        st.markdown("**☁️ GitHub**")
        if gh_ok:
            st.success(f"✅ {gh_msg}")
        else:
            st.error(f"❌ {gh_msg}")
            with st.expander("🔧 راهنمای تنظیم GitHub"):
                st.markdown("در Streamlit Cloud → Manage app → Settings → Secrets:")
                st.code('GITHUB_TOKEN = "ghp_..."\nGITHUB_REPO = "username/repo"\nAPP_PASSWORD = "..."', language="toml")
                st.caption("مخزن را Private کنید تا data.json محرمانه بماند.")

    st.divider()
    st.subheader("📊 آمار داده‌ها")
    c1, c2, c3 = st.columns(3)
    c1.metric("📁 دارایی‌ها", len(data.get("assets", [])))
    total_records = sum(len(a.get("records", [])) for a in data.get("assets", []))
    c2.metric("📝 رکوردها", total_records)
    c3.metric("💵 نرخ‌های دلار", len(data.get("usd_rates", [])))

# ================== صفحه نمای کلی ==================
if selected == "overview":
    st.header("📊 نمای کلی دارایی‌ها")
    assets = data.get("assets", [])
    rate, _ = get_current_usd_rate(data)

    if not assets:
        st.info("هنوز دارایی‌ای ثبت نشده. از تب «+ افزودن دارایی» اضافه کنید.")
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
            st.info("برای نمایش پای‌چارت، ابتدا نرخ دلار را ثبت کنید.")

        st.subheader("📈 روند رشد ارزش کل دارایی")
        timeline = build_portfolio_timeline(data)
        if len(timeline) >= 2:
            fig_usd = px.line(timeline, x="date_jalali", y="total_usd", markers=True,
                             labels={"date_jalali": "تاریخ", "total_usd": "ارزش (دلار)"},
                             color_discrete_sequence=["#3b82f6"])
            fig_usd.update_traces(hovertemplate="تاریخ: %{x}<br>ارزش: $%{y:,.2f}<extra></extra>",
                                 line=dict(width=3), marker=dict(size=7))
            fig_usd.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13),
                                 yaxis=dict(tickformat=",.0f", title="ارزش (دلار)"), xaxis=dict(title="تاریخ"),
                                 margin=dict(t=30, b=20, l=10, r=10), hovermode="x unified",
                                 title=dict(text="💵 ارزش کل دارایی به دلار", font=dict(size=14)))
            st.plotly_chart(fig_usd, use_container_width=True)

            fig_irr = px.line(timeline, x="date_jalali", y="total_irr", markers=True,
                             labels={"date_jalali": "تاریخ", "total_irr": "ارزش (ریال)"},
                             color_discrete_sequence=["#10b981"])
            fig_irr.update_traces(hovertemplate="تاریخ: %{x}<br>ارزش: %{y:,.0f} ریال<extra></extra>",
                                 line=dict(width=3), marker=dict(size=7))
            fig_irr.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13),
                                 yaxis=dict(tickformat=",.0f", title="ارزش (ریال)"), xaxis=dict(title="تاریخ"),
                                 margin=dict(t=30, b=20, l=10, r=10), hovermode="x unified",
                                 title=dict(text="🇮🇷 ارزش کل دارایی به ریال", font=dict(size=14)))
            st.plotly_chart(fig_irr, use_container_width=True)

            first_usd = timeline["total_usd"].iloc[0]; last_usd = timeline["total_usd"].iloc[-1]
            first_irr = timeline["total_irr"].iloc[0]; last_irr = timeline["total_irr"].iloc[-1]
            d_usd = last_usd - first_usd; d_irr = last_irr - first_irr
            pct_usd = ((last_usd / first_usd - 1) * 100) if first_usd else 0
            pct_irr = ((last_irr / first_irr - 1) * 100) if first_irr else 0
            g1, g2 = st.columns(2)
            g1.metric("تغییر ارزش (دلاری)", f"${last_usd:,.2f}", delta=f"{d_usd:+,.2f} ({pct_usd:+.1f}%)")
            g2.metric("تغییر ارزش (ریالی)", f"{last_irr:,.0f} ریال", delta=f"{d_irr:+,.0f} ({pct_irr:+.1f}%)")
        elif len(timeline) == 1:
            st.info("📊 برای نمایش نمودار روند، حداقل دو رکورد در تاریخ‌های مختلف لازم است.")
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
    with st.container(border=True):
        st.subheader("➕ ثبت دارایی جدید")
        with st.form("add_asset_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 3, 2])
            name = c1.text_input("نام دارایی", placeholder="طلا، سهام، بیت‌کوین...")
            cur = c2.selectbox("ارز ثبت قیمت", ["IRR", "USD"], format_func=lambda x: "ریال" if x == "IRR" else "دلار")
            icon_choice = c3.selectbox("آیکون", options=[n for n, _ in FA_ICONS], index=0,
                                       format_func=lambda n: f"{dict(FA_ICONS).get(n, n)} — {n}",
                                       key="new_asset_icon")
            st.markdown("**📝 رکورد اولیه (اختیاری)**")
            c4, c5, c6 = st.columns([2, 2, 3])
            q0 = c4.number_input("تعداد اولیه", min_value=0.0, format="%.4f", step=1.0)
            p0 = c5.number_input("قیمت واحد اولیه", min_value=0.0, format="%.2f", step=1000.0)
            note0 = c6.text_input("توضیح", placeholder="اختیاری")
            if st.form_submit_button("💾 ایجاد دارایی", use_container_width=True):
                if not name.strip():
                    st.error("نام دارایی را وارد کنید.")
                else:
                    asset_id = datetime.now().isoformat()
                    records = []
                    if q0 > 0 and p0 > 0:
                        records.append({"id": asset_id + "_r0", "date_gregorian": asset_id,
                                       "date_jalali": today_jalali_str(), "quantity": q0, "unit_price": p0,
                                       "note": note0.strip() or "رکورد اولیه"})
                    data.setdefault("assets", []).append({
                        "id": asset_id, "name": name.strip(), "icon": icon_choice, "currency": cur,
                        "created_at_gregorian": asset_id, "created_at_jalali": today_jalali_str(),
                        "records": records,
                    })
                    st.session_state.data = data
                    save_all(data)
                    st.session_state.pending_nav = f"asset_{asset_id}"
                    st.rerun()

    assets = data.get("assets", [])
    if not assets:
        st.info("هنوز دارایی‌ای ثبت نشده.")
    else:
        st.subheader("📝 لیست دارایی‌ها")
        rate, _ = get_current_usd_rate(data)
        for a in assets:
            value, usd_val, rec = compute_asset_value(a, rate)
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 3, 2, 1])
                c1.markdown(f'**<i class="fa-solid {asset_icon_class(a)}" style="color:#3b82f6;"></i> {a["name"]}**',
                            unsafe_allow_html=True)
                c2.caption(currency_label(a["currency"]))
                c3.caption(f"آخرین رکورد: {rec['date_jalali'] if rec else '—'}")
                c4.write(f"{fmt_num(value)} {currency_label(a['currency'])}" if value else "—")
                if c5.button("🗑️", key=f"del_asset_{a['id']}", help="حذف دارایی"):
                    data["assets"] = [x for x in data["assets"] if x["id"] != a["id"]]
                    st.session_state.data = data
                    save_all(data)
                    st.session_state.pending_nav = "overview"
                    st.rerun()

# ================== صفحه دلار ==================
elif selected == "usd":
    st.header("💵 نرخ دلار به ریال")
    st.caption(f"📅 امروز — شمسی: **{today_jalali_str()}** | میلادی: {datetime.now().strftime('%Y-%m-%d')}")
    with st.container(border=True):
        st.subheader("➕ ثبت نرخ جدید")
        with st.form("usd_rate_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 3])
            new_rate = c1.number_input("نرخ دلار (ریال)", min_value=0, step=1000, format="%d")
            note = c2.text_input("توضیح (اختیاری)", placeholder="بازار آزاد")
            if st.form_submit_button("💾 ثبت نرخ", use_container_width=True):
                if new_rate > 0:
                    now = datetime.now().isoformat()
                    data.setdefault("usd_rates", []).append({
                        "id": now, "rate": new_rate, "note": note.strip(),
                        "created_at": now, "created_at_jalali": today_jalali_str(),
                    })
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
        c2.metric("تعداد ثبت‌ها", len(rates))
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
                vkey = f"v_rate_{r['id']}"
                fk = f"edit_rate_{r['id']}_v{get_version(vkey)}"
                with st.expander("✏️ ویرایش این نرخ"):
                    with st.form(fk):
                        ec1, ec2 = st.columns([2, 3])
                        er_date = ec1.text_input("تاریخ (شمسی)", value=r.get("created_at_jalali", today_jalali_str()))
                        er_rate = ec2.number_input("نرخ (ریال)", value=int(r["rate"]), min_value=1, step=1000, format="%d")
                        er_note = st.text_input("توضیح", value=r.get("note", ""))
                        if st.form_submit_button("💾 ذخیره تغییرات", use_container_width=True):
                            jdate = parse_jalali(er_date)
                            if jdate is None:
                                st.error("تاریخ نامعتبر است.")
                            elif er_rate <= 0:
                                st.error("نرخ باید بزرگتر از صفر باشد.")
                            else:
                                time_part = r["created_at"][11:16] if len(r.get("created_at", "")) >= 16 else "00:00"
                                giso = jalali_to_gregorian_iso(jdate, time_part)
                                for i, x in enumerate(data["usd_rates"]):
                                    if x["id"] == r["id"]:
                                        data["usd_rates"][i] = {"id": r["id"], "rate": er_rate, "note": er_note.strip(),
                                                               "created_at": giso, "created_at_jalali": jdate.strftime("%Y/%m/%d")}
                                        break
                                st.session_state.data = data
                                bump_version(vkey)
                                save_all(data)
                                st.rerun()

# ================== صفحه تنظیمات ==================
elif selected == "settings":
    render_settings_page(data)

# ================== صفحه دارایی اختصاصی ==================
elif selected.startswith("asset_"):
    asset_id = selected.replace("asset_", "")
    asset = next((a for a in data.get("assets", []) if a["id"] == asset_id), None)
    if asset is None:
        st.error("دارایی یافت نشد.")
    else:
        rate, _ = get_current_usd_rate(data)
        value, usd_val, rec = compute_asset_value(asset, rate)
        st.markdown(f'<h1 style="text-align:right;"><i class="fa-solid {asset_icon_class(asset)}" style="color:#3b82f6;"></i> {asset["name"]}</h1>',
                    unsafe_allow_html=True)
        st.caption(f"ارز: **{currency_label(asset['currency'])}** | تاریخ ایجاد: {asset.get('created_at_jalali', '—')}")

        avkey = f"v_asset_{asset['id']}"
        afk = f"edit_asset_{asset['id']}_v{get_version(avkey)}"
        with st.expander("⚙️ تنظیمات دارایی (نام و ارز)"):
            with st.form(afk):
                ac1, ac2 = st.columns([3, 2])
                new_name = ac1.text_input("نام دارایی", value=asset["name"])
                new_cur = ac2.selectbox("ارز قیمت‌گذاری", ["IRR", "USD"],
                                       index=0 if asset["currency"] == "IRR" else 1,
                                       format_func=lambda x: "ریال" if x == "IRR" else "دلار")
                st.caption("⚠️ تغییر ارز باعث تفسیر مجدد رکوردها می‌شود. آیکون از تب تنظیمات قابل تغییر است.")
                if st.form_submit_button("💾 ذخیره تنظیمات", use_container_width=True):
                    if not new_name.strip():
                        st.error("نام دارایی را وارد کنید.")
                    else:
                        for i, a in enumerate(data["assets"]):
                            if a["id"] == asset["id"]:
                                data["assets"][i]["name"] = new_name.strip()
                                data["assets"][i]["currency"] = new_cur
                                break
                        st.session_state.data = data
                        bump_version(avkey)
                        save_all(data)
                        st.rerun()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 آخرین تعداد", fmt_num(rec["quantity"]) if rec else "—")
        c2.metric("💲 آخرین قیمت واحد", f"{fmt_num(rec['unit_price'])} {currency_label(asset['currency'])}" if rec else "—")
        c3.metric("💰 ارزش فعلی", f"{fmt_num(value)} {currency_label(asset['currency'])}" if rec else "—")
        if usd_val is not None:
            c4.metric("💵 معادل دلاری", f"${usd_val:,.2f}")
        else:
            c4.metric("💵 معادل دلاری", "—")

        with st.container(border=True):
            st.subheader("➕ ثبت رکورد روزانه")
            st.caption("قیمت و تعداد هر روز را اینجا ثبت کنید. تاریخ شمسی (YYYY/MM/DD).")
            with st.form(f"add_record_{asset['id']}", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
                date_text = c1.text_input("تاریخ (شمسی)", value=today_jalali_str(), placeholder="1405/08/09")
                qty = c2.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
                price = c3.number_input(f"قیمت واحد ({currency_label(asset['currency'])})", min_value=0.0, format="%.2f", step=1000.0)
                note = c4.text_input("توضیح (اختیاری)")
                if st.form_submit_button("💾 ثبت رکورد", use_container_width=True):
                    jdate = parse_jalali(date_text)
                    if jdate is None:
                        st.error("تاریخ معتبر نیست. مثال: 1405/08/09")
                    elif qty <= 0:
                        st.error("تعداد باید بزرگتر از صفر باشد.")
                    elif price <= 0:
                        st.error("قیمت واحد باید بزرگتر از صفر باشد.")
                    else:
                        giso = jalali_to_gregorian_iso(jdate, datetime.now().strftime("%H:%M"))
                        asset.setdefault("records", []).append({
                            "id": datetime.now().isoformat(), "date_gregorian": giso,
                            "date_jalali": jdate.strftime("%Y/%m/%d"),
                            "quantity": qty, "unit_price": price, "note": note.strip(),
                        })
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
                    if c6.button("🗑️", key=f"del_rec_{r['id']}", help="حذف رکورد"):
                        asset["records"] = [x for x in asset["records"] if x["id"] != r["id"]]
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()
                    rvkey = f"v_rec_{r['id']}"
                    rfk = f"edit_rec_{r['id']}_v{get_version(rvkey)}"
                    with st.expander("✏️ ویرایش این رکورد"):
                        with st.form(rfk):
                            ec1, ec2, ec3 = st.columns([2, 2, 2])
                            ed_date = ec1.text_input("تاریخ (شمسی)", value=r["date_jalali"])
                            ed_qty = ec2.number_input("تعداد", value=float(r["quantity"]), min_value=0.0, format="%.4f", step=1.0)
                            ed_price = ec3.number_input(f"قیمت واحد ({currency_label(asset['currency'])})",
                                                        value=float(r["unit_price"]), min_value=0.0, format="%.2f", step=1000.0)
                            ed_note = st.text_input("توضیح", value=r.get("note", ""))
                            if st.form_submit_button("💾 ذخیره تغییرات", use_container_width=True):
                                jdate = parse_jalali(ed_date)
                                if jdate is None:
                                    st.error("تاریخ نامعتبر است.")
                                elif ed_qty <= 0:
                                    st.error("تعداد باید بزرگتر از صفر باشد.")
                                elif ed_price <= 0:
                                    st.error("قیمت واحد باید بزرگتر از صفر باشد.")
                                else:
                                    time_part = r["date_gregorian"][11:16] if len(r.get("date_gregorian", "")) >= 16 else "00:00"
                                    giso = jalali_to_gregorian_iso(jdate, time_part)
                                    for i, x in enumerate(asset["records"]):
                                        if x["id"] == r["id"]:
                                            asset["records"][i] = {"id": r["id"], "date_gregorian": giso,
                                                                  "date_jalali": jdate.strftime("%Y/%m/%d"),
                                                                  "quantity": ed_qty, "unit_price": ed_price, "note": ed_note.strip()}
                                            break
                                    st.session_state.data = data
                                    bump_version(rvkey)
                                    save_all(data)
                                    st.rerun()

        st.divider()
        with st.expander("⚠️ حذف کل دارایی"):
            confirm = st.checkbox("مطمئنم", key=f"confirm_del_asset_{asset['id']}")
            if st.button("🗑️ حذف دارایی", disabled=not confirm, key=f"del_asset_btn_{asset['id']}"):
                data["assets"] = [x for x in data["assets"] if x["id"] != asset["id"]]
                st.session_state.data = data
                save_all(data)
                st.session_state.pending_nav = "overview"
                st.rerun()
