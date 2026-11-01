"""
استایل‌های داشبورد مالی — نسخه جدا شده
"""
import streamlit as st

# ================== فونت‌های داخلی (CDN) ==================
FONTS = {
    "vazirmatn": ("Vazirmatn", "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css"),
    "sahel":     ("Sahel",    "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@v3.4.0/dist/font-face.css"),
    "samim":     ("Samim",    "https://cdn.jsdelivr.net/gh/rastikerdar/samim-font@v4.0.5/dist/font-face.css"),
    "shabnam":   ("Shabnam",  "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@v5.0.1/dist/font-face.css"),
    "markazi":   ("Markazi Text", "https://fonts.googleapis.com/css2?family=Markazi+Text:wght@400;700&display=swap"),
    "noto":      ("Noto Naskh Arabic", "https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;700&display=swap"),
}

# ================== CDN ثابت‌ها ==================
_FA_CDN = "@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');"

# ================== CSS اصلی (با placeholder __FONT__) ==================
_MAIN_CSS = """
* { font-family: '__FONT__', 'Vazirmatn', Tahoma, sans-serif !important; }

/* Font Awesome — بازگرداندن فونت آیکون‌ها */
.fa, .fas, .far, .fal, .fat, .fab, .fad,
.fa-solid, .fa-regular, .fa-brands {
    font-family: "Font Awesome 6 Free", "Font Awesome 6 Brands" !important;
    font-feature-settings: normal !important;
}

/* Material Icons — بازگرداندن فونت آیکون‌های Streamlit */
.material-symbols-rounded, .material-symbols-outlined, .material-symbols-sharp,
.material-icons, .material-icons-round, .material-icons-outlined,
.material-icons-two-tone, .material-icons-sharp,
span[data-testid="stExpanderToggleIcon"],
span[data-testid="stTooltipIcon"],
span[data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    font-feature-settings: 'liga' !important;
}

/* RTL */
.stApp { direction: rtl; }
h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stCaption, .stText {
    text-align: right !important;
}
input, textarea, select {
    direction: rtl !important;
    text-align: right !important;
}
table { direction: rtl !important; }
table th, table td { text-align: right !important; }

/* Layout */
.block-container {
    padding-top: 4.5rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1250px !important;
}
header[data-testid="stHeader"] { z-index: 999 !important; }

/* Sidebar */
section[data-testid="stSidebar"] { direction: rtl !important; }
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label { text-align: right !important; }
section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    font-size: 1.3rem !important;
    white-space: normal !important;
    overflow: visible !important;
    word-break: break-word !important;
}
section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
    width: 100% !important;
}

/* Responsive — Tablet/Mobile */
@media (max-width: 768px) {
    .block-container {
        padding-top: 4rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
        padding-bottom: 2rem !important;
    }
    h1 { font-size: 1.35rem !important; }
    h2 { font-size: 1.1rem !important; }
    h3 { font-size: 0.98rem !important; }
    h4 { font-size: 0.92rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.05rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.78rem !important; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: 100% !important;
    }
    [data-testid="stMainBlockContainer"] .stButton > button { width: 100% !important; }
}
@media (max-width: 400px) {
    .block-container {
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
    }
    h1 { font-size: 1.2rem !important; }
}
"""

# ================== CSS حالت شب ==================
_DARK_CSS = """
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: #0e1117 !important;
    color: #e6edf3 !important;
}
[data-testid="stHeader"] { background-color: #0e1117 !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp label, .stApp .stMarkdown, .stApp .stText,
.stApp li, .stApp small { color: #e6edf3 !important; }
section[data-testid="stSidebar"] { background-color: #161b22 !important; }
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }
.stTextInput input, .stNumberInput input, .stTextArea textarea,
[data-baseweb="select"] > div, [data-baseweb="input"] > div {
    background-color: #21262d !important;
    color: #e6edf3 !important;
    border-color: #30363d !important;
}
[data-testid="stMetric"] {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    padding: 10px;
    border-radius: 8px;
}
[data-testid="stMetricValue"] { color: #e6edf3 !important; }
[data-testid="stMetricLabel"] { color: #8b949e !important; }
[data-testid="stExpander"] {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] p {
    color: #e6edf3 !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #30363d !important;
    background-color: #161b22 !important;
}
.stButton > button {
    background-color: #21262d !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
}
.stButton > button:hover { background-color: #30363d !important; }
[data-testid="stTabs"] [role="tablist"] { background-color: #161b22 !important; }
[data-testid="stTabs"] [role="tab"] { color: #8b949e !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #58a6ff !important; }
[data-testid="stPills"] button { background-color: #21262d !important; color: #e6edf3 !important; }
[data-testid="stPills"] button[aria-checked="true"] {
    background-color: #1f6feb !important;
    color: white !important;
}
[data-testid="stAlert"] { color: #e6edf3 !important; }
hr { border-color: #30363d !important; }
"""

# ================== ساخت بخش‌های داینامیک ==================
def _font_imports_css():
    """@import برای همه فونت‌های CDN"""
    return "\n".join(
        f"@import url('{url}');"
        for _, (_, url) in FONTS.items()
        if url
    )

def _custom_font_faces(custom_fonts):
    """@font-face برای فونت‌های سفارشی (base64)"""
    if not custom_fonts:
        return ""
    parts = []
    for key, info in custom_fonts.items():
        try:
            parts.append(
                f"@font-face {{"
                f" font-family: '{key}';"
                f" src: url(data:{info.get('mime', 'font/ttf')};"
                f"base64,{info['data']})"
                f" format('{info.get('format', 'truetype')}');"
                f" font-weight: normal;"
                f" font-style: normal;"
                f" font-display: swap;"
                f" }}"
            )
        except Exception:
            continue
    return "\n".join(parts)

def _assemble_css(font_family, custom_fonts, dark):
    """ترکیب همه بخش‌های CSS در یک رشته"""
    parts = ["<style>"]
    parts.append(_font_imports_css())
    parts.append(_FA_CDN)
    faces = _custom_font_faces(custom_fonts)
    if faces:
        parts.append(faces)
    parts.append(_MAIN_CSS.replace("__FONT__", font_family))
    if dark:
        parts.append(_DARK_CSS)
    parts.append("</style>")
    return "".join(parts)

# ================== توابع عمومی ==================
def inject_login():
    """CSS صفحه لاگین — Vazirmatn، بدون dark mode"""
    st.markdown(_assemble_css("Vazirmatn", {}, False), unsafe_allow_html=True)

def inject_app(data):
    """CSS برنامه — فونت فعال + فونت‌های سفارشی + حالت شب"""
    settings = data.get("settings") or {}
    font_key = settings.get("font", "vazirmatn")
    custom_fonts = settings.get("custom_fonts", {}) or {}
    dark = bool(settings.get("dark_mode", False))

    if font_key in custom_fonts:
        font_family = font_key
    elif font_key in FONTS:
        font_family = FONTS[font_key][0]
    else:
        font_family = "Vazirmatn"

    st.markdown(_assemble_css(font_family, custom_fonts, dark), unsafe_allow_html=True)
