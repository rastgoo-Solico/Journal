"""Entry point: streamlit run streamlit_app.py

This is the continuation of the original Streamlit application. It deliberately
uses the existing data.json schema and GitHub Contents API, not PostgreSQL.
"""
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="داشبورد مالی", layout="wide", initial_sidebar_state="expanded")

from analysis_pages import render_asset_page, render_gold_page
from financial_core import (
    APP_PASSWORD, AUTH_TOKEN, DATA_FILE, DEFAULT_NAV_ORDER, GITHUB_REPO, GITHUB_TOKEN,
    NAV_EMOJI, NAV_LABELS, asset_overview_emoji, check_github_status, get_current_usd_rate,
    get_effective_theme, get_settings, load_all, load_github_file, migrate_data, save_all,
    save_local_file, today_jalali_str,
)
from settings_panel import render_settings_panel
from streamlit_pages import render_journal, render_monthly_returns_page, render_overview, render_usd_page
from styles import inject_app, inject_login
from synthetic_page import render_synthetic_page


if not APP_PASSWORD:
    inject_login()
    st.error("APP_PASSWORD در Secrets تنظیم نشده است.")
    st.markdown("در Streamlit Cloud از **Settings → Secrets** مقدار `APP_PASSWORD` و در صورت نیاز `GITHUB_TOKEN` و `GITHUB_REPO` را وارد کنید.")
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    query_auth = st.query_params.get("auth")
    if query_auth and query_auth == AUTH_TOKEN:
        st.session_state.authenticated = True

if not st.session_state.authenticated:
    inject_login()
    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown("""
        <div style="text-align:center;padding:24px 0 16px;direction:rtl">
          <div style="font-size:3.2rem;line-height:1;margin-bottom:8px">🔐</div>
          <h1 style="margin:0;color:#1e40af">داشبورد مالی</h1>
          <p style="color:#6b7280;margin-top:8px">لطفاً رمز عبور را وارد کنید</p>
        </div>""", unsafe_allow_html=True)
        with st.container(border=True):
            with st.form("login_form"):
                password = st.text_input("رمز", type="password", placeholder="••••••••", label_visibility="collapsed")
                if st.form_submit_button("🚪 ورود", use_container_width=True):
                    if password == APP_PASSWORD:
                        st.session_state.authenticated = True
                        st.query_params["auth"] = AUTH_TOKEN
                        st.rerun()
                    st.error("❌ رمز عبور اشتباه است.")
    st.stop()

if "data" not in st.session_state:
    st.session_state.data = migrate_data(load_all())
data = migrate_data(st.session_state.data)
st.session_state.data = data
data.setdefault("assets", [])
data.setdefault("usd_rates", [])
data.setdefault("gold_funds", [])
data.setdefault("synthetic_pairs", [])
inject_app(data)
settings = get_settings(data)
dark = get_effective_theme(data) == "dark"

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="sidebar-brand-icon"><i class="fa-solid fa-chart-line"></i></div>
      <div><div class="sidebar-brand-title">داشبورد مالی</div><div class="sidebar-brand-sub">تحلیل دارایی، ارز و طلا</div></div>
    </div>""", unsafe_allow_html=True)
    col_date, col_mode, col_logout = st.columns([3, 1, 1])
    col_date.markdown(f"### 🗓️ {today_jalali_str()}")
    if col_mode.button("☀️" if dark else "🌙", key="dark_toggle_btn", help="حالت دستی روز/شب", use_container_width=True):
        data["settings"]["dark_mode"] = not dark
        data["settings"]["auto_theme"] = False
        save_all(data)
        st.rerun()
    if col_logout.button("🚪", key="logout_btn", help="خروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.pop("data", None)
        st.query_params.clear()
        st.rerun()
    st.divider()
    rate, rate_date = get_current_usd_rate(data)
    if rate:
        st.markdown(f"""
        <div style="background:var(--app-primary-soft);padding:14px 16px;border-radius:12px;border-right:4px solid var(--app-primary);margin-bottom:12px;direction:rtl;text-align:right">
          <div style="font-size:.78rem;color:var(--app-muted)">💵 نرخ فعلی دلار</div>
          <div style="font-size:1.45rem;font-weight:750;color:var(--app-primary)">{rate:,.0f}<span style="font-size:.8rem;color:var(--app-muted)"> ریال</span></div>
          <div style="font-size:.68rem;color:var(--app-muted)">آخرین: {rate_date}</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("💡 هنوز نرخی ثبت نشده.")

render_settings_panel(data)

