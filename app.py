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

# ================== مسیر فایل ذخیره‌سازی محلی ==================
# این فایل در کنار app.py ذخیره می‌شود و داده‌ها را بین اجراها نگه می‌دارد
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

# ================== CSS: راست‌چین + فونت + رفع مشکلات سایدبار ==================
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');

    /* فقط فونت */
    * { font-family: 'Vazirmatn', 'B Nazanin', Tahoma, sans-serif !important; }

    /* RTL پایه روی کل اپ */
    .stApp { direction: rtl; }

    /* تراز راست متن‌ها */
    h1, h2, h3, h4, h5, h6, p, label,
    .stMarkdown, .stCaption, .stText { text-align: right !important; }

    /* ورودی‌ها */
    input, textarea, select { direction: rtl !important; text-align: right !important; }

    /* جدول */
    table { direction: rtl !important; }
    table th, table td { text-align: right !important; }

    /* ✅ رفع مشکل هدر: تب‌ها زیر هدر ثابت گم نشوند */
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1250px !important;
    }
    header[data-testid="stHeader"] { z-index: 999 !important; }

    /* ✅ سایدبار: RTL بدون به‌هم‌ریختن چیدمان */
    section[data-testid="stSidebar"] { direction: rtl !important; }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label { text-align: right !important; }

    /* جلوگیری از سرریز مقادیر طولانی در سایدبار */
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
        white-space: normal !important;
        overflow: visible !important;
        word-break: break-word !important;
    }

    /* ✅ رادیو در سایدبار: به شکل پیش‌فرض (عمودی) */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] {
        flex-direction: column !important;
        border: none !important;
        gap: 0.4rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 0.4rem 0 !important;
        border-bottom: none !important;
        border-radius: 0 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
        display: flex !important;
    }

    /* ✅ ناوبری تب‌مانند: فقط در محتوای اصلی، نه سایدبار */
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] {
        flex-direction: row !important;
        gap: 0.25rem !important;
        border-bottom: 1px solid #e5e7eb !important;
        margin-bottom: 1.5rem !important;
        padding: 0 !important;
        justify-content: flex-start !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 0.75rem 1.4rem !important;
        margin: 0 !important;
        cursor: pointer !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0 !important;
        transition: all 0.15s ease !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
        background: #f3f4f6 !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
        border-bottom-color: #3b82f6 !important;
        color: #1d4ed8 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    /* دکمه دانلود در سایدبار: تمام عرض */
    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
        width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# ================== تنظیمات GitHub ==================
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"

def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

# ================== ذخیره‌سازی محلی (فایل مجزا) ==================
def load_local_file():
    """خواندن از data.json کنار app.py"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None

def save_local_file(data):
    """ذخیره در data.json"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.warning(f"⚠️ ذخیره محلی ناموفق: {e}")
        return False

# ================== ذخیره‌سازی GitHub ==================
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
        "content": base64.b64encode(
            json.dumps(data, ensure_ascii=False, indent=2).encode()
        ).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    try:
        r = requests.put(url, headers=github_headers(), json=payload, timeout=15)
        return r.status_code in (200, 201)
    except Exception:
        return False

# ================== بارگذاری/ذخیره ترکیبی ==================
def migrate_data(data):
    """سازگاری با ساختار قدیمی (usd_rate → usd_rates)"""
    if not data:
        return {"journals": [], "usd_rates": []}
    if "usd_rates" not in data:
        data["usd_rates"] = []
        if data.get("usd_rate"):
            data["usd_rates"].append({
                "id": datetime.now().isoformat(),
                "rate": data["usd_rate"],
                "note": "منتقل‌شده از نسخه قدیمی",
                "created_at": datetime.now().isoformat(),
                "created_at_jalali": today_jalali_str(),
            })
        data.pop("usd_rate", None)
    data.setdefault("journals", [])
    return data

def load_all():
    """بارگذاری: اولویت با فایل محلی (تازه‌ترین)، اگر خالی بود از GitHub"""
    local = load_local_file()
    if local and (local.get("journals") or local.get("usd_rates")):
        return migrate_data(local)
    gh = load_github_file()
    if gh:
        return migrate_data(gh)
    return {"journals": [], "usd_rates": []}

def save_all(data):
    """ذخیره همزمان در فایل محلی و GitHub"""
    local_ok = save_local_file(data)
    gh_ok = save_github_file(data)
    if local_ok and gh_ok:
        st.toast("ذخیره شد (فایل محلی + GitHub)", icon="✅")
    elif local_ok:
        st.toast("ذخیره در فایل محلی ✅ (GitHub تنظیم نشده)", icon="💾")
    elif gh_ok:
        st.toast("ذخیره در GitHub ✅ (فایل محلی ناموفق)", icon="☁️")
    else:
        st.error("⚠️ ذخیره‌سازی ناموفق بود! لطفاً دسترسی‌ها را بررسی کنید.")

def get_current_usd_rate(data):
    rates = data.get("usd_rates", [])
    if not rates:
        return None, None
    latest = max(rates, key=lambda x: x.get("created_at", ""))
    return latest["rate"], latest.get("created_at_jalali", "—")

# ================== مقداردهی اولیه ==================
if "data" not in st.session_state:
    st.session_state.data = load_all()
data = st.session_state.data

# ================== سایدبار ==================
with st.sidebar:
    st.markdown(f"### 🗓️ امروز: **{today_jalali_str()}**")
    st.caption(f"میلادی: {datetime.now().strftime('%Y-%m-%d')}")
    st.divider()

    # نمایش نرخ دلار با کارت HTML (جلوگیری از overflow)
    rate, rate_date = get_current_usd_rate(data)
    if rate:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            padding: 14px 16px;
            border-radius: 10px;
            border-right: 4px solid #3b82f6;
            margin-bottom: 12px;
            direction: rtl;
            text-align: right;
        ">
            <div style="font-size: 0.82rem; color: #6b7280; margin-bottom: 6px;">
                💵 نرخ فعلی دلار
            </div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #1e40af; line-height: 1.2;">
                {rate:,.0f}
                <span style="font-size: 0.95rem; color: #6b7280;">ریال</span>
            </div>
            <div style="font-size: 0.72rem; color: #9ca3af; margin-top: 6px;">
                آخرین بروزرسانی: {rate_date}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("💡 هنوز نرخی ثبت نشده. از تب «💵 دلار» ثبت کنید.")

    st.divider()

    # وضعیت ذخیره‌سازی
    st.markdown("**💾 وضعیت ذخیره‌سازی**")
    local_ok = os.path.exists(DATA_FILE)
    gh_ok = bool(GITHUB_TOKEN and GITHUB_REPO)
    st.caption(
        f"{'✅' if local_ok else '❌'} فایل محلی: `data.json`  \n"
        f"{'✅' if gh_ok else '❌'} GitHub: {'متصل' if gh_ok else 'تنظیم نشده'}"
    )
    st.divider()

    # پشتیبان‌گیری
    with st.expander("📥 پشتیبان‌گیری / 📤 بازیابی", expanded=False):
        st.download_button(
            "📥 دانلود فایل JSON",
            data=json.dumps(data, ensure_ascii=False, indent=2),
            file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )
        uploaded = st.file_uploader(
            "📤 آپلود فایل پشتیبان",
            type=["json"],
            key="uploader",
        )
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
selected = st.radio(
    "ناوبری",
    options=["overview", "journal", "usd"],
    format_func=lambda x: {
        "overview": "📊 نمای کلی",
        "journal": "📒 ژورنال",
        "usd": "💵 دلار",
    }[x],
    index=0,
    horizontal=True,
    label_visibility="collapsed",
    key="nav_tab",
)

# ================== تب ۱: نمای کلی ==================
if selected == "overview":
    st.header("📊 نمای کلی دارایی‌ها")
    journals = data.get("journals", [])
    rate, _ = get_current_usd_rate(data)

    if not journals:
        st.info("هنوز دارایی‌ای ثبت نشده. از تب «📒 ژورنال» اضافه کنید.")
    else:
        rows = []
        for j in journals:
            amt = j["amount"]
            cur = j["currency"]
            usd_eq = (amt / rate) if (cur == "IRR" and rate and rate > 0) else (amt if cur == "USD" else None)
            rows.append({
                "دارایی": j["asset_name"],
                "مبلغ": amt,
                "ارز": "ریال" if cur == "IRR" else "دلار",
                "معادل_دلاری": usd_eq,
                "تاریخ_شمسی": j.get("created_at_jalali", "—"),
            })
        df = pd.DataFrame(rows)

        total_usd = df["معادل_دلاری"].dropna().sum() if not df["معادل_دلاری"].isna().all() else 0
        total_irr = df[df["ارز"] == "ریال"]["مبلغ"].sum()
        total_usd_dir = df[df["ارز"] == "دلار"]["مبلغ"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("💰 کل دارایی (دلاری)", f"${total_usd:,.2f}")
        c2.metric("🇮🇷 دارایی ریالی", f"{total_irr:,.0f} ریال")
        c3.metric("🇺🇸 دارایی دلاری", f"${total_usd_dir:,.2f}")

        st.subheader("🥧 ترکیب دارایی‌ها (بر اساس معادل دلاری)")
        pie_df = df.dropna(subset=["معادل_دلاری"])
        if not pie_df.empty and pie_df["معادل_دلاری"].sum() > 0:
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
            st.info("برای نمایش پای‌چارت، ابتدا نرخ دلار را در تب «💵 دلار» ثبت کنید.")

        st.subheader("📋 جدول دارایی‌ها")
        display = df.copy()
        display["معادل_دلاری"] = display["معادل_دلاری"].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
        )
        display["مبلغ"] = display.apply(
            lambda r: f"{r['مبلغ']:,.0f} {'ریال' if r['ارز']=='ریال' else 'دلار'}", axis=1
        )
        display = display[["دارایی", "مبلغ", "معادل_دلاری", "تاریخ_شمسی"]]
        display.columns = ["دارایی", "مبلغ", "معادل دلاری", "تاریخ ثبت (شمسی)"]
        st.dataframe(display, use_container_width=True, hide_index=True)

# ================== تب ۲: ژورنال ==================
elif selected == "journal":
    st.header("📒 ژورنال دارایی‌ها")

    with st.container(border=True):
        st.subheader("➕ افزودن دارایی جدید")
        with st.form("add_asset_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            name = c1.text_input("نام دارایی", placeholder="مثلاً: طلا، سهام، دلار نقدی")
            amount = c2.number_input("مبلغ", min_value=0.0, format="%.2f", step=1000.0)
            currency = c3.selectbox(
                "ارز", ["IRR", "USD"],
                format_func=lambda x: "ریال" if x == "IRR" else "دلار",
            )
            st.caption(
                f"📅 تاریخ ثبت خودکار → شمسی: **{today_jalali_str()}** | "
                f"میلادی: {datetime.now().strftime('%Y-%m-%d')}"
            )
            if st.form_submit_button("💾 ثبت دارایی", use_container_width=True):
                if not name.strip():
                    st.error("نام دارایی را وارد کنید.")
                elif amount <= 0:
                    st.error("مبلغ باید بزرگتر از صفر باشد.")
                else:
                    now = datetime.now().isoformat()
                    data["journals"].append({
                        "id": now,
                        "asset_name": name.strip(),
                        "amount": amount,
                        "currency": currency,
                        "created_at_gregorian": now,
                        "created_at_jalali": today_jalali_str(),
                    })
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()

    journals = data.get("journals", [])
    if not journals:
        st.info("هنوز دارایی‌ای ثبت نشده.")
    else:
        st.subheader("📝 لیست دارایی‌های ثبت‌شده")
        sorted_j = sorted(journals, key=lambda x: x.get("created_at_gregorian", ""), reverse=True)
        for j in sorted_j:
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
                c1.markdown(f"**{j['asset_name']}**")
                c2.write(f"{j['amount']:,.0f} {'ریال' if j['currency']=='IRR' else 'دلار'}")
                c3.caption(f"📅 {j.get('created_at_jalali', '—')}")
                c4.caption(iso_to_jalali(j.get("created_at_gregorian", ""), with_time=True))
                if c5.button("🗑️", key=f"del_{j['id']}", help="حذف"):
                    data["journals"] = [x for x in data["journals"] if x["id"] != j["id"]]
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()

# ================== تب ۳: دلار ==================
else:
    st.header("💵 نرخ دلار به ریال")
    st.caption(
        f"📅 امروز — شمسی: **{today_jalali_str()}** | "
        f"میلادی: {datetime.now().strftime('%Y-%m-%d')}"
    )

    with st.container(border=True):
        st.subheader("➕ ثبت نرخ جدید")
        with st.form("usd_rate_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 3])
            new_rate = c1.number_input("نرخ دلار (ریال)", min_value=0, step=1000, format="%d")
            note = c2.text_input("توضیح (اختیاری)", placeholder="مثلاً: بازار آزاد")
            if st.form_submit_button("💾 ثبت نرخ", use_container_width=True):
                if new_rate > 0:
                    now = datetime.now().isoformat()
                    data.setdefault("usd_rates", []).append({
                        "id": now,
                        "rate": new_rate,
                        "note": note.strip(),
                        "created_at": now,
                        "created_at_jalali": today_jalali_str(),
                    })
                    st.session_state.data = data
                    save_all(data)
                    st.rerun()
                else:
                    st.error("نرخ باید بزرگتر از صفر باشد.")

    rates = data.get("usd_rates", [])
    if not rates:
        st.info("هنوز نرخی ثبت نشده. اولین نرخ را ثبت کنید.")
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
        fig = px.line(
            chart_df, x="تاریخ", y="rate", markers=True,
            labels={"تاریخ": "تاریخ", "rate": "نرخ (ریال)"},
        )
        fig.update_layout(
            font=dict(family="Vazirmatn, B Nazanin, Tahoma", size=13),
            margin=dict(t=20, b=20),
        )
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
