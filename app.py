import streamlit as st
import pandas as pd
import plotly.express as px
import json
import requests
import base64
from datetime import datetime
import jdatetime

# ================== تنظیمات صفحه ==================
st.set_page_config(page_title="داشبورد مالی", layout="wide")

# ================== توابع تاریخ شمسی ==================
def today_jalali_str():
    """تاریخ شمسی امروز به فرمت خوانا"""
    j = jdatetime.date.today()
    return j.strftime("%Y/%m/%d")

def iso_to_jalali(iso_str, with_time=True):
    """تبدیل رشته ISO میلادی به تاریخ شمسی"""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str)
        j = jdatetime.datetime.fromgregorian(datetime=dt)
        if with_time:
            return j.strftime("%Y/%m/%d - %H:%M")
        return j.strftime("%Y/%m/%d")
    except Exception:
        return "—"

# ================== تزریق CSS: راست‌چین + فونت نازنین ==================
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
    * { font-family: 'Vazirmatn', 'B Nazanin', Tahoma, sans-serif !important; }
    .stApp, div, p, h1, h2, h3, h4, h5, h6, label, .stMarkdown, .stText, .stButton {
        direction: rtl !important; text-align: right !important;
    }
    table { direction: rtl !important; text-align: right !important; }
    input, select, textarea { direction: rtl !important; text-align: right !important; }
    section[data-testid="stSidebar"] { direction: rtl !important; text-align: right !important; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ================== تنظیمات GitHub ==================
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "your-username/financial-dashboard")
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"

def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"}

def load_data_from_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        st.warning("توکن GitHub یا نام مخزن تنظیم نشده است. داده‌ها موقتاً در حافظه ذخیره می‌شوند.")
        return {"journals": [], "usd_rates": []}
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        resp = requests.get(url, headers=github_headers(), timeout=10)
        if resp.status_code == 200:
            content = base64.b64decode(resp.json()["content"]).decode("utf-8")
            data = json.loads(content)
            # سازگاری با نسخه قدیمی (فیلد usd_rate تک‌عددی)
            if "usd_rates" not in data:
                data["usd_rates"] = []
                if data.get("usd_rate"):
                    data["usd_rates"].append({
                        "rate": data["usd_rate"],
                        "created_at": datetime.now().isoformat(),
                        "created_at_jalali": today_jalali_str(),
                        "note": "منتقل شده از نسخه قدیمی"
                    })
                data.pop("usd_rate", None)
            return data
        elif resp.status_code == 404:
            return {"journals": [], "usd_rates": []}
        else:
            st.error(f"خطا در خواندن از GitHub: {resp.status_code}")
            return {"journals": [], "usd_rates": []}
    except Exception as e:
        st.error(f"خطا در ارتباط با GitHub: {e}")
        return {"journals": [], "usd_rates": []}

def save_data_to_github(data):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        st.info("داده‌ها فقط در حافظه ذخیره شدند (GitHub تنظیم نشده).")
        return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    sha = None
    try:
        resp = requests.get(url, headers=github_headers(), timeout=10)
        if resp.status_code == 200:
            sha = resp.json()["sha"]
    except:
        pass
    content_encoded = base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=2).encode()
    ).decode()
    payload = {
        "message": f"بروزرسانی داشبورد - {today_jalali_str()} {datetime.now().strftime('%H:%M')}",
        "content": content_encoded,
        "branch": GITHUB_BRANCH
    }
    if sha:
        payload["sha"] = sha
    try:
        resp = requests.put(url, headers=github_headers(), json=payload, timeout=15)
        if resp.status_code in (200, 201):
            st.success("✅ داده‌ها با موفقیت در GitHub ذخیره شد.")
            return True
        else:
            st.error(f"خطا در ذخیره در GitHub: {resp.status_code}")
            return False
    except Exception as e:
        st.error(f"خطا در ارتباط با GitHub: {e}")
        return False

