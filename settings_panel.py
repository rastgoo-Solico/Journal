"""Settings rendered inside Streamlit's right-hand sidebar."""
from __future__ import annotations

import base64
import re
from datetime import datetime

import streamlit as st

from financial_core import (
    DEFAULT_NAV_ICONS, DEFAULT_NAV_ORDER, NAV_LABELS, asset_color, asset_icon,
    asset_overview_emoji, check_github_status, get_effective_theme, get_settings,
    load_fa_icons, save_all, verify_github_save,
)
from styles import FONTS


def _persist(data, rerun=True):
    st.session_state.data = data
    save_all(data)
    if rerun:
        st.rerun()


def _all_fonts(data):
    fonts = {key: {"name": name, "builtin": True} for key, (name, _) in FONTS.items()}
    for key, info in get_settings(data)["custom_fonts"].items():
        fonts[key] = {"name": info.get("display_name", key), "builtin": False}
    return fonts


def _theme_settings(data):
    settings = get_settings(data)
    with st.form("sidebar_theme_settings"):
        auto = st.checkbox("تغییر خودکار روز/شب بر اساس ساعت", value=settings["auto_theme"])
        col1, col2 = st.columns(2)
        day_value = datetime.strptime(settings["day_start"], "%H:%M").time()
        night_value = datetime.strptime(settings["night_start"], "%H:%M").time()
        day_start = col1.time_input("شروع روز", value=day_value)
        night_start = col2.time_input("شروع شب", value=night_value)
        manual = st.radio("پوسته در حالت دستی", ["light", "dark"], index=1 if settings["dark_mode"] else 0,
                          format_func=lambda value: "☀️ روز" if value == "light" else "🌙 شب", horizontal=True, disabled=auto)
        st.caption(f"پوستهٔ مؤثر اکنون: {'🌙 شب' if get_effective_theme(data) == 'dark' else '☀️ روز'}")
        if st.form_submit_button("💾 ذخیرهٔ زمان‌بندی", use_container_width=True):
            if day_start == night_start:
                st.error("ساعت شروع روز و شب نباید یکسان باشد.")
            else:
                data["settings"].update({
                    "auto_theme": auto, "day_start": day_start.strftime("%H:%M"),
                    "night_start": night_start.strftime("%H:%M"), "dark_mode": manual == "dark",
                })
                _persist(data)


def _font_settings(data):
    settings = get_settings(data)
    fonts = _all_fonts(data)
    keys = list(fonts)
    current = settings["font"] if settings["font"] in keys else "vazirmatn"
    selected = st.selectbox("فونت برنامه", keys, index=keys.index(current), format_func=lambda key: fonts[key]["name"] + (" (سفارشی)" if not fonts[key]["builtin"] else ""))
    st.markdown(f'<div style="font-family:{selected},Tahoma;border:1px solid var(--app-border);border-radius:10px;padding:12px;text-align:center">داشبورد مالی — ۱۲۳۴۵</div>', unsafe_allow_html=True)
    if st.button("💾 اعمال فونت", use_container_width=True):
        data["settings"]["font"] = selected
        _persist(data)
    with st.expander("📤 بارگذاری فونت سفارشی"):
        with st.form("sidebar_font_upload", clear_on_submit=True):
            uploaded = st.file_uploader("TTF, OTF, WOFF, WOFF2", type=["ttf", "otf", "woff", "woff2"])
            display_name = st.text_input("نام نمایشی")
            if st.form_submit_button("بارگذاری", use_container_width=True):
                if uploaded is None:
                    st.error("فایل انتخاب کنید.")
                elif uploaded.size > 10 * 1024 * 1024:
                    st.error("حجم بیش از ۱۰ مگابایت است.")
                else:
                    content = uploaded.read()
                    extension = uploaded.name.lower().rsplit(".", 1)[-1]
                    formats = {"ttf": "truetype", "otf": "opentype", "woff": "woff", "woff2": "woff2"}
                    mimes = {"ttf": "font/ttf", "otf": "font/otf", "woff": "font/woff", "woff2": "font/woff2"}
                    base_name = uploaded.name.rsplit(".", 1)[0]
                    safe = re.sub(r"[^a-z0-9_]", "_", base_name.lower())[:40] or "font"
                    key = f"custom_{safe}"
                    counter = 1
                    while key in data["settings"].setdefault("custom_fonts", {}):
                        counter += 1
                        key = f"custom_{safe}_{counter}"
                    data["settings"]["custom_fonts"][key] = {
                        "display_name": (display_name.strip() or base_name)[:60], "data": base64.b64encode(content).decode(),
                        "format": formats.get(extension, "truetype"), "mime": mimes.get(extension, "font/ttf"),
                        "filename": uploaded.name, "size_bytes": len(content), "uploaded_at": datetime.now().isoformat(),
                    }
                    _persist(data)
        for key, info in list(settings["custom_fonts"].items()):
            col1, col2 = st.columns([4, 1])
            col1.caption(f"{info.get('display_name', key)} · {info.get('size_bytes', 0)//1024:,} KB")
            if col2.button("🗑️", key=f"delete_font_{key}"):
                del data["settings"]["custom_fonts"][key]
                if data["settings"].get("font") == key:
                    data["settings"]["font"] = "vazirmatn"
                _persist(data)


