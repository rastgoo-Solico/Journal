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
st.set_page_config(
    page_title="داشبورد مالی",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")

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
# نکته کلیدی: ابتدا همه چیز Vazirmatn، سپس آیکون‌های Material را با !important بازمی‌گردانیم
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');

    /* فونت اصلی همه‌جا */
    * { font-family: 'Vazirmatn', 'B Nazanin', Tahoma, sans-serif !important; }

    /* ✅✅✅ بازگرداندن فونت آیکون‌های Material (رفع تداخل keyboard_arrow_down) ✅✅✅ */
    .material-symbols-rounded,
    .material-symbols-outlined,
    .material-symbols-sharp,
    .material-icons,
    .material-icons-round,
    .material-icons-outlined,
    .material-icons-two-tone,
    .material-icons-sharp,
    span[data-testid="stExpanderToggleIcon"],
    span[data-testid="stTooltipIcon"],
    span[data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Rounded', 'Material Icons', 'Segoe UI Symbol', sans-serif !important;
        font-feature-settings: 'liga' !important;
        -webkit-font-feature-settings: 'liga' !important;
    }

    /* RTL */
    .stApp { direction: rtl; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stCaption, .stText { text-align: right !important; }
    input, textarea, select { direction: rtl !important; text-align: right !important; }
    table { direction: rtl !important; }
    table th, table td { text-align: right !important; }

    /* جلوگیری از گم شدن تب‌ها زیر هدر */
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1250px !important;
    }
    header[data-testid="stHeader"] { z-index: 999 !important; }

    /* سایدبار */
    section[data-testid="stSidebar"] { direction: rtl !important; }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label { text-align: right !important; }
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
        font-size: 1.3rem !important; white-space: normal !important;
        overflow: visible !important; word-break: break-word !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] {
        flex-direction: column !important; border: none !important; gap: 0.4rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 0.4rem 0 !important; border-bottom: none !important; border-radius: 0 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
        display: flex !important;
    }

    /* ناوبری بالا */
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] {
        flex-direction: row !important; flex-wrap: wrap !important; gap: 0.25rem !important;
        border-bottom: 1px solid #e5e7eb !important; margin-bottom: 1.5rem !important;
        padding: 0 !important; justify-content: flex-start !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 0.7rem 1.2rem !important; margin: 0 !important; cursor: pointer !important;
        border-bottom: 3px solid transparent !important; border-radius: 0 !important;
        transition: all 0.15s ease !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
        background: #f3f4f6 !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
        border-bottom-color: #3b82f6 !important; color: #1d4ed8 !important; font-weight: 600 !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button { width: 100% !important; }

    /* ✅✅✅ ریسپانسیو موبایل ✅✅✅ */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 4rem !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
            padding-bottom: 2rem !important;
        }
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.15rem !important; }
        h3 { font-size: 1rem !important; }
        h4 { font-size: 0.95rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.05rem !important; }
        [data-testid="stMetricLabel"] { font-size: 0.78rem !important; }

        /* نوار ناوبری: اسکرول افقی */
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] {
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: thin !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] > label {
            padding: 0.55rem 0.75rem !important;
            font-size: 0.82rem !important;
            white-space: nowrap !important;
            flex-shrink: 0 !important;
        }

        /* استک کردن همه ستون‌ها */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            flex: 1 1 100% !important;
            min-width: 100% !important;
            width: 100% !important;
        }

        /* جداول: کوچک‌تر */
        [data-testid="stDataFrame"] { font-size: 0.8rem !important; }

        /* کارت‌های تاریخچه رکورد: بج‌ها کوچک‌تر */
        section[data-testid="stSidebar"] { font-size: 0.9rem; }
    }

    /* ✅ حتی روی موبایل کوچک‌تر */
    @media (max-width: 400px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        h1 { font-size: 1.2rem !important; }
        [data-testid="stMetricValue"] { font-size: 0.95rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ================== GitHub ==================
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"

def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

@st.cache_data(ttl=120, show_spinner=False)
def check_github_status(token, repo):
    """تشخیص دقیق وضعیت اتصال GitHub"""
    if not token and not repo:
        return "no_config", "هیچ‌کدام از GITHUB_TOKEN و GITHUB_REPO تنظیم نشده‌اند."
    if not token:
        return "no_token", "فقط GITHUB_REPO تنظیم شده — GITHUB_TOKEN وجود ندارد."
    if not repo:
        return "no_repo", "فقط GITHUB_TOKEN تنظیم شده — GITHUB_REPO وجود ندارد."
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}",
            headers={"Authorization": f"token {token}",
                     "Accept": "application/vnd.github.v3+json"},
            timeout=8,
        )
        if r.status_code == 200:
            return "ok", f"متصل به {repo}"
        if r.status_code == 401:
            return "error", "توکن نامعتبر یا منقضی است (401)."
        if r.status_code == 404:
            return "error", f"مخزن «{repo}» پیدا نشد یا دسترسی ندارد (404)."
        return "error", f"HTTP {r.status_code}"
    except Exception as e:
        return "error", f"خطای شبکه: {str(e)[:60]}"

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
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(url, headers=github_headers(), timeout=10)
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
    except Exception:
        pass
    return None

def save_github_file(data):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
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

