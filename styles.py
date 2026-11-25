"""Visual styles for the Streamlit application (kept compatible with FONTS API)."""
from __future__ import annotations

import streamlit as st

from financial_core import get_effective_theme, get_settings

FONTS = {
    "vazirmatn": ("Vazirmatn", "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/webfonts/Vazirmatn-Regular.woff2"),
    "vazir": ("Vazir", "https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/Vazir.woff2"),
    "shabnam": ("Shabnam", "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@v5.0.1/dist/Shabnam.woff2"),
    "sahel": ("Sahel", "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@v3.4.0/dist/Sahel.woff2"),
    "samim": ("Samim", "https://cdn.jsdelivr.net/gh/rastikerdar/samim-font@v4.0.5/dist/Samim.woff2"),
    "tanha": ("Tanha", "https://cdn.jsdelivr.net/gh/rastikerdar/tanha-font@v1.0.0/dist/Tanha.woff2"),
    "estedad": ("Estedad", "https://cdn.jsdelivr.net/gh/aminabedi68/Estedad@v7.3/fonts/webfonts/Estedad-Regular.woff2"),
}


def inject_login():
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
    <style>
    @font-face{font-family:Vazirmatn;src:url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/webfonts/Vazirmatn-Regular.woff2') format('woff2')}
    html,body,[class*="css"],.stApp{font-family:Vazirmatn,Tahoma,sans-serif!important}
    .stApp{direction:rtl;background:radial-gradient(circle at 50% 10%,#eff6ff 0,#f8fafc 48%,#fff 100%)}
    [data-testid="stSidebar"],header[data-testid="stHeader"]{display:none}
    [data-testid="stMainBlockContainer"]{max-width:760px;padding-top:1rem}
    .stButton button{border-radius:12px;background:#2563eb;color:white;border:0;font-weight:700}
    .stTextInput input{direction:ltr;text-align:center;border-radius:12px}
    </style>
    """, unsafe_allow_html=True)


def _font_faces(data) -> str:
    css = []
    for key, (_, url) in FONTS.items():
        css.append(f"@font-face{{font-family:'{key}';src:url('{url}') format('woff2');font-display:swap}}")
    custom = get_settings(data).get("custom_fonts", {})
    for key, info in custom.items():
        if info.get("data"):
            css.append(
                f"@font-face{{font-family:'{key}';src:url(data:{info.get('mime', 'font/ttf')};base64,{info['data']}) "
                f"format('{info.get('format', 'truetype')}');font-display:swap}}"
            )
    return "\n".join(css)


def inject_app(data):
    settings = get_settings(data)
    font = settings["font"] if settings["font"] in FONTS or settings["font"] in settings["custom_fonts"] else "vazirmatn"
    dark = get_effective_theme(data) == "dark"
    colors = {
        "bg": "#0d1117" if dark else "#f5f7fb",
        "surface": "#161b22" if dark else "#ffffff",
        "soft": "#0d1117" if dark else "#f8fafc",
        "text": "#e6edf3" if dark else "#172033",
        "muted": "#8b949e" if dark else "#64748b",
        "border": "#30363d" if dark else "#e2e8f0",
        "primary": "#79a6ff" if dark else "#2563eb",
        "primary_soft": "#172554" if dark else "#eff6ff",
        "input": "#0d1117" if dark else "#ffffff",
    }
    st.markdown(f"""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
    <style>
    {_font_faces(data)}
    :root{{--app-bg:{colors['bg']};--app-surface:{colors['surface']};--app-soft:{colors['soft']};--app-text:{colors['text']};--app-muted:{colors['muted']};--app-border:{colors['border']};--app-primary:{colors['primary']};--app-primary-soft:{colors['primary_soft']};--app-input:{colors['input']};--sidebar-width:20rem}}
    html,body,[class*="css"],.stApp,.stMarkdown,button,input,select,textarea{{font-family:'{font}',Vazirmatn,Tahoma,sans-serif!important}}
    .stApp{{direction:rtl;background:var(--app-bg);color:var(--app-text)}}
    [data-testid="stMainBlockContainer"]{{max-width:1540px;padding:1.2rem 2rem 4rem;direction:rtl}}
    [data-testid="stAppViewContainer"]{{background:var(--app-bg);color:var(--app-text)}}
    [data-testid="stHeader"]{{background:transparent}}
    h1,h2,h3,h4,h5,h6,p,label,.stMarkdown{{color:var(--app-text)}}
    h1{{font-size:1.85rem!important;font-weight:800!important;letter-spacing:-.02em}}
    h2{{font-size:1.4rem!important;font-weight:800!important}}
    h3{{font-size:1.08rem!important;font-weight:750!important}}
    small,.stCaption,[data-testid="stCaptionContainer"]{{color:var(--app-muted)!important}}
    section[data-testid="stSidebar"]{{right:0;left:auto;direction:rtl;background:var(--app-surface);border-left:1px solid var(--app-border);border-right:0;box-shadow:-8px 0 30px rgba(15,23,42,.04)}}
    section[data-testid="stSidebar"]>div{{right:0;left:auto}}
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{{direction:rtl}}
    section[data-testid="stSidebar"] .stMarkdown{{text-align:right}}
    [data-testid="stSidebarCollapseButton"],[data-testid="collapsedControl"]{{right:auto!important;left:.4rem}}
    @media(min-width:992px){{
      [data-testid="stAppViewContainer"]{{margin-right:20rem;margin-left:0}}
      [data-testid="stHeader"]{{right:20rem;left:0}}
      section[data-testid="stSidebar"][aria-expanded="false"]~[data-testid="stAppViewContainer"]{{margin-right:0}}
    }}
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]){{
      background:var(--app-surface);border:1px solid var(--app-border)!important;border-radius:16px;box-shadow:0 5px 18px rgba(15,23,42,.035)
    }}
    .stButton button,.stDownloadButton button,.stFormSubmitButton button{{
      border-radius:10px;border:1px solid var(--app-border);background:var(--app-surface);color:var(--app-text);font-weight:650;min-height:2.45rem;transition:.16s ease
    }}
    .stButton button:hover,.stDownloadButton button:hover,.stFormSubmitButton button:hover{{border-color:var(--app-primary);color:var(--app-primary);background:var(--app-primary-soft)}}
    .stFormSubmitButton button[kind="primary"],.stButton button[kind="primary"]{{background:#2563eb;color:#fff;border-color:#2563eb}}
    .stTextInput input,.stNumberInput input,.stSelectbox div[data-baseweb="select"]>div,.stTextArea textarea,.stDateInput input,.stTimeInput input{{
      background:var(--app-input)!important;color:var(--app-text)!important;border-color:var(--app-border)!important;border-radius:10px!important
    }}
    .stTextInput input,.stNumberInput input{{direction:ltr;text-align:right}}
    [data-testid="stMetric"]{{background:var(--app-surface);border:1px solid var(--app-border);border-radius:14px;padding:13px 15px;box-shadow:0 4px 14px rgba(15,23,42,.03)}}
    [data-testid="stMetricLabel"],[data-testid="stMetricLabel"] *{{color:var(--app-muted)!important;font-size:.78rem!important}}
    [data-testid="stMetricValue"],[data-testid="stMetricValue"] *{{color:var(--app-text)!important;font-size:1.25rem!important;font-weight:750!important}}
    [data-testid="stMetricDelta"],[data-testid="stMetricDelta"] *{{font-size:.72rem!important}}
    [data-testid="stExpander"]{{border:1px solid var(--app-border)!important;border-radius:12px!important;background:var(--app-surface);overflow:hidden}}
    [data-testid="stExpander"] summary{{background:var(--app-surface);color:var(--app-text)}}
    [data-testid="stTabs"] [data-baseweb="tab-list"]{{gap:4px;direction:rtl;flex-wrap:wrap}}
    [data-testid="stTabs"] button{{color:var(--app-muted);font-size:.78rem}}
    [data-testid="stTabs"] button[aria-selected="true"]{{color:var(--app-primary)}}
    [data-testid="stRadio"]>div{{direction:rtl;flex-wrap:wrap;gap:7px}}
    [data-testid="stRadio"] label{{background:var(--app-surface);border:1px solid var(--app-border);padding:5px 11px;border-radius:9px}}
    [data-testid="stAlert"]{{direction:rtl;border-radius:12px}}
    [data-testid="stDataFrame"],.stPlotlyChart{{direction:ltr}}
    .stPlotlyChart{{border:1px solid var(--app-border);border-radius:14px;background:var(--app-surface);padding:5px;overflow:hidden}}
    .stDivider{{border-color:var(--app-border)}}
    .nav-pills [data-testid="stPills"]{{direction:rtl}}
    [data-testid="stPills"] button{{border-radius:10px;background:var(--app-surface);border:1px solid var(--app-border);color:var(--app-muted)}}
    [data-testid="stPills"] button[aria-pressed="true"]{{background:var(--app-primary-soft);border-color:var(--app-primary);color:var(--app-primary);font-weight:700}}
    .sidebar-brand{{display:flex;align-items:center;gap:10px;padding:2px 3px 12px}}
    .sidebar-brand-icon{{display:grid;place-items:center;width:40px;height:40px;border-radius:13px;background:linear-gradient(145deg,#2563eb,#14b8a6);color:white;font-size:1.2rem}}
    .sidebar-brand-title{{font-size:1.05rem;font-weight:800;line-height:1.4}}
    .sidebar-brand-sub{{font-size:.65rem;color:var(--app-muted)}}
    .section-caption{{font-size:.78rem;color:var(--app-muted);margin:3px 0 8px}}
    .danger-zone{{border:1px solid #ef444455!important}}
    @media(max-width:768px){{[data-testid="stMainBlockContainer"]{{padding:.8rem .7rem 3rem}}[data-testid="stMetricValue"],[data-testid="stMetricValue"] *{{font-size:1rem!important}}}}
    </style>
    """, unsafe_allow_html=True)