# ================== توابع کمکی ==================
def get_current_usd_rate(data):
    """آخرین نرخ ثبت‌شده دلار"""
    rates = data.get("usd_rates", [])
    if not rates:
        return None, None
    sorted_rates = sorted(rates, key=lambda x: x.get("created_at", ""))
    latest = sorted_rates[-1]
    return latest["rate"], latest.get("created_at_jalali", "—")

# ================== مقداردهی اولیه ==================
if "data" not in st.session_state:
    st.session_state.data = load_data_from_github()
data = st.session_state.data

# ================== سایدبار: مدیریت داده + نمایش تاریخ و نرخ ==================
with st.sidebar:
    st.header("💵 نرخ دلار و تاریخ")
    
    # نمایش تاریخ شمسی امروز
    st.markdown(f"### 🗓️ امروز: **{today_jalali_str()}**")
    
    # نمایش نرخ فعلی از صفحه دلار
    current_rate, rate_date = get_current_usd_rate(data)
    if current_rate:
        st.metric("نرخ فعلی دلار", f"{current_rate:,.0f} ریال",
                  help=f"آخرین بروزرسانی: {rate_date}")
    else:
        st.info("هنوز نرخی ثبت نشده است. از تب «💵 دلار» ثبت کنید.")
    
    st.divider()
    
    # --- پشتیبان‌گیری ---
    st.subheader("📥 دریافت خروجی (پشتیبان)")
    st.download_button(
        label="دانلود فایل JSON",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name=f"financial_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        key="download_backup"
    )
    
    st.subheader("📤 بازیابی از فایل")
    uploaded_file = st.file_uploader("فایل JSON پشتیبان را انتخاب کنید",
                                     type=["json"], key="upload_backup")
    if uploaded_file is not None:
        try:
            imported_data = json.loads(uploaded_file.read().decode("utf-8"))
            if st.button("✅ اعمال و ذخیره بازیابی", key="restore_btn"):
                st.session_state.data = imported_data
                save_data_to_github(imported_data)
                st.success("داده‌ها با موفقیت بازیابی شدند.")
                st.rerun()
        except Exception as e:
            st.error(f"فایل معتبر نیست: {e}")
    
    st.divider()
    st.caption("نکته: داده‌ها به‌صورت خودکار در GitHub ذخیره می‌شوند.")

# ================== تب‌بندی اصلی ==================
tab1, tab2, tab3 = st.tabs([
    "📊 نمای کلی دارایی‌ها",
    "📒 ژورنال دارایی‌ها",
    "💵 دلار (نرخ و تاریخچه)"
])