def _nav_order_settings(data):
    settings = get_settings(data)
    order = [key for key in settings["nav_order"] if key in DEFAULT_NAV_ORDER]
    order += [key for key in DEFAULT_NAV_ORDER if key not in order]
    st.caption("با دکمه‌های بالا و پایین، ترتیب سربرگ‌های اصلی را تغییر دهید. صفحهٔ هر دارایی بعد از سربرگ‌ها قرار می‌گیرد.")
    for index, key in enumerate(order):
        col1, col2, col3 = st.columns([5, 1, 1])
        col1.markdown(f"**{index+1}.** {NAV_LABELS[key]}")
        if col2.button("↑", key=f"nav_up_{key}", disabled=index == 0):
            order[index - 1], order[index] = order[index], order[index - 1]
            data["settings"]["nav_order"] = order
            _persist(data)
        if col3.button("↓", key=f"nav_down_{key}", disabled=index == len(order)-1):
            order[index + 1], order[index] = order[index], order[index + 1]
            data["settings"]["nav_order"] = order
            _persist(data)
    if st.button("↩️ ترتیب پیش‌فرض", use_container_width=True):
        data["settings"]["nav_order"] = DEFAULT_NAV_ORDER.copy()
        _persist(data)


def _icon_settings(data):
    icons = load_fa_icons()
    classes = [icon["class"] for icon in icons]
    labels = {icon["class"]: f"{icon['label']} ({icon['class']})" for icon in icons}
    st.caption("برای جستجوی آیکون، داخل فهرست تایپ کنید.")
    for key in DEFAULT_NAV_ORDER:
        config = get_settings(data)["nav_icons"].get(key, DEFAULT_NAV_ICONS[key])
        with st.expander(f"آیکون {NAV_LABELS[key]}"):
            current_icon = config["icon"] if config["icon"] in classes else classes[0]
            selected = st.selectbox("آیکون", classes, index=classes.index(current_icon), format_func=lambda value: labels.get(value, value), key=f"nav_icon_select_{key}")
            color = st.color_picker("رنگ", value=config["color"], key=f"nav_icon_color_{key}")
            if st.button("💾 ذخیره", key=f"save_nav_icon_{key}", use_container_width=True):
                data["settings"].setdefault("nav_icons", {})[key] = {"icon": selected, "color": color}
                _persist(data)
    for asset in data.get("assets", []):
        with st.expander(f"دارایی: {asset['name']}"):
            current = asset_icon(asset)
            selected = st.selectbox("آیکون دارایی", classes, index=classes.index(current) if current in classes else 0,
                                    format_func=lambda value: labels.get(value, value), key=f"asset_icon_select_{asset['id']}")
            color = st.color_picker("رنگ دارایی", value=asset_color(asset), key=f"asset_color_{asset['id']}")
            emoji = st.text_input("ایموجی نمای کلی (خالی = خودکار)", value=asset.get("overview_emoji", ""), max_chars=8, key=f"asset_emoji_{asset['id']}")
            if st.button("💾 ذخیرهٔ دارایی", key=f"save_asset_style_{asset['id']}", use_container_width=True):
                asset.update({"icon": selected, "color": color, "overview_emoji": emoji.strip()})
                _persist(data)


def render_settings_panel(data):
    with st.sidebar.expander("⚙️ تنظیمات برنامه", expanded=False):
        tabs = st.tabs(["پوسته", "فونت", "ترتیب سربرگ", "آیکون‌ها"])
        with tabs[0]:
            _theme_settings(data)
        with tabs[1]:
            _font_settings(data)
        with tabs[2]:
            _nav_order_settings(data)
        with tabs[3]:
            _icon_settings(data)