# ================== مهاجرت داده ==================
def migrate_data(data):
    if not isinstance(data, dict) or not data:
        return {"assets": [], "usd_rates": []}

    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list):
        old_rate = data.get("usd_rate")
        data["usd_rates"] = []
        if old_rate:
            data["usd_rates"].append({
                "id": datetime.now().isoformat(),
                "rate": old_rate,
                "note": "منتقل‌شده",
                "created_at": datetime.now().isoformat(),
                "created_at_jalali": today_jalali_str(),
            })
        data.pop("usd_rate", None)

    if "journals" in data and isinstance(data.get("journals"), list):
        if "assets" not in data or not isinstance(data.get("assets"), list):
            data["assets"] = []
        for j in data.get("journals", []):
            asset_id = j.get("id") or datetime.now().isoformat()
            created_iso = j.get("created_at_gregorian") or j.get("created_at") or datetime.now().isoformat()
            created_jalali = j.get("created_at_jalali") or iso_to_jalali(created_iso, with_time=False)
            data["assets"].append({
                "id": asset_id,
                "name": j.get("asset_name", "بدون نام"),
                "icon": "📁",
                "currency": j.get("currency", "IRR"),
                "created_at_gregorian": created_iso,
                "created_at_jalali": created_jalali,
                "records": [{
                    "id": asset_id + "_r",
                    "date_gregorian": created_iso,
                    "date_jalali": created_jalali,
                    "quantity": j.get("amount", 0),
                    "unit_price": 1,
                    "note": "منتقل‌شده",
                }],
            })
        data.pop("journals", None)

    if "assets" not in data or not isinstance(data.get("assets"), list):
        data["assets"] = []
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list):
        data["usd_rates"] = []

    # تضمین وجود icon روی همه دارایی‌ها
    for a in data["assets"]:
        if "icon" not in a or not a["icon"]:
            a["icon"] = "📁"

    return data

def load_all():
    local = load_local_file()
    if local and (local.get("assets") or local.get("journals") or local.get("usd_rates")):
        return migrate_data(local)
    gh = load_github_file()
    if gh:
        return migrate_data(gh)
    return {"assets": [], "usd_rates": []}

def save_all(data):
    local_ok = save_local_file(data)
    gh_ok = save_github_file(data)
    if local_ok and gh_ok:
        st.toast("ذخیره شد (محلی + GitHub)", icon="✅")
    elif local_ok:
        st.toast("ذخیره محلی ✅ (GitHub متصل نیست)", icon="💾")
    elif gh_ok:
        st.toast("ذخیره در GitHub ✅", icon="☁️")
    else:
        st.error("⚠️ ذخیره‌سازی ناموفق بود!")

# ================== توابع کمکی ==================
def get_current_usd_rate(data):
    rates = data.get("usd_rates", [])
    if not rates:
        return None, None
    latest = max(rates, key=lambda x: x.get("created_at", ""))
    return latest["rate"], latest.get("created_at_jalali", "—")

def latest_record(asset):
    records = asset.get("records", [])
    if not records:
        return None
    return max(records, key=lambda r: (r.get("date_gregorian", ""), r.get("id", "")))

def compute_asset_value(asset, usd_rate):
    rec = latest_record(asset)
    if not rec:
        return 0, None, None
    value = rec["quantity"] * rec["unit_price"]
    if asset["currency"] == "IRR":
        usd = (value / usd_rate) if (usd_rate and usd_rate > 0) else None
    else:
        usd = value
    return value, usd, rec

def currency_label(cur):
    return "ریال" if cur == "IRR" else "دلار"

def asset_icon(asset):
    return asset.get("icon") or "📁"

def get_version(key):
    if key not in st.session_state:
        st.session_state[key] = 0
    return st.session_state[key]

def bump_version(key):
    st.session_state[key] = st.session_state.get(key, 0) + 1

# ================== مقداردهی ==================
if "data" not in st.session_state:
    st.session_state.data = load_all()

st.session_state.data = migrate_data(st.session_state.data)
data = st.session_state.data
data.setdefault("assets", [])
data.setdefault("usd_rates", [])

# ================== سایدبار ==================
with st.sidebar:
    st.markdown(f"### 🗓️ امروز: **{today_jalali_str()}**")
    st.caption(f"میلادی: {datetime.now().strftime('%Y-%m-%d')}")
    st.divider()

    rate, rate_date = get_current_usd_rate(data)
    if rate:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            padding: 14px 16px; border-radius: 10px;
            border-right: 4px solid #3b82f6;
            margin-bottom: 12px; direction: rtl; text-align: right;
        ">
            <div style="font-size: 0.82rem; color: #6b7280; margin-bottom: 6px;">💵 نرخ فعلی دلار</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #1e40af; line-height: 1.2;">
                {rate:,.0f}<span style="font-size: 0.95rem; color: #6b7280;"> ریال</span>
            </div>
            <div style="font-size: 0.72rem; color: #9ca3af; margin-top: 6px;">آخرین بروزرسانی: {rate_date}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("💡 هنوز نرخی ثبت نشده. از تب «💵 دلار» ثبت کنید.")

    st.divider()

    # ✅✅✅ وضعیت ذخیره‌سازی با تشخیص دقیق ✅✅✅
    st.markdown("**💾 وضعیت ذخیره‌سازی**")
    local_ok = os.path.exists(DATA_FILE)
    gh_status, gh_message = check_github_status(GITHUB_TOKEN, GITHUB_REPO)

    c_local, c_gh = st.columns(2)
    c_local.caption(f"{'✅' if local_ok else '❌'} محلی")
    c_gh.caption(f"{'✅' if gh_status == 'ok' else '❌'} GitHub")

    if gh_status != "ok":
        st.warning(f"GitHub: {gh_message}", icon="⚠️")
        with st.expander("🔧 چطور GitHub را تنظیم کنم؟", expanded=False):
            st.markdown(""")
