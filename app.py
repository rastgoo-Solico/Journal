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
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
    * { font-family: 'Vazirmatn', 'B Nazanin', Tahoma, sans-serif !important; }
    .stApp { direction: rtl; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stCaption, .stText { text-align: right !important; }
    input, textarea, select { direction: rtl !important; text-align: right !important; }
    table { direction: rtl !important; }
    table th, table td { text-align: right !important; }
    .block-container { padding-top: 4.5rem !important; padding-bottom: 2.5rem !important; max-width: 1250px !important; }
    header[data-testid="stHeader"] { z-index: 999 !important; }
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
    if not isinstance(data, dict):
        return {"assets": [], "usd_rates": []}
    if not data:
        return {"assets": [], "usd_rates": []}
    
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list):
        old_rate = data.get("usd_rate")
        data["usd_rates"] = []
        if old_rate:
            data["usd_rates"].append({
                "id": datetime.now().isoformat(),
                "rate": old_rate,
                "note": "منتقل‌شده از نسخه قدیمی",
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
            amount = j.get("amount", 0)
            data["assets"].append({
                "id": asset_id,
                "name": j.get("asset_name", "بدون نام"),
                "currency": j.get("currency", "IRR"),
                "created_at_gregorian": created_iso,
                "created_at_jalali": created_jalali,
                "records": [{
                    "id": asset_id + "_r",
                    "date_gregorian": created_iso,
                    "date_jalali": created_jalali,
                    "quantity": amount,
                    "unit_price": 1,
                    "note": "منتقل‌شده از نسخه قبلی",
                }],
            })
        data.pop("journals", None)
    
    if "assets" not in data or not isinstance(data.get("assets"), list):
        data["assets"] = []
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list):
        data["usd_rates"] = []
    
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
        st.toast("ذخیره در فایل محلی ✅", icon="💾")
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
    st.markdown("**💾 وضعیت ذخیره‌سازی**")
    local_ok = os.path.exists(DATA_FILE)
    gh_ok = bool(GITHUB_TOKEN and GITHUB_REPO)
    st.caption(f"{'✅' if local_ok else '❌'} فایل محلی `data.json`  \n{'✅' if gh_ok else '❌'} GitHub")
    st.divider()
    
    with st.expander("📥 پشتیبان‌گیری / 📤 بازیابی", expanded=False):
        st.download_button(
            "📥 دانلود فایل JSON",
            data=json.dumps(data, ensure_ascii=False, indent=2),
            file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )
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

# ================== نوار ناوبری ==================
nav_options = ["overview", "journal", "usd"]
for a in data.get("assets", []):
    nav_options.append(f"asset_{a['id']}")

nav_labels = {
    "overview": "📊 نمای کلی",
    "journal": "📒 دارایی‌ها",
    "usd": "💵 دلار",
}
for a in data.get("assets", []):
    nav_labels[f"asset_{a['id']}"] = f"📁 {a['name']}"

if "pending_nav" in st.session_state:
    st.session_state.nav_tab = st.session_state.pending_nav
    del st.session_state.pending_nav

if "nav_tab" not in st.session_state or st.session_state.nav_tab not in nav_options:
    st.session_state.nav_tab = "overview"

selected = st.radio(
    "ناوبری",
    options=nav_options,
    format_func=lambda x: nav_labels.get(x, x),
    horizontal=True,
    label_visibility="collapsed",
    key="nav_tab",
)

# ================== صفحه ۱: نمای کلی ==================
if selected == "overview":
    st.header("📊 نمای کلی دارایی‌ها")
    assets = data.get("assets", [])
    rate, _ = get_current_usd_rate(data)
    
    if not assets:
        st.info("هنوز دارایی‌ای ثبت نشده. از تب «📒 دارایی‌ها» اضافه کنید.")
    else:
        rows = []
        total_usd = 0.0
        for a in assets:
            value, usd_val, rec = compute_asset_value(a, rate)
            if usd_val is not None:
                total_usd += usd_val
            rows.append({
                "دارایی": a["name"],
                "ارز": currency_label(a["currency"]),
                "تعداد": rec["quantity"] if rec else 0,
                "قیمت واحد": rec["unit_price"] if rec else 0,
                "ارزش": value,
                "معادل_دلاری": usd_val,
                "آخرین_تاریخ": rec["date_jalali"] if rec else "—",
            })
        df = pd.DataFrame(rows)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 کل ارزش (دلاری)", f"${total_usd:,.2f}")
        c2.metric("📁 تعداد دارایی‌ها", len(assets))
        c3.metric("💵 نرخ دلار", f"{rate:,.0f} ریال" if rate else "ثبت نشده")
        
        st.subheader("🥧 ترکیب دارایی‌ها")
        pie_df = df.dropna(subset=["معادل_دلاری"])
        pie_df = pie_df[pie_df["معادل_دلاری"] > 0]
        if not pie_df.empty:
            fig = px.pie(
                pie_df, values="معادل_دلاری", names="دارایی", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(
                font=dict(family="Vazirmatn, B Nazanin, Tahoma", size=14),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                margin=dict(t=20, b=20, l=10, r=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("برای نمایش پای‌چارت، ابتدا نرخ دلار را ثبت کنید.")
        
        st.subheader("📋 جدول دارایی‌ها")
        disp = df.copy()
        disp["تعداد"] = disp["تعداد"].apply(fmt_num)
        disp["قیمت واحد"] = disp.apply(
            lambda r: f"{fmt_num(r['قیمت واحد'])} {r['ارز']}" if r['قیمت واحد'] else "—", axis=1)
        disp["ارزش"] = disp.apply(
            lambda r: f"{fmt_num(r['ارزش'])} {r['ارز']}" if r['ارزش'] else "—", axis=1)
        disp["معادل_دلاری"] = disp["معادل_دلاری"].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
        disp = disp[["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل_دلاری", "آخرین_تاریخ"]]
        disp.columns = ["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل دلاری", "آخرین بروزرسانی"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

# ================== صفحه ۲: مدیریت دارایی‌ها ==================
elif selected == "journal":
    st.header("📒 مدیریت دارایی‌ها")
    
    with st.container(border=True):
        st.subheader("➕ ثبت دارایی جدید")
        with st.form("add_asset_form", clear_on_submit=True):
            c1, c2 = st.columns([3, 2])
            name = c1.text_input("نام دارایی", placeholder="مثلاً: طلا، سهام، بیت‌کوین")
            cur = c2.selectbox("ارز ثبت قیمت", ["IRR", "USD"],
                               format_func=lambda x: "ریال" if x == "IRR" else "دلار")
            
            st.markdown("**📝 رکورد اولیه (اختیاری)**")
            c3, c4, c5 = st.columns([2, 2, 3])
            q0 = c3.number_input("تعداد اولیه", min_value=0.0, format="%.4f", step=1.0)
            p0 = c4.number_input("قیمت واحد اولیه", min_value=0.0, format="%.2f", step=1000.0)
            note0 = c5.text_input("توضیح", placeholder="اختیاری")
            
            if st.form_submit_button("💾 ایجاد دارایی", use_container_width=True):
                if not name.strip():
                    st.error("نام دارایی را وارد کنید.")
                else:
                    asset_id = datetime.now().isoformat()
                    records = []
                    if q0 > 0 and p0 > 0:
                        records.append({
                            "id": asset_id + "_r0",
                            "date_gregorian": asset_id,
                            "date_jalali": today_jalali_str(),
                            "quantity": q0,
                            "unit_price": p0,
                            "note": note0.strip() or "رکورد اولیه",
                        })
                    data.setdefault("assets", []).append({
                        "id": asset_id,
                        "name": name.strip(),
                        "currency": cur,
                        "created_at_gregorian": asset_id,
                        "created_at_jalali": today_jalali_str(),
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
                c1.markdown(f"**📁 {a['name']}**")
                c2.caption(currency_label(a["currency"]))
                c3.caption(f"آخرین رکورد: {rec['date_jalali'] if rec else '—'}")
                c4.write(f"{fmt_num(value)} {currency_label(a['currency'])}" if value else "—")
                if c5.button("🗑️", key=f"del_asset_{a['id']}", help="حذف دارایی"):
                    data["assets"] = [x for x in data["assets"] if x["id"] != a["id"]]
                    st.session_state.data = data
                    save_all(data)
                    st.session_state.pending_nav = "overview"
                    st.rerun()

# ================== صفحه ۳: دلار ==================
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
        fig.update_layout(font=dict(family="Vazirmatn, B Nazanin, Tahoma", size=13),
                         margin=dict(t=20, b=20))
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
                
                # ✅ ویرایش نرخ دلار
                vkey = f"v_rate_{r['id']}"
                fk = f"edit_rate_{r['id']}_v{get_version(vkey)}"
                with st.expander("✏️ ویرایش این نرخ"):
                    with st.form(fk):
                        ec1, ec2 = st.columns([2, 3])
                        er_date = ec1.text_input(
                            "تاریخ (شمسی)",
                            value=r.get("created_at_jalali", today_jalali_str()),
                        )
                        er_rate = ec2.number_input(
                            "نرخ (ریال)",
                            value=int(r["rate"]),
                            min_value=1,
                            step=1000,
                            format="%d",
                        )
                        er_note = st.text_input("توضیح", value=r.get("note", ""))
                        if st.form_submit_button("💾 ذخیره تغییرات", use_container_width=True):
                            jdate = parse_jalali(er_date)
                            if jdate is None:
                                st.error("تاریخ شمسی نامعتبر است. مثال: 1405/08/09")
                            elif er_rate <= 0:
                                st.error("نرخ باید بزرگتر از صفر باشد.")
                            else:
                                time_part = (
                                    r["created_at"][11:16]
                                    if len(r.get("created_at", "")) >= 16 else "00:00"
                                )
                                giso = jalali_to_gregorian_iso(jdate, time_part)
                                for i, x in enumerate(data["usd_rates"]):
                                    if x["id"] == r["id"]:
                                        data["usd_rates"][i] = {
                                            "id": r["id"],
                                            "rate": er_rate,
                                            "note": er_note.strip(),
                                            "created_at": giso,
                                            "created_at_jalali": jdate.strftime("%Y/%m/%d"),
                                        }
                                        break
                                st.session_state.data = data
                                bump_version(vkey)
                                save_all(data)
                                st.rerun()

# ================== صفحه ۴: هر دارایی اختصاصی ==================
elif selected.startswith("asset_"):
    asset_id = selected.replace("asset_", "")
    asset = next((a for a in data.get("assets", []) if a["id"] == asset_id), None)
    if asset is None:
        st.error("دارایی یافت نشد.")
    else:
        rate, _ = get_current_usd_rate(data)
        value, usd_val, rec = compute_asset_value(asset, rate)
        
        st.header(f"📁 {asset['name']}")
        st.caption(
            f"ارز: **{currency_label(asset['currency'])}** | "
            f"تاریخ ایجاد: {asset.get('created_at_jalali', '—')}"
        )
        
        # ✅ تنظیمات دارایی (ویرایش نام و ارز)
        avkey = f"v_asset_{asset['id']}"
        afk = f"edit_asset_{asset['id']}_v{get_version(avkey)}"
        with st.expander("⚙️ تنظیمات دارایی (ویرایش نام و ارز)"):
            with st.form(afk):
                ac1, ac2 = st.columns([3, 2])
                new_name = ac1.text_input("نام دارایی", value=asset["name"])
                new_cur = ac2.selectbox(
                    "ارز قیمت‌گذاری",
                    ["IRR", "USD"],
                    index=0 if asset["currency"] == "IRR" else 1,
                    format_func=lambda x: "ریال" if x == "IRR" else "دلار",
                )
                st.caption("⚠️ تغییر ارز باعث می‌شود رکوردهای قبلی با ارز جدید تفسیر شوند.")
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
        c2.metric("💲 آخرین قیمت واحد",
                  f"{fmt_num(rec['unit_price'])} {currency_label(asset['currency'])}" if rec else "—")
        c3.metric("💰 ارزش فعلی",
                  f"{fmt_num(value)} {currency_label(asset['currency'])}" if rec else "—")
        if usd_val is not None:
            c4.metric("💵 معادل دلاری", f"${usd_val:,.2f}")
        else:
            c4.metric("💵 معادل دلاری", "—", help="نرخ دلار ثبت نشده")
        
        # --- فرم ثبت رکورد روزانه ---
        with st.container(border=True):
            st.subheader("➕ ثبت رکورد روزانه")
            st.caption("قیمت و تعداد هر روز را اینجا ثبت کنید. تاریخ شمسی (YYYY/MM/DD).")
            with st.form(f"add_record_{asset['id']}", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
                date_text = c1.text_input("تاریخ (شمسی)", value=today_jalali_str(),
                                          placeholder="1405/08/09")
                qty = c2.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
                price = c3.number_input(
                    f"قیمت واحد ({currency_label(asset['currency'])})",
                    min_value=0.0, format="%.2f", step=1000.0)
                note = c4.text_input("توضیح (اختیاری)")
                
                if st.form_submit_button("💾 ثبت رکورد", use_container_width=True):
                    jdate = parse_jalali(date_text)
                    if jdate is None:
                        st.error("تاریخ شمسی معتبر نیست. مثال: 1405/08/09")
                    elif qty <= 0:
                        st.error("تعداد باید بزرگتر از صفر باشد.")
                    elif price <= 0:
                        st.error("قیمت واحد باید بزرگتر از صفر باشد.")
                    else:
                        giso = jalali_to_gregorian_iso(jdate, datetime.now().strftime("%H:%M"))
                        asset.setdefault("records", []).append({
                            "id": datetime.now().isoformat(),
                            "date_gregorian": giso,
                            "date_jalali": jdate.strftime("%Y/%m/%d"),
                            "quantity": qty,
                            "unit_price": price,
                            "note": note.strip(),
                        })
                        st.session_state.data = data
                        save_all(data)
                        st.rerun()
        
        # --- نمودار روند ---
        records = sorted(asset.get("records", []), key=lambda r: r.get("date_gregorian", ""))
        if len(records) >= 2:
            st.subheader("📈 روند ارزش دارایی")
            chart_rows = [{
                "تاریخ": r["date_jalali"],
                "ارزش": r["quantity"] * r["unit_price"],
            } for r in records]
            cdf = pd.DataFrame(chart_rows)
            fig = px.line(cdf, x="تاریخ", y="ارزش", markers=True,
                         labels={"تاریخ": "تاریخ",
                                 "ارزش": f"ارزش ({currency_label(asset['currency'])})"})
            fig.update_layout(font=dict(family="Vazirmatn, B Nazanin, Tahoma", size=13),
                             margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        
        # --- تاریخچه رکوردها با ویرایش ---
        st.subheader("📋 تاریخچه رکوردها")
        if not records:
            st.info("هنوز رکوردی ثبت نشده. اولین رکورد را از فرم بالا اضافه کنید.")
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
                    
                    # ✅ ویرایش رکورد
                    rvkey = f"v_rec_{r['id']}"
                    rfk = f"edit_rec_{r['id']}_v{get_version(rvkey)}"
                    with st.expander("✏️ ویرایش این رکورد"):
                        with st.form(rfk):
                            ec1, ec2, ec3 = st.columns([2, 2, 2])
                            ed_date = ec1.text_input("تاریخ (شمسی)", value=r["date_jalali"])
                            ed_qty = ec2.number_input(
                                "تعداد", value=float(r["quantity"]),
                                min_value=0.0, format="%.4f", step=1.0,
                            )
                            ed_price = ec3.number_input(
                                f"قیمت واحد ({currency_label(asset['currency'])})",
                                value=float(r["unit_price"]),
                                min_value=0.0, format="%.2f", step=1000.0,
                            )
                            ed_note = st.text_input("توضیح", value=r.get("note", ""))
                            if st.form_submit_button("💾 ذخیره تغییرات", use_container_width=True):
                                jdate = parse_jalali(ed_date)
                                if jdate is None:
                                    st.error("تاریخ شمسی نامعتبر است. مثال: 1405/08/09")
                                elif ed_qty <= 0:
                                    st.error("تعداد باید بزرگتر از صفر باشد.")
                                elif ed_price <= 0:
                                    st.error("قیمت واحد باید بزرگتر از صفر باشد.")
                                else:
                                    time_part = (
                                        r["date_gregorian"][11:16]
                                        if len(r.get("date_gregorian", "")) >= 16 else "00:00"
                                    )
                                    giso = jalali_to_gregorian_iso(jdate, time_part)
                                    for i, x in enumerate(asset["records"]):
                                        if x["id"] == r["id"]:
                                            asset["records"][i] = {
                                                "id": r["id"],
                                                "date_gregorian": giso,
                                                "date_jalali": jdate.strftime("%Y/%m/%d"),
                                                "quantity": ed_qty,
                                                "unit_price": ed_price,
                                                "note": ed_note.strip(),
                                            }
                                            break
                                    st.session_state.data = data
                                    bump_version(rvkey)
                                    save_all(data)
                                    st.rerun()
        
        # --- حذف کل دارایی ---
        st.divider()
        with st.expander("⚠️ حذف کل دارایی"):
            confirm = st.checkbox(
                "از حذف کل دارایی و تمام رکوردهای آن مطمئن هستم",
                key=f"confirm_del_asset_{asset['id']}"
            )
            if st.button("🗑️ حذف دارایی", disabled=not confirm,
                        key=f"del_asset_btn_{asset['id']}"):
                data["assets"] = [x for x in data["assets"] if x["id"] != asset["id"]]
                st.session_state.data = data
                save_all(data)
                st.session_state.pending_nav = "overview"
                st.rerun()
