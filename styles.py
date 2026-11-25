"""استایل‌ها، فونت‌ها و تم برنامهٔ Streamlit (نسخهٔ توسعه‌یافتهٔ داشبورد مالی)."""
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

FONTS = {
    "vazirmatn": ("Vazirmatn", "https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&display=swap"),
    "sahel": ("Sahel", "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@v3.4.0/dist/font-face.css"),
    "shabnam": ("Shabnam", "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@v5.0.1/dist/font-face.css"),
    "iran-sans": ("IRANSans", ""),
    "tahoma": ("Tahoma", ""),
}


def _theme_palette(dark: bool) -> dict:
    if dark:
        return {
            "bg": "#0d1420", "surface": "#121c2a", "soft": "#172334",
            "text": "#e8eef7", "muted": "#91a0b5", "border": "#243348",
            "primary": "#6f9aff", "primary_soft": "#1c3156",
        }
    return {
        "bg": "#f4f7fb", "surface": "#ffffff", "soft": "#f8fafd",
        "text": "#182230", "muted": "#78869a", "border": "#e8edf4",
        "primary": "#326be8", "primary_soft": "#edf3ff",
    }


def auto_theme(settings: dict, now: datetime | None = None) -> bool:
    """آیا الان باید حالت شب فعال باشد؟ (بر اساس ساعت تهران)"""
    if not settings.get("auto_theme", False):
        return bool(settings.get("dark_mode", False))
    now = now or datetime.now(ZoneInfo("Asia/Tehran"))
    try:
        start_h, start_m = [int(part) for part in str(settings.get("day_start", "07:00")).split(":")]
        end_h, end_m = [int(part) for part in str(settings.get("night_start", "19:00")).split(":")]
    except (TypeError, ValueError):
        start_h, start_m, end_h, end_m = 7, 0, 19, 0
    current = now.hour * 60 + now.minute
    start = start_h * 60 + start_m
    end = end_h * 60 + end_m
    day_duration = (end - start) % 1440
    elapsed = (current - start) % 1440
    return not (day_duration > 0 and elapsed < day_duration)


def _base_css(dark: bool) -> str:
    p = _theme_palette(dark)
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"], .stApp, .stMarkdown, .stText, .stButton, .stSelectbox,
    .stTextInput, .stNumberInput, input, textarea, select, button {{
        font-family: 'Vazirmatn', Tahoma, sans-serif !important;
        direction: rtl;
    }}
    .stApp {{ background: {p['bg']}; color: {p['text']}; }}
    [data-testid="stHeader"] {{ background: transparent; }}
    .block-container {{ padding-top: 2rem; max-width: 1300px; }}
    /* پنل سمت راست: سایدبار Streamlit به سمت راست منتقل می‌شود */
    section[data-testid="stSidebar"] {{
        right: 0 !important; left: auto !important;
        border-left: 1px solid {p['border']}; border-right: none !important;
        background: {p['surface']} !important;
    }}
    section[data-testid="stSidebar"] > div {{ direction: rtl; }}
    [data-testid="stSidebarCollapsedControl"] {{ right: 0.6rem; left: auto; }}
    @media (min-width: 990px) {{
        section.main, [data-testid="stAppViewContainer"] > .main {{
            margin-right: 21rem; margin-left: 0;
        }}
        [data-testid="stSidebar"] {{ width: 21rem !important; }}
    }}
    h1, h2, h3, h4 {{ color: {p['text']} !important; font-weight: 800 !important; }}
    p, span, label, div {{ color: {p['text']}; }}
    .stCaption, [data-testid="stCaptionContainer"] * {{ color: {p['muted']} !important; }}
    div[data-testid="stMetric"] {{
        background: {p['surface']}; border: 1px solid {p['border']};
        border-radius: 14px; padding: 14px 16px;
    }}
    div[data-testid="stMetricLabel"] * {{ font-size: 0.78rem !important; color: {p['muted']} !important; }}
    div[data-testid="stMetricValue"] * {{ font-size: 1.25rem !important; font-weight: 700 !important; color: {p['text']} !important; }}
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
        border-radius: 10px !important; border: 1px solid {p['border']} !important;
        background: {p['surface']} !important; color: {p['text']} !important;
        font-size: 0.82rem !important; font-weight: 600 !important;
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{
        border-color: {p['primary']} !important; color: {p['primary']} !important;
        background: {p['primary_soft']} !important;
    }}
    .stButton > button[kind="primary"] {{
        background: {p['primary']} !important; color: #fff !important; border-color: {p['primary']} !important;
    }}
    input, textarea, [data-baseweb="select"] > div {{
        background: {p['surface']} !important; color: {p['text']} !important;
        border-color: {p['border']} !important; border-radius: 10px !important;
    }}
    [data-testid="stExpander"] {{
        background: {p['surface']}; border: 1px solid {p['border']} !important; border-radius: 12px;
    }}
    [data-testid="stTabs"] button[role="tab"] {{ color: {p['muted']}; }}
    [data-testid="stTabs"] button[aria-selected="true"] {{ color: {p['primary']} !important; }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.55rem; }}
    .fin-card {{
        background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 14px;
        padding: 14px 16px; direction: rtl; text-align: right;
    }}
    .fin-chip {{
        display: inline-block; padding: 3px 9px; border-radius: 8px;
        background: {p['primary_soft']}; color: {p['primary']}; font-size: 0.72rem; font-weight: 700;
    }}
    .fin-alert {{
        padding: 11px 13px; border-radius: 11px; font-size: 0.8rem; direction: rtl;
        border: 1px solid {p['border']}; background: {p['soft']};
    }}
    .fin-table {{ width: 100%; border-collapse: collapse; direction: rtl; font-size: 0.82rem; }}
    .fin-table th {{ background: {p['soft']}; color: {p['muted']}; padding: 9px 11px; text-align: right; }}
    .fin-table td {{ padding: 8px 11px; border-bottom: 1px solid {p['border']}; color: {p['text']}; }}
    .login-card {{ max-width: 420px; margin: 6vh auto; background: {p['surface']}; border: 1px solid {p['border']};
        border-radius: 18px; padding: 26px; direction: rtl; text-align: right; }}
    </style>
    """


def inject_login() -> None:
    st.markdown(_base_css(False), unsafe_allow_html=True)


def inject_app(data: dict) -> None:
    settings = data.get("settings", {}) if isinstance(data, dict) else {}
    dark = auto_theme(settings)
    st.markdown(_base_css(dark), unsafe_allow_html=True)