# ================== تب ۱: نمای کلی ==================
with tab1:
    st.header("📊 نمای کلی دارایی‌ها")
    
    journals = data.get("journals", [])
    current_rate, _ = get_current_usd_rate(data)
    
    if not journals:
        st.info("هنوز هیچ دارایی ثبت نشده است. از تب «📒 ژورنال دارایی‌ها» اضافه کنید.")
    else:
        rows = []
        for j in journals:
            amount = j["amount"]
            currency = j["currency"]
            if currency == "IRR":
                usd_equivalent = (amount / current_rate) if current_rate and current_rate > 0 else None
            else:
                usd_equivalent = amount
            rows.append({
                "دارایی": j["asset_name"],
                "مبلغ": amount,
                "ارز": "ریال" if currency == "IRR" else "دلار",
                "معادل دلاری": usd_equivalent,
                "تاریخ ثبت (شمسی)": j.get("created_at_jalali", "—")
            })
        
        df = pd.DataFrame(rows)
        
        # --- کارت‌های خلاصه ---
        total_usd = df["معادل دلاری"].dropna().sum() if not df["معادل دلاری"].isna().all() else 0
        total_irr = df[df["ارز"] == "ریال"]["مبلغ"].sum()
        total_usd_direct = df[df["ارز"] == "دلار"]["مبلغ"].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 کل دارایی (دلاری)", f"${total_usd:,.2f}")
        with col2:
            st.metric("🇮🇷 دارایی ریالی", f"{total_irr:,.0f} ریال")
        with col3:
            st.metric("🇺🇸 دارایی دلاری", f"${total_usd_direct:,.2f}")
        
        # --- نمودار پای چارت ---
        st.subheader("🥧 ترکیب دارایی‌ها (بر اساس معادل دلاری)")
        pie_df = df.dropna(subset=["معادل دلاری"])
        if not pie_df.empty and pie_df["معادل دلاری"].sum() > 0:
            fig_pie = px.pie(
                pie_df, values="معادل دلاری", names="دارایی", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_layout(
                font=dict(family="Vazirmatn, B Nazanin, Tahoma", size=14),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                margin=dict(t=30, b=30, l=10, r=10)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("برای نمایش پای‌چارت، ابتدا نرخ دلار را در تب «💵 دلار» ثبت کنید.")
        
        # --- جدول دارایی‌ها ---
        st.subheader("📋 جدول دارایی‌ها")
        display_df = df.copy()
        display_df["معادل دلاری"] = display_df["معادل دلاری"].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
        )
        display_df["مبلغ"] = display_df.apply(
            lambda r: f"{r['مبلغ']:,.0f} {'ریال' if r['ارز']=='ریال' else 'دلار'}", axis=1
        )
        display_df = display_df[["دارایی", "مبلغ", "معادل دلاری", "تاریخ ثبت (شمسی)"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ================== تب ۲: ژورنال ==================
with tab2:
    st.header("📒 ژورنال دارایی‌ها")
    
    with st.expander("➕ افزودن دارایی جدید", expanded=True):
        with st.form("add_asset_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                asset_name = st.text_input("نام دارایی", placeholder="مثلاً: طلا، سهام")
            with col2:
                amount = st.number_input("مبلغ", min_value=0.0, format="%.2f", step=1000.0)
            with col3:
                currency = st.selectbox("ارز", options=["IRR", "USD"],
                                        format_func=lambda x: "ریال" if x == "IRR" else "دلار")
            
            st.caption(f"📅 تاریخ ثبت خودکار: **{today_jalali_str()}** "
                       f"(میلادی: {datetime.now().strftime('%Y-%m-%d')})")
            
            submitted = st.form_submit_button("ثبت دارایی")
            if submitted:
                if not asset_name.strip():
                    st.error("نام دارایی را وارد کنید.")
                elif amount <= 0:
                    st.error("مبلغ باید بزرگتر از صفر باشد.")
                else:
                    now_iso = datetime.now().isoformat()
                    data["journals"].append({
                        "id": now_iso,
                        "asset_name": asset_name.strip(),
                        "amount": amount,
                        "currency": currency,
                        "created_at_gregorian": now_iso,
                        "created_at_jalali": today_jalali_str(),
                    })
                    st.session_state.data = data
                    save_data_to_github(data)
                    st.success(f"دارایی «{asset_name}» ثبت شد.")
                    st.rerun()
    
    journals = data.get("journals", [])
    if not journals:
        st.info("هنوز دارایی‌ای ثبت نشده است.")
    else:
        st.subheader("📝 لیست دارایی‌های ثبت‌شده")
        # جدیدترین‌ها بالای لیست
        sorted_journals = sorted(journals,
            key=lambda x: x.get("created_at_gregorian", x.get("created_at", "")),
            reverse=True)
        for j in sorted_journals:
            with st.container(border=True):
                cols = st.columns([3, 2, 2, 2, 1])
                with cols[0]:
                    st.write(f"**{j['asset_name']}**")
                with cols[1]:
                    st.write(f"{j['amount']:,.0f} {'ریال' if j['currency']=='IRR' else 'دلار'}")
                with cols[2]:
                    st.caption(j.get("created_at_jalali",
                                     iso_to_jalali(j.get("created_at_gregorian", ""), with_time=False)))
                with cols[3]:
                    st.caption(iso_to_jalali(j.get("created_at_gregorian", ""), with_time=True))
                with cols[4]:
                    if st.button("🗑️", key=f"del_{j['id']}", help="حذف"):
                        data["journals"] = [x for x in data["journals"] if x["id"] != j["id"]]
                        st.session_state.data = data
                        save_data_to_github(data)
                        st.rerun()

# ================== تب ۳: صفحه اختصاصی دلار ==================
with tab3:
    st.header("💵 نرخ دلار به ریال")
    
    st.markdown(f"**تاریخ امروز (شمسی):** {today_jalali_str()} &nbsp;|&nbsp; "
                f"**تاریخ میلادی:** {datetime.now().strftime('%Y-%m-%d')}")
    
    # --- فرم ثبت نرخ ---
    with st.form("usd_rate_form"):
        st.subheader("➕ ثبت نرخ جدید")
        col1, col2 = st.columns([2, 3])
        with col1:
            new_rate = st.number_input("نرخ دلار (ریال)", min_value=0, step=1000, format="%d")
        with col2:
            note = st.text_input("توضیح (اختیاری)", placeholder="مثلاً: نرخ بازار آزاد")
        
        if st.form_submit_button("ثبت نرخ"):
            if new_rate > 0:
                now_iso = datetime.now().isoformat()
                data.setdefault("usd_rates", []).append({
                    "id": now_iso,
                    "rate": new_rate,
                    "note": note.strip(),
                    "created_at": now_iso,
                    "created_at_jalali": today_jalali_str(),
                })
                st.session_state.data = data
                save_data_to_github(data)
                st.success(f"نرخ {new_rate:,.0f} ریال ثبت شد.")
                st.rerun()
            else:
                st.error("نرخ باید بزرگتر از صفر باشد.")
    
    # --- تاریخچه و نمودار ---
    rates = data.get("usd_rates", [])
    if not rates:
        st.info("هنوز نرخی ثبت نشده است.")
    else:
        sorted_rates = sorted(rates, key=lambda x: x.get("created_at", ""))
        current_rate, rate_date = get_current_usd_rate(data)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("نرخ فعلی", f"{current_rate:,.0f} ریال")
        with col2:
            st.metric("تعداد ثبت‌ها", len(rates))
        with col3:
            st.metric("آخرین بروزرسانی", rate_date or "—")
        
        # نمودار روند
        st.subheader("📈 نمودار روند نرخ دلار")
        chart_df = pd.DataFrame(sorted_rates)
        chart_df["تاریخ"] = chart_df["created_at_jalali"]
        chart_df = chart_df.sort_values("created_at")
        fig_line = px.line(
            chart_df, x="تاریخ", y="rate", markers=True,
            labels={"تاریخ": "تاریخ", "rate": "نرخ (ریال)"}
        )
        fig_line.update_layout(
            font=dict(family="Vazirmatn, B Nazanin, Tahoma", size=13),
            margin=dict(t=20, b=20)
        )
        st.plotly_chart(fig_line, use_container_width=True)
        
        # جدول تاریخچه
        st.subheader("📋 تاریخچه نرخ‌ها")
        for r in reversed(sorted_rates):
            with st.container(border=True):
                cols = st.columns([2, 2, 3, 2, 1])
                with cols[0]:
                    st.write(f"**{r['rate']:,.0f} ریال**")
                with cols[1]:
                    st.caption(f"📅 {r.get('created_at_jalali', '—')}")
                with cols[2]:
                    st.caption(r.get("note", "—") or "—")
                with cols[3]:
                    st.caption(iso_to_jalali(r.get("created_at", ""), with_time=True))
                with cols[4]:
                    if st.button("🗑️", key=f"delrate_{r['id']}", help="حذف"):
                        data["usd_rates"] = [x for x in data["usd_rates"] if x["id"] != r["id"]]
                        st.session_state.data = data
                        save_data_to_github(data)
                        st.rerun()
