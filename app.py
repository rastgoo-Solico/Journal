import streamlit as st
import pandas as pd
import plotly.express as px
import json
import requests
import base64
from datetime import datetime
from io import BytesIO

# ================== تنظیمات صفحه ==================
st.set_page_config(page_title="داشبورد مالی", layout="wide")

# ================== تزریق CSS برای راست‌چین و فونت نازنین ==================
st.markdown("""
<style>
    /* فونت نازنین */
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
    * {
        font-family: 'Vazirmatn', 'B Nazanin', Tahoma, sans-serif !important;
    }
    /* راست‌چین کردن کل صفحه */
    .stApp, div, p, h1, h2, h3, h4, h5, h6, label, .stMarkdown, .stText, .stButton {
        direction: rtl !important;
        text-align: right !important;
    }
    /* اصلاح جهت جدول‌ها */
    table {
        direction: rtl !important;
        text-align: right !important;
    }
    /* اصلاح جهت ورودی‌ها */
    input, select, textarea {
        direction: rtl !important;
        text-align: right !important;
    }
    /* اصلاح جهت سایدبار */
    section[data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }
    /* حذف حاشیه پیش‌فرض برای ظاهر تمیزتر */
    .block-container {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ================== تنظیمات GitHub ==================
# این مقادیر را در Streamlit Secrets قرار دهید
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "your-username/financial-dashboard")
GITHUB_FILE_PATH = "data.json"  # مسیر فایل در مخزن
GITHUB_BRANCH = "main"

# ================== توابع ذخیره‌سازی GitHub ==================
def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def load_data_from_github():
    """خواندن فایل JSON از GitHub"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        st.warning("توکن GitHub یا نام مخزن تنظیم نشده است. داده‌ها موقتاً در حافظه ذخیره می‌شوند.")
        return {"journals": [], "usd_rate": None}
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        resp = requests.get(url, headers=github_headers(), timeout=10)
        if resp.status_code == 200:
            content = base64.b64decode(resp.json()["content"]).decode("utf-8")
            return json.loads(content)
        elif resp.status_code == 404:
            # فایل وجود ندارد، داده خالی برگردان
            return {"journals": [], "usd_rate": None}
        else:
            st.error(f"خطا در خواندن از GitHub: {resp.status_code}")
            return {"journals": [], "usd_rate": None}
    except Exception as e:
        st.error(f"خطا در ارتباط با GitHub: {e}")
        return {"journals": [], "usd_rate": None}

def save_data_to_github(data):
    """ذخیره فایل JSON در GitHub"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        st.info("داده‌ها فقط در حافظه ذخیره شدند (GitHub تنظیم نشده).")
        return False
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    # ابتدا SHA فعلی فایل را بگیر (اگر وجود دارد)
    sha = None
    try:
        resp = requests.get(url, headers=github_headers(), timeout=10)
        if resp.status_code == 200:
            sha = resp.json()["sha"]
    except:
        pass
    
    content_encoded = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode()
    payload = {
        "message": f"بروزرسانی داشبورد - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
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
            st.error(f"خطا در ذخیره در GitHub: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        st.error(f"خطا در ارتباط با GitHub: {e}")
        return False

# ================== مقداردهی اولیه ==================
if "data" not in st.session_state:
    st.session_state.data = load_data_from_github()

data = st.session_state.data

# ================== سایدبار: مدیریت داده و پشتیبان‌گیری ==================
with st.sidebar:
    st.header("⚙️ مدیریت داده‌ها")
    
    # --- پشتیبان‌گیری (Export) ---
    st.subheader("📥 دریافت خروجی (پشتیبان)")
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    st.download_button(
        label="دانلود فایل JSON",
        data=json_str,
        file_name=f"financial_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        key="download_backup"
    )
    
    # --- بازیابی (Import) ---
    st.subheader("📤 بازیابی از فایل")
    uploaded_file = st.file_uploader("فایل JSON پشتیبان را انتخاب کنید", type=["json"], key="upload_backup")
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

# ================== نوار کناری: ورود نرخ دلار ==================
with st.sidebar:
    st.header("💵 نرخ دلار به ریال")
    current_rate = data.get("usd_rate")
    if current_rate:
        st.metric("نرخ فعلی", f"{current_rate:,.0f} ریال")
    else:
        st.info("هنوز نرخی ثبت نشده است.")
    
    with st.form("usd_rate_form"):
        new_rate = st.number_input(
            "نرخ جدید (ریال)",
            min_value=0,
            value=current_rate if current_rate else 0,
            step=1000,
            format="%d"
        )
        if st.form_submit_button("ثبت نرخ"):
            if new_rate > 0:
                data["usd_rate"] = new_rate
                st.session_state.data = data
                save_data_to_github(data)
                st.rerun()
            else:
                st.error("نرخ باید بزرگتر از صفر باشد.")

# ================== تب‌بندی اصلی ==================
tab1, tab2 = st.tabs(["📊 نمای کلی دارایی‌ها", "📒 ژورنال دارایی‌ها"])

# ================== تب ۱: نمای کلی ==================
with tab1:
    st.header("📊 نمای کلی دارایی‌ها")
    
    journals = data.get("journals", [])
    usd_rate = data.get("usd_rate")
    
    if not journals:
        st.info("هنوز هیچ دارایی ثبت نشده است. از تب «ژورنال دارایی‌ها» اضافه کنید.")
    else:
        # --- محاسبه معادل دلاری ---
        rows = []
        for j in journals:
            amount = j["amount"]
            currency = j["currency"]
            if currency == "IRR":
                if usd_rate and usd_rate > 0:
                    usd_equivalent = amount / usd_rate
                else:
                    usd_equivalent = None  # نرخ دلار ثبت نشده
            else:  # USD
                usd_equivalent = amount
            
            rows.append({
                "دارایی": j["asset_name"],
                "مبلغ": amount,
                "ارز": "ریال" if currency == "IRR" else "دلار",
                "معادل دلاری": usd_equivalent
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
                pie_df,
                values="معادل دلاری",
                names="دارایی",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_layout(
                font=dict(family="Vazirmatn, B Nazanin, Tahoma", size=14),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                margin=dict(t=30, b=30, l=10, r=10)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("برای نمایش پای‌چارت، ابتدا نرخ دلار را ثبت کنید یا دارایی دلاری اضافه کنید.")
        
        # --- جدول دارایی‌ها ---
        st.subheader("📋 جدول دارایی‌ها")
        display_df = df.copy()
        display_df["معادل دلاری"] = display_df["معادل دلاری"].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
        )
        display_df["مبلغ"] = display_df.apply(
            lambda r: f"{r['مبلغ']:,.0f} {'ریال' if r['ارز']=='ریال' else 'دلار'}", axis=1
        )
        display_df = display_df[["دارایی", "مبلغ", "معادل دلاری"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ================== تب ۲: ژورنال ==================
with tab2:
    st.header("📒 ژورنال دارایی‌ها")
    
    # --- فرم افزودن دارایی جدید ---
    with st.expander("➕ افزودن دارایی جدید", expanded=True):
        with st.form("add_asset_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                asset_name = st.text_input("نام دارایی", placeholder="مثلاً: طلا، سهام، دلار نقدی")
            with col2:
                amount = st.number_input("مبلغ", min_value=0.0, format="%.2f", step=1000.0)
            with col3:
                currency = st.selectbox("ارز", options=["IRR", "USD"], format_func=lambda x: "ریال" if x=="IRR" else "دلار")
            
            submitted = st.form_submit_button("ثبت دارایی")
            if submitted:
                if not asset_name.strip():
                    st.error("نام دارایی را وارد کنید.")
                elif amount <= 0:
                    st.error("مبلغ باید بزرگتر از صفر باشد.")
                else:
                    data["journals"].append({
                        "id": datetime.now().isoformat(),
                        "asset_name": asset_name.strip(),
                        "amount": amount,
                        "currency": currency,
                        "created_at": datetime.now().isoformat()
                    })
                    st.session_state.data = data
                    save_data_to_github(data)
                    st.success(f"دارایی «{asset_name}» ثبت شد.")
                    st.rerun()
    
    # --- لیست ژورنال‌ها ---
    journals = data.get("journals", [])
    if not journals:
        st.info("هنوز دارایی‌ای ثبت نشده است.")
    else:
        st.subheader("📝 لیست دارایی‌های ثبت‌شده")
        for idx, j in enumerate(journals):
            with st.container(border=True):
                cols = st.columns([3, 2, 2, 2, 1])
                with cols[0]:
                    st.write(f"**{j['asset_name']}**")
                with cols[1]:
                    st.write(f"{j['amount']:,.0f} {'ریال' if j['currency']=='IRR' else 'دلار'}")
                with cols[2]:
                    st.caption("ریالی" if j['currency']=="IRR" else "دلاری")
                with cols[3]:
                    st.caption(j.get("created_at", "")[:10])
                with cols[4]:
                    if st.button("🗑️", key=f"del_{j['id']}", help="حذف"):
                        data["journals"] = [x for x in data["journals"] if x["id"] != j["id"]]
                        st.session_state.data = data
                        save_data_to_github(data)
                        st.rerun()