with st.sidebar:
    st.divider()
    st.markdown("**💾 وضعیت ذخیره‌سازی**")
    if data.get("last_saved"):
        st.caption(f"✅ آخرین ذخیره: {data.get('last_saved_jalali', '—')}")
    else:
        st.caption("⚠️ هنوز ذخیره نشده")
    github_status, github_message = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
    col1, col2 = st.columns(2)
    col1.caption(f"{'✅' if DATA_FILE.exists() else '❌'} محلی")
    col2.caption(f"{'✅' if github_status == 'ok' else '❌'} GitHub")
    if github_status != "ok":
        st.caption(f"وضعیت GitHub: {github_message}")
    if st.button("💾 ذخیره فوری + تأیید", use_container_width=True, key="force_save"):
        if save_all(data):
            st.rerun()
    with st.expander("🔍 تأیید و همگام‌سازی"):
        if st.button("🔍 تأیید نسخهٔ GitHub", use_container_width=True):
            from financial_core import verify_github_save
            verified, message, sha = verify_github_save(data)
            (st.success if verified else st.error)(f"{message} {('· SHA '+sha) if sha else ''}")
        if st.button("🔄 بارگذاری از GitHub", use_container_width=True):
            github_data = load_github_file()
            if github_data:
                st.session_state.data = migrate_data(github_data)
                save_local_file(st.session_state.data)
                st.success("بارگذاری شد")
                st.rerun()
            st.error("بارگذاری ناموفق بود.")
    with st.expander("📥 پشتیبان / 📤 بازیابی"):
        st.download_button("📥 دانلود JSON", data=json.dumps(data, ensure_ascii=False, indent=2),
                           file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", use_container_width=True)
        uploaded = st.file_uploader("📤 آپلود JSON", type=["json"], key="backup_uploader")
        if uploaded is not None:
            try:
                imported = migrate_data(json.loads(uploaded.read().decode("utf-8")))
                st.caption(f"دارایی: {len(imported.get('assets', []))} · صندوق: {len(imported.get('gold_funds', []))} · جفت: {len(imported.get('synthetic_pairs', []))}")
                if st.button("✅ اعمال فایل پشتیبان", use_container_width=True):
                    st.session_state.data = imported
                    save_all(imported)
                    st.rerun()
            except Exception as exc:
                st.error(f"فایل معتبر نیست: {exc}")

# Ordered main tabs plus individual asset pages. Settings now lives in the right panel.
order = [key for key in settings["nav_order"] if key in DEFAULT_NAV_ORDER]
order += [key for key in DEFAULT_NAV_ORDER if key not in order]
nav_options = order + [f"asset_{asset['id']}" for asset in data["assets"]]
nav_labels = {key: f"{NAV_EMOJI[key]} {NAV_LABELS[key]}" for key in DEFAULT_NAV_ORDER}
for asset in data["assets"]:
    nav_labels[f"asset_{asset['id']}"] = f"{asset_overview_emoji(asset)} {asset['name']}"

if "nav_version" not in st.session_state:
    st.session_state.nav_version = 0
if "pending_nav" in st.session_state:
    pending = st.session_state.pop("pending_nav")
    if pending in nav_options:
        st.session_state.nav_version += 1
        st.session_state[f"nav_pills_v{st.session_state.nav_version}"] = pending
widget_key = f"nav_pills_v{st.session_state.nav_version}"
if widget_key not in st.session_state or st.session_state[widget_key] not in nav_options:
    st.session_state[widget_key] = "overview"

st.markdown('<div class="nav-pills">', unsafe_allow_html=True)
if hasattr(st, "pills"):
    selected = st.pills("ناوبری", options=nav_options, format_func=lambda key: nav_labels.get(key, key),
                        selection_mode="single", label_visibility="collapsed", key=widget_key)
    if selected is None:
        selected = st.session_state[widget_key]
else:
    selected = st.radio("ناوبری", options=nav_options, format_func=lambda key: nav_labels.get(key, key),
                        horizontal=True, label_visibility="collapsed", key=f"{widget_key}_radio")
st.markdown("</div>", unsafe_allow_html=True)

if selected == "overview":
    render_overview(data)
elif selected == "journal":
    render_journal(data)
elif selected == "usd":
    render_usd_page(data)
elif selected == "gold":
    render_gold_page(data)
elif selected == "synthetic":
    render_synthetic_page(data)
elif selected == "monthly":
    render_monthly_returns_page(data)
elif selected.startswith("asset_"):
    asset_id = selected.replace("asset_", "", 1)
    asset = next((item for item in data["assets"] if item["id"] == asset_id), None)
    if asset is None:
        st.error("دارایی یافت نشد.")
    else:
        render_asset_page(data, asset)
