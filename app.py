import streamlit as st
import pandas as pd
import plotly.express as px
import json
import requests
import base64
from datetime import datetime
import jdatetime

# ================== تنظیمات صفحه ==================
st.set_page_config(
    page_title="داشبورد مالی",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== توابع کمکی تاریخ ==================
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

# ================== CSS: راست‌چین + فونت نازنین + رفع مشکل هدر ==================
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
    
    * { font-family: 'Vazirmatn', 'B Nazanin', Tahoma, sans-serif !important; }
    
    .stApp, div, p, h1, h2, h3, h4, h5, h6, label, .stMarkdown, .stText {
        direction: rtl; text-align: right;
    }
    
    /* ✅✅✅ رفع مشکل اصلی: جلوگیری از مخفی شدن تب‌ها زیر هدر ثابت ✅✅✅ */
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1250px;
    }
    
    /* هدر ثابت Streamlit همیشه بالاترین لایه باشد */
    header[data-testid="stHeader"] { z-index: 999; }
    
    /* راست‌چین جدول و فرم‌ها */
    table { direction: rtl !important; text-align: right !important; }
    input, select, textarea { direction: rtl !important; text-align: right !important; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
    
    /* ناوبری: تبدیل radio به تب‌های حرفه‌ای */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        flex-direction: row;
        gap: 0.25rem;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 1.5rem;
        padding: 0;
        justify-content: flex-start;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 0.75rem 1.4rem;
        margin: 0;
        cursor: pointer;
        border-bottom: 3px solid transparent;
        direction: rtl;
        background: transparent;
        border-radius: 0;
        transition: all 0.15s ease;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
        background: #f3f4f6;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
        border-bottom-color: #3b82f6;
        color: #1d4ed8;
        font-weight: 600;
    }
    /* مخفی کردن دایره رادیویی */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
        display: none;
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

def load_data_from_github():
    empty = {"journals": [], "usd_rates": []}
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return empty
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(url, headers=github_headers(), timeout=10)
        if r.status_code == 200:
            data = json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
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
            return data
        return empty
    except Exception as e:
        st.error(f"خطا در خواندن از GitHub: {e}")
        return empty

def save_data_to_github(data, notify=True):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        if notify:
            st.toast("ذخیره ابری فعال نیست (GitHub تنظیم نشده)", icon="⚠️")
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
        if r.status_code in (200, 201):
            if notify:
                st.toast("ذخیره شد", icon="✅")
            return True
        st.error(f"خطا در ذخیره: {r.status_code}")
        return False
    except Exception as e:
        st.error(f"خطا در ارتباط با GitHub: {e}")
        return False

def get_current_usd_rate(data):
    rates = data.get("usd_rates", [])
    if not rates:
        return None, None
    latest = max(rates, key=lambda x: x.get("created_at", ""))
    return latest["rate"], latest.get("created_at_jalali", "—")

# ================== مقداردهی اولیه ==================
if "data" not in st.session_state:
    st.session_state.data = load_data_from_github()
data = st.session_state.data

# ================== سایدبار ==================
with st.sidebar:
    st.markdown(f"### 🗓️ امروز: **{today_jalali_str()}**")
    st.caption(f"میلادی: {datetime.now().strftime('%Y-%m-%d')}")
    
    rate, rate_date = get_current_usd_rate(data)
    if rate:
        st.metric(
            "💵 نرخ فعلی دلار",
            f"{rate:,.0f} ریال",
            help=f"آخرین بروزرسانی: {rate_date}",
        )
    else:
        st.info("هنوز نرخی ثبت نشده. از تب «💵 دلار» ثبت کنید.")
    
    st.divider()
    
    with st.expander("💾 پشتیبان‌گیری و بازیابی", expanded=False):
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
                if st.button("✅ اعمال و ذخیره بازیابی", use_container_width=True):
                    st.session_state.data = imported
                    save_data_to_github(imported)
                    st.rerun()
            except Exception as e:
                st.error(f"فایل معتبر نیست: {e}")
    
    st.caption("ℹ️ داده‌ها به‌صورت خودکار در GitHub ذخیره می‌شوند.")

# ================== ناوبری (radio با key → حفظ تب فعال) ==================
tabs_list = ["overview", "journal", "usd"]
labels = {
    "overview": "📊 نمای کلی",
    "journal": "📒 ژورنال",
    "usd": "💵 دلار",
}

selected = st.radio(
    "ناوبری",
    options=tabs_list,
    format_func=lambda x: labels[x],
    index=0,
    horizontal=True,
    label_visibility="collapsed",
    key="nav_tab",   # ← کلید حفظ تب فعال در rerun
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
            if cur == "IRR":
                usd_eq = (amt / rate) if (rate and rate > 0) else None
            else:
                usd_eq = amt
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
                    save_data_to_github(data)
                    st.rerun()
    
    journals = data.get("journals", [])
    if not journals:
        st.info("هنوز دارایی‌ای ثبت نشده.")
    else:
        st.subheader("📝 لیست دارایی‌های ثبت‌شده")
        sorted_j = sorted(
            journals,
            key=lambda x: x.get("created_at_gregorian", ""),
            reverse=True,
        )
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
                    save_data_to_github(data)
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
            new_rate = c1.number_input(
                "نرخ دلار (ریال)", min_value=0, step=1000, format="%d"
            )
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
                    save_data_to_github(data)
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
                    data["usd_rates"] = [
                        x for x in data["usd_rates"] if x["id"] != r["id"]
                    ]
                    st.session_state.data = data
                    save_data_to_github(data)
                    st.rerun()
