"""داشبورد مالی — نسخهٔ Streamlit توسعه‌یافته بر پایهٔ کد قبلی.

قابلیت‌های تازه:
  • صفحهٔ «جفت ارز مصنوعی» با نمودار نسبت و مقایسهٔ نرمال‌شده
  • اولویت‌بندی سربرگ‌ها در تنظیمات
  • تنظیمات در پنل سمت راست (سایدبار)
  • حالت روز/شب خودکار بر اساس ساعت ورودی کاربر (قابل خاموش/روشن)
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
from datetime import datetime, timedelta

import jdatetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from styles import FONTS, auto_theme, inject_app, inject_login

DEFAULT_NAV_ICONS = {
    "overview": {"icon": "fa-chart-pie", "color": "#3b82f6"},
    "journal": {"icon": "fa-circle-plus", "color": "#10b981"},
    "assets": {"icon": "fa-wallet", "color": "#3b82f6"},
    "usd": {"icon": "fa-dollar-sign", "color": "#f59e0b"},
    "gold": {"icon": "fa-coins", "color": "#eab308"},
    "synthetic": {"icon": "fa-arrow-right-arrow-left", "color": "#8b5cf6"},
    "monthly": {"icon": "fa-calendar-days", "color": "#ec4899"},
    "settings": {"icon": "fa-gear", "color": "#6b7280"},
}
NAV_LABELS = {
    "overview": "نمای کلی", "journal": "افزودن دارایی", "assets": "دارایی‌ها",
    "usd": "دلار", "gold": "صندوق‌های طلا", "synthetic": "جفت مصنوعی",
    "monthly": "بازده ماهانه", "settings": "تنظیمات",
}
NAV_EMOJI = {
    "overview": "📊", "journal": "➕", "assets": "🧾", "usd": "💵",
    "gold": "🥇", "synthetic": "🔀", "monthly": "📅", "settings": "⚙️",
}
DEFAULT_NAV_ORDER = ["overview", "assets", "usd", "gold", "synthetic", "monthly"]
PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"]

st.set_page_config(page_title="داشبورد مالی", layout="wide", initial_sidebar_state="expanded")

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "S@mnet11970") if hasattr(st, "secrets") else "S@mnet11970"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "") if hasattr(st, "secrets") else ""
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "") if hasattr(st, "secrets") else ""
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"
AUTH_TOKEN = hashlib.sha256((str(APP_PASSWORD) + "_salt_v2_2024").encode()).hexdigest()


# ----------------------------- تاریخ و عدد -----------------------------
def today_jalali_str() -> str:
    return jdatetime.date.today().strftime("%Y/%m/%d")


def iso_to_jalali(iso_str: str, with_time: bool = True) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00")).replace(tzinfo=None)
        j = jdatetime.datetime.fromgregorian(datetime=dt)
        return j.strftime("%Y/%m/%d - %H:%M") if with_time else j.strftime("%Y/%m/%d")
    except Exception:
        return "—"


def parse_jalali(text: str):
    try:
        parts = str(text).strip().replace("-", "/").replace(".", "/").split("/")
        if len(parts) != 3:
            return None
        year, month, day = map(int, parts)
        return jdatetime.date(year, month, day)
    except Exception:
        return None


def jalali_to_gregorian_iso(jdate, time_str: str = "00:00") -> str:
    gregorian = jdate.togregorian()
    return f"{gregorian.strftime('%Y-%m-%d')}T{time_str}:00"


def fmt_num(value) -> str:
    try:
        number = float(value)
        return f"{int(number):,}" if number == int(number) else f"{number:,.2f}"
    except Exception:
        return str(value)


def short_id() -> str:
    return str(int(datetime.now().timestamp() * 1000))


# ----------------------------- ذخیره‌سازی -----------------------------
def _compact_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _decompress(raw: bytes) -> bytes:
    if len(raw) >= 2 and raw[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(raw)
        except Exception:
            return raw
    return raw


def load_local_file():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as handle:
                return json.loads(_decompress(handle.read()).decode("utf-8"))
    except Exception:
        pass
    return None


def save_local_file(data) -> bool:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as handle:
            handle.write(_compact_json(data))
        return True
    except Exception:
        return False


def github_headers() -> dict:
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}


def load_github_file():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        response = requests.get(url, headers=github_headers(), timeout=20)
        if response.status_code != 200:
            return None
        info = response.json()
        content = info.get("content", "")
        if content:
            raw = base64.b64decode(content)
        else:
            download = info.get("download_url") or f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_FILE_PATH}"
            fallback = requests.get(download, timeout=30)
            if fallback.status_code != 200:
                return None
            raw = fallback.content
        return json.loads(_decompress(raw).decode("utf-8"))
    except Exception:
        return None


def save_github_file(data):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GitHub تنظیم نشده"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    sha = None
    try:
        response = requests.get(url, headers=github_headers(), timeout=15)
        if response.status_code == 200:
            sha = response.json().get("sha")
    except Exception as exc:
        return False, f"خطای شبکه: {str(exc)[:50]}"
    payload = {
        "message": f"update {today_jalali_str()} {datetime.now().strftime('%H:%M')}",
        "content": base64.b64encode(_compact_json(data).encode("utf-8")).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    try:
        response = requests.put(url, headers=github_headers(), json=payload, timeout=30)
        if response.status_code in (200, 201):
            return True, ""
        return False, f"HTTP {response.status_code}"
    except Exception as exc:
        return False, f"خطای شبکه: {str(exc)[:50]}"


# ----------------------------- مهاجرت و بارگذاری -----------------------------
def default_settings() -> dict:
    return {
        "font": "vazirmatn",
        "nav_icons": DEFAULT_NAV_ICONS.copy(),
        "custom_fonts": {},
        "dark_mode": False,
        "auto_theme": True,
        "day_start": "07:00",
        "night_start": "19:00",
        "nav_order": DEFAULT_NAV_ORDER.copy(),
    }


def migrate_data(data) -> dict:
    if not isinstance(data, dict) or not data:
        return {"assets": [], "usd_rates": [], "gold_funds": [], "synthetic_pairs": [], "settings": default_settings()}
    data.setdefault("assets", [])
    data.setdefault("usd_rates", [])
    data.setdefault("gold_funds", [])
    data.setdefault("synthetic_pairs", [])
    settings = data.get("settings") if isinstance(data.get("settings"), dict) else {}
    merged = default_settings()
    merged.update(settings)
    icons = merged.get("nav_icons") if isinstance(merged.get("nav_icons"), dict) else {}
    for key, value in DEFAULT_NAV_ICONS.items():
        icons.setdefault(key, value.copy())
    merged["nav_icons"] = icons
    order = [item for item in (merged.get("nav_order") or []) if item in DEFAULT_NAV_ORDER]
    for item in DEFAULT_NAV_ORDER:
        if item not in order:
            order.append(item)
    merged["nav_order"] = order
    data["settings"] = merged

    # مهاجرت از ساختار قدیمی journals و usd_rate
    if isinstance(data.get("usd_rate"), (int, float)) and data["usd_rate"]:
        data["usd_rates"].append({
            "id": short_id(), "rate": data["usd_rate"], "note": "منتقل‌شده",
            "created_at": datetime.now().isoformat(), "created_at_jalali": today_jalali_str(),
        })
        data.pop("usd_rate", None)
    if isinstance(data.get("journals"), list):
        for journal in data["journals"]:
            asset_id = journal.get("id") or short_id()
            created = journal.get("created_at") or datetime.now().isoformat()
            data["assets"].append({
                "id": asset_id, "name": journal.get("asset_name", "بدون نام"),
                "icon": "fa-folder", "color": "#3b82f6", "overview_emoji": "",
                "currency": journal.get("currency", "IRR"),
                "created_at_gregorian": created,
                "created_at_jalali": iso_to_jalali(created, with_time=False),
                "records": [{
                    "id": asset_id + "_r", "date_gregorian": created,
                    "date_jalali": iso_to_jalali(created, with_time=False),
                    "quantity": journal.get("amount", 0), "unit_price": 1, "note": "منتقل‌شده",
                }],
            })
        data.pop("journals", None)

    seen = set()
    assets = []
    for asset in data["assets"]:
        if asset.get("id") and asset["id"] not in seen:
            seen.add(asset["id"])
            asset.setdefault("currency", "IRR")
            asset.setdefault("color", "#3b82f6")
            asset.setdefault("icon", "fa-folder")
            asset.setdefault("records", [])
            assets.append(asset)
    data["assets"] = assets

    seen_gold = set()
    funds = []
    for fund in data["gold_funds"]:
        if fund.get("id") and fund["id"] not in seen_gold:
            seen_gold.add(fund["id"])
            fund.setdefault("records", [])
            fund.setdefault("icon", "🥇")
            funds.append(fund)
    data["gold_funds"] = funds
    return data


def save_all(data) -> bool:
    now = datetime.now()
    data["last_saved"] = now.isoformat()
    data["last_saved_jalali"] = jdatetime.datetime.fromgregorian(datetime=now).strftime("%Y/%m/%d - %H:%M")
    local_ok = save_local_file(data)
    github_ok, github_error = save_github_file(data)
    if github_ok:
        st.toast("✅ در GitHub و حافظهٔ محلی ذخیره شد", icon="✅")
        return True
    if local_ok:
        st.warning(f"⚠️ فقط محلی ذخیره شد — GitHub: {github_error}")
        return True
    st.error(f"❌ ذخیره‌سازی ناموفق: {github_error}")
    return False


def refresh(data) -> None:
    st.session_state.data = data
    st.rerun()


# ----------------------------- توابع کمکی داده -----------------------------
def latest_record(records):
    if not records:
        return None
    return max(records, key=lambda item: item.get("date_gregorian", ""))


def current_rate(data):
    rates = data.get("usd_rates", [])
    if not rates:
        return None, None
    latest = max(rates, key=lambda item: item.get("created_at", ""))
    return float(latest["rate"]), latest.get("created_at_jalali", "—")


def rate_at(data, date_str: str):
    rate = None
    for item in sorted(data.get("usd_rates", []), key=lambda row: row.get("created_at", "")):
        if item.get("created_at", "")[:10] <= date_str:
            try:
                value = float(item.get("rate", 0) or 0)
                if value > 0:
                    rate = value
            except (TypeError, ValueError):
                continue
        else:
            break
    return rate


def asset_value(asset, rate):
    record = latest_record(asset.get("records", []))
    if not record:
        return 0.0, None
    unit = float(record.get("unit_price", 0) or 0)
    quantity = float(record.get("quantity", 0) or 0)
    if asset.get("currency", "IRR") == "USD":
        return unit * quantity, (unit * quantity) if not rate else unit * quantity
    return unit * quantity, (unit * quantity / rate) if rate else None


def currency_label(currency: str) -> str:
    return "دلار" if currency == "USD" else "ریال"


def get_instruments(data) -> list[dict]:
    instruments = []
    for asset in data.get("assets", []):
        records = [row for row in asset.get("records", []) if float(row.get("unit_price", 0) or 0) > 0]
        if not records:
            continue
        instruments.append({
            "id": f"asset:{asset['id']}", "label": asset.get("name", "بدون نام"),
            "kind": "asset", "color": asset.get("color", "#3b82f6"), "records": records,
            "currency": asset.get("currency", "IRR"),
        })
    for fund in data.get("gold_funds", []):
        records = [row for row in fund.get("records", []) if float(row.get("unit_price", 0) or 0) > 0]
        if not records:
            continue
        instruments.append({
            "id": f"gold:{fund['id']}", "label": f"{fund.get('icon', '🥇')} {fund['name']}",
            "kind": "gold", "color": "#eab308", "records": records, "currency": "IRR",
        })
    if data.get("usd_rates"):
        instruments.append({
            "id": "usd", "label": "دلار آزاد", "kind": "usd", "color": "#f59e0b",
            "records": data["usd_rates"], "currency": "IRR",
        })
    return instruments


def price_history(data, instrument_id: str) -> list[tuple[str, float]]:
    kind, _, raw_id = instrument_id.partition(":")
    rows: list[tuple[str, float]] = []
    if instrument_id == "usd":
        for item in data.get("usd_rates", []):
            rate = float(item.get("rate", 0) or 0)
            if rate > 0:
                rows.append((item.get("created_at", "")[:10], rate))
    elif kind == "gold":
        fund = next((item for item in data.get("gold_funds", []) if item["id"] == raw_id), None)
        for record in (fund or {}).get("records", []):
            price = float(record.get("unit_price", 0) or 0)
            if price > 0:
                rows.append((record.get("date_gregorian", "")[:10], price))
    else:
        asset = next((item for item in data.get("assets", []) if item["id"] == raw_id), None)
        for record in (asset or {}).get("records", []):
            unit = float(record.get("unit_price", 0) or 0)
            if unit <= 0:
                continue
            rate = rate_at(data, record.get("date_gregorian", "")[:10])
            price = unit if (asset or {}).get("currency", "IRR") != "USD" else unit * (rate or 0)
            if price > 0:
                rows.append((record.get("date_gregorian", "")[:10], price))
    return sorted(rows, key=lambda item: item[0])


def _price_on(history: list[tuple[str, float]], date_str: str):
    value = None
    for date, price in history:
        if date <= date_str:
            value = price
        else:
            break
    return value


def build_pair_series(data, left_id: str, right_id: str) -> pd.DataFrame:
    left = price_history(data, left_id)
    right = price_history(data, right_id)
    dates = sorted({date for date, _ in left} | {date for date, _ in right})
    rows = []
    for date in dates:
        left_price = _price_on(left, date)
        right_price = _price_on(right, date)
        if not left_price or not right_price or left_price <= 0 or right_price <= 0:
            continue
        rows.append({"date": date, "left": left_price, "right": right_price, "ratio": left_price / right_price})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    base = frame.iloc[0]
    frame["left_index"] = frame["left"] / base["left"] * 100
    frame["right_index"] = frame["right"] / base["right"] * 100
    frame["ratio_index"] = frame["ratio"] / base["ratio"] * 100
    frame["label"] = frame["date"].map(lambda value: iso_to_jalali(value + "T00:00:00", with_time=False))
    return frame


def chart_layout(fig, dark: bool, height: int = 360):
    fig.update_layout(
        height=height,
        font={"family": "Vazirmatn, Tahoma", "size": 12, "color": "#e6edf3" if dark else "#1f2937"},
        paper_bgcolor="rgba(0,0,0,0)" if dark else "white",
        plot_bgcolor="rgba(0,0,0,0)" if dark else "white",
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.25, "xanchor": "center", "x": 0.5},
        margin={"t": 30, "b": 20, "l": 8, "r": 8},
        hovermode="x unified",
    )
    return fig


def render_table(frame: pd.DataFrame) -> None:
    st.markdown(frame.to_html(index=False, escape=False, classes="fin-table"), unsafe_allow_html=True)


# ----------------------------- تحلیل دارایی -----------------------------
def asset_analysis(data, asset) -> pd.DataFrame:
    rows = []
    for record in sorted(asset.get("records", []), key=lambda item: item.get("date_gregorian", "")):
        date_str = record.get("date_gregorian", "")[:10]
        rate = rate_at(data, date_str)
        unit = float(record.get("unit_price", 0) or 0)
        quantity = float(record.get("quantity", 0) or 0)
        if unit <= 0 or not rate:
            continue
        unit_irr = unit if asset.get("currency", "IRR") != "USD" else unit * rate
        unit_usd = unit if asset.get("currency", "IRR") == "USD" else unit / rate
        rows.append({
            "id": record.get("id"), "date": date_str, "label": iso_to_jalali(date_str + "T00:00:00", False),
            "quantity": quantity, "unit": unit, "unit_irr": unit_irr, "unit_usd": unit_usd,
            "rate": rate, "value_irr": unit_irr * quantity, "usd_return": 0.0,
            "irr_index": 100.0, "usd_index": 100.0, "rate_index": 100.0,
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["irr_index"] = frame["unit_irr"] / frame["unit_irr"].iloc[0] * 100
    frame["usd_index"] = frame["unit_usd"] / frame["unit_usd"].iloc[0] * 100
    frame["rate_index"] = frame["rate"] / frame["rate"].iloc[0] * 100
    frame["usd_return"] = frame["usd_index"] - 100
    return frame


def render_asset_detail(data, asset, dark: bool) -> None:
    rate, _ = current_rate(data)
    frame = asset_analysis(data, asset)
    st.markdown(f'<h2>{asset.get("name", "")}</h2>', unsafe_allow_html=True)
    st.caption(f"ارز: **{currency_label(asset.get('currency', 'IRR'))}** | ایجاد: {asset.get('created_at_jalali', '—')}")

    with st.expander("⚙️ ویرایش نام، ارز و رنگ"):
        with st.form(f"edit_asset_{asset['id']}"):
            c1, c2, c3 = st.columns([3, 2, 2])
            new_name = c1.text_input("نام", value=asset.get("name", ""))
            new_currency = c2.selectbox("ارز", ["IRR", "USD"], index=0 if asset.get("currency", "IRR") == "IRR" else 1,
                                        format_func=lambda value: "ریال" if value == "IRR" else "دلار")
            new_color = c3.color_picker("رنگ", value=asset.get("color", "#3b82f6"))
            if st.form_submit_button("💾 ذخیره", use_container_width=True):
                if new_name.strip():
                    asset["name"] = new_name.strip()
                    asset["currency"] = new_currency
                    asset["color"] = new_color
                    save_all(data)
                    st.rerun()

    latest = latest_record(asset.get("records", []))
    value, usd_value = asset_value(asset, rate)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 تعداد", fmt_num(latest.get("quantity", 0)) if latest else "—")
    c2.metric("💲 قیمت هر واحد", f"{fmt_num(latest.get('unit_price', 0))} {currency_label(asset.get('currency', 'IRR'))}" if latest else "—")
    c3.metric("💰 ارزش کل", f"{fmt_num(value)} {currency_label(asset.get('currency', 'IRR'))}" if latest else "—")
    c4.metric("💵 ارزش دلاری", f"${usd_value:,.2f}" if usd_value is not None else "—")

    with st.container(border=True):
        st.subheader("➕ ثبت رکورد روزانه")
        with st.form(f"add_record_{asset['id']}", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
            date_text = c1.text_input("تاریخ (شمسی)", value=today_jalali_str())
            quantity = c2.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
            price = c3.number_input(f"قیمت هر واحد ({currency_label(asset.get('currency', 'IRR'))})", min_value=0.0, format="%.2f", step=1000.0)
            note = c4.text_input("توضیح")
            if st.form_submit_button("💾 ثبت", use_container_width=True):
                jdate = parse_jalali(date_text)
                if jdate and quantity > 0 and price > 0:
                    asset.setdefault("records", []).append({
                        "id": short_id(), "date_gregorian": jalali_to_gregorian_iso(jdate, datetime.now().strftime("%H:%M")),
                        "date_jalali": jdate.strftime("%Y/%m/%d"), "quantity": quantity,
                        "unit_price": price, "note": note.strip(),
                    })
                    save_all(data)
                    st.rerun()
                else:
                    st.error("مقادیر معتبر وارد کنید.")

    records = sorted(asset.get("records", []), key=lambda item: item.get("date_gregorian", ""))
    if len(records) >= 2:
        st.subheader("📈 روند ارزش کل")
        st.caption("⚠️ ارزش کل = تعداد × قیمت؛ با خرید و فروش تغییر می‌کند.")
        chart = pd.DataFrame([{
            "تاریخ": row.get("date_jalali"),
            "ارزش": float(row.get("quantity", 0)) * float(row.get("unit_price", 0)),
        } for row in records])
        fig = px.line(chart, x="تاریخ", y="ارزش", markers=True)
        fig.update_traces(line={"width": 3}, marker={"size": 7})
        st.plotly_chart(chart_layout(fig, dark), use_container_width=True)

    if len(frame) >= 2:
        st.subheader("📈 مقایسهٔ قیمت هر واحد (پایه = ۱۰۰)")
        st.caption("🔵 قیمت واحد به ریال | 🟢 قیمت واحد به دلار | 🟠 نرخ دلار — مستقل از تعداد")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=frame["label"], y=frame["irr_index"], mode="lines+markers", name="قیمت واحد (ریال)", line={"color": "#3b82f6", "width": 3}))
        fig.add_trace(go.Scatter(x=frame["label"], y=frame["usd_index"], mode="lines+markers", name="قیمت واحد (دلار)", line={"color": "#10b981", "width": 3}))
        fig.add_trace(go.Scatter(x=frame["label"], y=frame["rate_index"], mode="lines+markers", name="نرخ دلار", line={"color": "#f59e0b", "width": 2, "dash": "dot"}))
        st.plotly_chart(chart_layout(fig, dark), use_container_width=True)
        last = frame.iloc[-1]
        irr_change = last["irr_index"] - 100
        usd_change = last["usd_index"] - 100
        rate_change = last["rate_index"] - 100
        if irr_change > 5 and usd_change < -5:
            st.error(f"🔴 تله دلار: ریالی {irr_change:+.1f}٪ رشد ولی دلاری {usd_change:+.1f}٪ افت (نرخ دلار {rate_change:+.1f}٪).")
        elif usd_change > 5:
            st.success(f"🟢 سود دلاری واقعی: قیمت واحد به دلار {usd_change:+.1f}٪ رشد (نرخ دلار {rate_change:+.1f}٪).")
        elif usd_change < -5:
            st.warning(f"🟡 ضرر دلاری: قیمت واحد به دلار {usd_change:+.1f}٪ افت (نرخ دلار {rate_change:+.1f}٪).")
        else:
            st.info(f"⚪ قیمت واحد به دلار {usd_change:+.1f}٪ — تعادل نسبی.")

    st.subheader("📋 تاریخچه رکوردها")
    for record in reversed(records):
        date_str = record.get("date_gregorian", "")[:10]
        rate_used = rate_at(data, date_str)
        unit = float(record.get("unit_price", 0) or 0)
        unit_irr = unit if asset.get("currency", "IRR") != "USD" else unit * (rate_used or 0)
        unit_usd = unit if asset.get("currency", "IRR") == "USD" else (unit / rate_used if rate_used else 0)
        with st.expander(f"📅 {record.get('date_jalali', '—')} — {fmt_num(record.get('quantity', 0))} واحد × {fmt_num(unit)}"):
            cols = st.columns(4)
            cols[0].caption(f"ریال: **{fmt_num(unit_irr)}**")
            cols[1].caption(f"دلار: **${unit_usd:,.4f}**")
            cols[2].caption(f"نرخ دلار: **{fmt_num(rate_used or 0)}**")
            cols[3].caption(f"یادداشت: {record.get('note') or '—'}")
            with st.form(f"edit_record_{asset['id']}_{record['id']}"):
                c1, c2, c3 = st.columns([2, 2, 2])
                edit_date = c1.text_input("تاریخ", value=record.get("date_jalali", today_jalali_str()))
                edit_quantity = c2.number_input("تعداد", value=float(record.get("quantity", 0) or 0), min_value=0.0, format="%.4f")
                edit_price = c3.number_input("قیمت هر واحد", value=float(unit), min_value=0.0, format="%.2f")
                edit_note = st.text_input("توضیح", value=record.get("note", ""))
                save_col, delete_col = st.columns(2)
                if save_col.form_submit_button("💾 ذخیره", use_container_width=True):
                    jdate = parse_jalali(edit_date)
                    if jdate and edit_quantity > 0 and edit_price > 0:
                        record.update({
                            "date_gregorian": jalali_to_gregorian_iso(jdate, datetime.now().strftime("%H:%M")),
                            "date_jalali": jdate.strftime("%Y/%m/%d"), "quantity": edit_quantity,
                            "unit_price": edit_price, "note": edit_note.strip(),
                        })
                        save_all(data)
                        st.rerun()
                if delete_col.form_submit_button("🗑️ حذف رکورد", use_container_width=True):
                    asset["records"] = [item for item in asset.get("records", []) if item.get("id") != record.get("id")]
                    save_all(data)
                    st.rerun()

    with st.expander("⚠️ حذف کل دارایی"):
        confirm = st.checkbox("مطمئنم", key=f"confirm_asset_{asset['id']}")
        if st.button("🗑️ حذف دارایی", disabled=not confirm, key=f"delete_asset_{asset['id']}", use_container_width=True):
            data["assets"] = [item for item in data["assets"] if item.get("id") != asset.get("id")]
            data["synthetic_pairs"] = [
                pair for pair in data.get("synthetic_pairs", [])
                if pair.get("left") != f"asset:{asset['id']}" and pair.get("right") != f"asset:{asset['id']}"
            ]
            st.session_state.pending_nav = "assets"
            save_all(data)
            st.rerun()


# ----------------------------- تحلیل صندوق طلا -----------------------------
def gold_frame(fund) -> pd.DataFrame:
    rows = []
    first_usd = None
    first_ounce = None
    for index, record in enumerate(sorted(fund.get("records", []), key=lambda item: item.get("date_gregorian", ""))):
        unit = float(record.get("unit_price", 0) or 0)
        ounce = float(record.get("ounce_price_usd", 0) or 0)
        rate = float(record.get("usd_rate_used", 0) or 0)
        usd_equivalent = unit / rate if rate > 0 else 0
        if first_usd is None and usd_equivalent > 0:
            first_usd = usd_equivalent
        if first_ounce is None and ounce > 0:
            first_ounce = ounce
        rows.append({
            "id": record.get("id"), "record": record,
            "date": record.get("date_gregorian", "")[:10],
            "label": record.get("date_jalali", "—"),
            "unit": unit, "ounce": ounce, "rate": rate,
            "usd": usd_equivalent,
            "usd_return": (usd_equivalent / first_usd - 1) * 100 if first_usd else 0,
            "units_for_ounce": (ounce * rate / unit) if unit > 0 else 0,
            "gram": (unit * 31.1035) / (ounce * rate) if ounce > 0 and rate > 0 and unit > 0 else None,
            "ounce_index": (ounce / first_ounce * 100) if first_ounce else 100,
            "usd_index": (usd_equivalent / first_usd * 100) if first_usd else 100,
        })
    return pd.DataFrame(rows)


def render_gold_fund(data, fund, dark: bool) -> None:
    frame = gold_frame(fund)
    st.markdown(f"### {fund.get('icon', '🥇')} {fund.get('name', '')}")
    records = fund.get("records", [])
    if not records:
        st.info("هنوز رکوردی برای این صندوق ثبت نشده است.")
    else:
        last = frame.iloc[-1]
        if len(frame) >= 2:
            last_date = frame["date"].iloc[-1]
            try:
                cutoff = (datetime.fromisoformat(last_date + "T00:00:00") - timedelta(days=30)).strftime("%Y-%m-%d")
            except ValueError:
                cutoff = last_date
            older = frame.iloc[0]
            for _, row in frame.iterrows():
                if row["date"] >= cutoff:
                    older = row
                    break
            usd_change = (last["rate"] / older["rate"] - 1) * 100 if older["rate"] else 0
            ounce_change = (last["ounce"] / older["ounce"] - 1) * 100 if older["ounce"] else 0
            gap = usd_change - ounce_change
            if gap > 10:
                st.warning(f"⚠️ **هشدار تله دلار** — در ۳۰ روز گذشته: دلار {usd_change:+.1f}٪، انس {ounce_change:+.1f}٪، شکاف {gap:+.1f}٪. فروش صندوق بدون خرید دلار، سود دلاری را از بین می‌برد.")
        prices = frame["unit"].tolist()
        units = [value for value in frame["units_for_ounce"].tolist() if value > 0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📉 کمترین قیمت", fmt_num(min(prices)))
        c2.metric("📊 میانگین قیمت", fmt_num(sum(prices) / len(prices)))
        c3.metric("📈 بیشترین قیمت", fmt_num(max(prices)))
        c4.metric("📋 تعداد رکورد", fmt_num(len(records)))
        if units:
            u1, u2, u3, u4 = st.columns(4)
            u1.metric("📉 کمترین واحد/انس", fmt_num(min(units)))
            u2.metric("📊 میانگین واحد/انس", fmt_num(sum(units) / len(units)))
            u3.metric("📈 بیشترین واحد/انس", fmt_num(max(units)))
            u4.metric("💵 معادل دلاری فعلی", f"${last['usd']:,.4f}", delta=f"{last['usd_return']:+.1f}%")

        ounce_rows = frame[frame["ounce"] > 0]
        if len(ounce_rows) >= 3:
            recent = ounce_rows.tail(10)
            average = recent["ounce"].mean()
            diff = (last["ounce"] / average - 1) * 100 if average else 0
            if diff > 5:
                st.error(f"🔴 سیگنال انس: {diff:+.1f}٪ بالای میانگین — فروش")
            elif diff > 0:
                st.warning(f"🟡 سیگنال انس: {diff:+.1f}٪ بالای میانگین — کمی فروش")
            elif diff > -5:
                st.success(f"🟢 سیگنال انس: {diff:+.1f}٪ زیر میانگین — کمی خرید")
            else:
                st.success(f"🟢🟢 سیگنال انس: {diff:+.1f}٪ زیر میانگین — خرید قوی")

        if len(frame) >= 2:
            st.markdown("**📈 نمودار مقایسه‌ای (پایه = ۱۰۰)**")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=frame["label"], y=frame["unit"] / frame["unit"].iloc[0] * 100, mode="lines+markers", name="قیمت ریالی", line={"color": "#3b82f6", "width": 3}))
            fig.add_trace(go.Scatter(x=frame["label"], y=frame["usd_index"], mode="lines+markers", name="معادل دلاری", line={"color": "#10b981", "width": 3}))
            fig.add_trace(go.Scatter(x=frame["label"], y=frame["ounce_index"], mode="lines+markers", name="انس طلا", line={"color": "#f59e0b", "width": 2, "dash": "dot"}))
            st.plotly_chart(chart_layout(fig, dark, 380), use_container_width=True)
            st.caption(f"قیمت ریالی: {frame['unit'].iloc[-1] / frame['unit'].iloc[0] * 100 - 100:+.1f}٪ | دلاری: {frame['usd_index'].iloc[-1] - 100:+.1f}٪")

        with st.expander("🧮 ماشین‌حساب آربیتراژ دلاری"):
            rate_now, _ = current_rate(data)
            if not rate_now:
                st.warning("ابتدا نرخ دلار را در صفحهٔ «💵 دلار» ثبت کنید.")
            else:
                c1, c2, c3, c4 = st.columns(4)
                units_calc = c1.number_input("تعداد واحد", min_value=0.0, value=1.0, step=1.0, key=f"arb_units_{fund['id']}")
                sell_price = c2.number_input("قیمت فروش (ریال)", min_value=0.0, value=float(last["unit"]), step=1000.0, key=f"arb_sell_{fund['id']}")
                target_rate = c3.number_input("نرخ دلار پیش‌بینی", min_value=0.0, value=float(rate_now), step=1000.0, key=f"arb_rate_{fund['id']}")
                buy_price = c4.number_input("قیمت خرید مجدد (ریال)", min_value=0.0, value=float(last["unit"]), step=1000.0, key=f"arb_buy_{fund['id']}")
                f1, f2, f3 = st.columns(3)
                sell_fee = f1.number_input("کارمزد فروش صندوق (%)", min_value=0.0, value=0.5, step=0.1, key=f"arb_sf_{fund['id']}")
                usd_spread = f2.number_input("اسپرد دلار (%)", min_value=0.0, value=1.0, step=0.1, key=f"arb_us_{fund['id']}")
                buy_fee = f3.number_input("کارمزد خرید صندوق (%)", min_value=0.0, value=0.5, step=0.1, key=f"arb_bf_{fund['id']}")
                if units_calc > 0 and sell_price > 0 and target_rate > 0 and buy_price > 0:
                    gross = units_calc * sell_price * (1 - sell_fee / 100)
                    dollars = gross / (target_rate * (1 + usd_spread / 100))
                    irr_back = dollars * target_rate * (1 - usd_spread / 100)
                    new_units = (irr_back / buy_price) * (1 - buy_fee / 100)
                    net_units = new_units - units_calc
                    r1, r2, r3 = st.columns(3)
                    r1.metric("💵 دلار به‌دست‌آمده", f"${dollars:,.4f}")
                    r2.metric("📦 واحد پس از خرید مجدد", f"{new_units:,.4f}")
                    r3.metric("سود خالص", f"{net_units:+,.4f} واحد", delta=f"{net_units * buy_price:+,.0f} ریال")
                    if net_units > 0:
                        st.success("✅ این آربیتراژ سودآور است.")
                    else:
                        st.error("❌ این آربیتراژ ضرر دارد.")

    with st.expander(f"➕ افزودن رکورد برای {fund.get('name', '')}", expanded=not records):
        rate_now, rate_date = current_rate(data)
        if not rate_now:
            st.warning("⚠️ ابتدا نرخ دلار را در صفحهٔ «💵 دلار» ثبت کنید.")
        else:
            st.caption(f"نرخ دلار فعلی: **{fmt_num(rate_now)}** ریال ({rate_date})")
            c1, c2, c3 = st.columns(3)
            g_date = c1.text_input("تاریخ (شمسی)", value=today_jalali_str(), key=f"gdate_{fund['id']}")
            g_price = c2.number_input("قیمت واحد (ریال)", min_value=0.0, step=1000.0, key=f"gprice_{fund['id']}")
            g_ounce = c3.number_input("انس طلا (دلار)", min_value=0.0, value=3000.0, step=1.0, key=f"gounce_{fund['id']}")
            g_note = st.text_input("توضیح (اختیاری)", key=f"gnote_{fund['id']}")
            if g_price > 0 and g_ounce > 0:
                st.success(f"📊 واحد برای ۱ انس: **{(g_ounce * rate_now) / g_price:,.0f}** واحد | معادل دلاری: **${g_price / rate_now:.4f}**")
            if st.button("💾 ثبت رکورد", key=f"gsave_{fund['id']}", use_container_width=True):
                jdate = parse_jalali(g_date)
                if jdate is None or g_price <= 0 or g_ounce <= 0:
                    st.error("مقادیر معتبر وارد کنید.")
                else:
                    fund.setdefault("records", []).append({
                        "id": short_id(), "date_gregorian": jalali_to_gregorian_iso(jdate, datetime.now().strftime("%H:%M")),
                        "date_jalali": jdate.strftime("%Y/%m/%d"), "unit_price": g_price,
                        "ounce_price_usd": g_ounce, "usd_rate_used": rate_now, "note": g_note.strip(),
                    })
                    save_all(data)
                    st.rerun()

    if records:
        st.markdown("**📋 تاریخچه رکوردها**")
        for record in reversed(sorted(records, key=lambda item: item.get("date_gregorian", ""))):
            with st.expander(f"📅 {record.get('date_jalali', '—')} — {fmt_num(record.get('unit_price', 0))} ریال"):
                with st.form(f"edit_gold_{fund['id']}_{record['id']}"):
                    c1, c2, c3 = st.columns(3)
                    edit_date = c1.text_input("تاریخ", value=record.get("date_jalali", today_jalali_str()))
                    edit_price = c2.number_input("قیمت واحد", value=float(record.get("unit_price", 0) or 0), min_value=0.0, format="%.0f", step=1000.0)
                    edit_ounce = c3.number_input("انس (دلار)", value=float(record.get("ounce_price_usd", 0) or 0), min_value=0.0, format="%.2f")
                    c4, c5 = st.columns(2)
                    edit_rate = c4.number_input("نرخ دلار", value=float(record.get("usd_rate_used", 0) or 0), min_value=0.0, format="%.0f", step=1000.0)
                    edit_note = c5.text_input("توضیح", value=record.get("note", ""))
                    sc, dc = st.columns(2)
                    if sc.form_submit_button("💾 ذخیره", use_container_width=True):
                        jdate = parse_jalali(edit_date)
                        if jdate and edit_price > 0 and edit_ounce > 0 and edit_rate > 0:
                            record.update({
                                "date_gregorian": jalali_to_gregorian_iso(jdate, datetime.now().strftime("%H:%M")),
                                "date_jalali": jdate.strftime("%Y/%m/%d"), "unit_price": edit_price,
                                "ounce_price_usd": edit_ounce, "usd_rate_used": edit_rate, "note": edit_note.strip(),
                            })
                            save_all(data)
                            st.rerun()
                    if dc.form_submit_button("🗑️ حذف", use_container_width=True):
                        fund["records"] = [item for item in fund.get("records", []) if item.get("id") != record.get("id")]
                        save_all(data)
                        st.rerun()

    with st.expander("⚠️ حذف صندوق"):
        confirm = st.checkbox("مطمئنم", key=f"confirm_gold_{fund['id']}")
        if st.button("🗑️ حذف صندوق", disabled=not confirm, key=f"delete_gold_{fund['id']}", use_container_width=True):
            data["gold_funds"] = [item for item in data["gold_funds"] if item.get("id") != fund.get("id")]
            data["synthetic_pairs"] = [
                pair for pair in data.get("synthetic_pairs", [])
                if pair.get("left") != f"gold:{fund['id']}" and pair.get("right") != f"gold:{fund['id']}"
            ]
            save_all(data)
            st.rerun()


# ----------------------------- صفحات -----------------------------
def page_overview(data, dark: bool) -> None:
    assets = data.get("assets", [])
    rate, rate_date = current_rate(data)
    st.header("📊 نمای کلی دارایی‌ها")
    total_usd = 0.0
    total_irr = 0.0
    rows = []
    for asset in assets:
        value, usd_value = asset_value(asset, rate)
        record = latest_record(asset.get("records", []))
        total_usd += usd_value or 0
        total_irr += value if asset.get("currency", "IRR") != "USD" else value * (rate or 0)
        rows.append({
            "دارایی": asset.get("name"), "ارز": currency_label(asset.get("currency", "IRR")),
            "ارزش": fmt_num(value), "معادل دلاری": f"${usd_value:,.2f}" if usd_value else "—",
            "آخرین بروزرسانی": record.get("date_jalali") if record else "—",
        })
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 ارزش کل (دلار)", f"${total_usd:,.2f}")
    c2.metric("📁 دارایی‌ها", len(assets))
    c3.metric("💵 نرخ دلار", f"{fmt_num(rate)} ریال" if rate else "ثبت نشده")
    c4.metric("🔀 جفت‌های مصنوعی", len(data.get("synthetic_pairs", [])))
    if not assets:
        st.info("هنوز دارایی‌ای ثبت نشده است.")
        return
    frame = pd.DataFrame(rows)
    render_table(frame)
    pie_rows = [{"name": asset.get("name"), "value": (asset_value(asset, rate)[1] or 0)} for asset in assets]
    pie_frame = pd.DataFrame([row for row in pie_rows if row["value"] > 0])
    if not pie_frame.empty:
        fig = px.pie(pie_frame, values="value", names="name", hole=0.45)
        st.plotly_chart(chart_layout(fig, dark, 320), use_container_width=True)


def page_add_asset(data) -> None:
    st.header("➕ افزودن دارایی")
    with st.container(border=True):
        with st.form("add_asset_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            name = c1.text_input("نام", placeholder="وبملت، طلا، ...")
            currency = c2.selectbox("ارز", ["IRR", "USD"], format_func=lambda value: "ریال" if value == "IRR" else "دلار")
            color = c3.color_picker("رنگ", value=PALETTE[len(data.get("assets", [])) % len(PALETTE)])
            c4, c5, c6 = st.columns([2, 2, 3])
            quantity = c4.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
            price = c5.number_input("قیمت واحد", min_value=0.0, format="%.2f", step=1000.0)
            note = c6.text_input("توضیح")
            if st.form_submit_button("💾 ایجاد دارایی", use_container_width=True):
                if not name.strip():
                    st.error("نام را وارد کنید.")
                else:
                    asset_id = short_id()
                    records = []
                    if quantity > 0 and price > 0:
                        records.append({
                            "id": asset_id + "_r0", "date_gregorian": datetime.now().isoformat(),
                            "date_jalali": today_jalali_str(), "quantity": quantity,
                            "unit_price": price, "note": note.strip() or "رکورد اولیه",
                        })
                    data["assets"].append({
                        "id": asset_id, "name": name.strip(), "icon": "fa-wallet", "color": color,
                        "overview_emoji": "", "currency": currency,
                        "created_at_gregorian": datetime.now().isoformat(),
                        "created_at_jalali": today_jalali_str(), "records": records,
                    })
                    save_all(data)
                    st.rerun()


def page_usd(data, dark: bool) -> None:
    st.header("💵 نرخ دلار")
    with st.container(border=True):
        with st.form("usd_rate_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 3])
            new_rate = c1.number_input("نرخ (ریال)", min_value=0, step=1000, format="%d")
            date_text = c2.text_input("تاریخ", value=today_jalali_str())
            note = c3.text_input("توضیح")
            if st.form_submit_button("💾 ثبت", use_container_width=True):
                jdate = parse_jalali(date_text)
                if new_rate > 0 and jdate:
                    data["usd_rates"].append({
                        "id": short_id(), "rate": new_rate, "note": note.strip(),
                        "created_at": jalali_to_gregorian_iso(jdate, datetime.now().strftime("%H:%M")),
                        "created_at_jalali": jdate.strftime("%Y/%m/%d"),
                    })
                    save_all(data)
                    st.rerun()
                else:
                    st.error("نرخ و تاریخ معتبر وارد کنید.")
    rates = sorted(data.get("usd_rates", []), key=lambda item: item.get("created_at", ""))
    if not rates:
        st.info("هنوز نرخی ثبت نشده است.")
        return
    current, current_date = current_rate(data)
    c1, c2 = st.columns(2)
    c1.metric("نرخ فعلی", f"{fmt_num(current)} ریال")
    c2.metric("آخرین ثبت", current_date or "—")
    chart = pd.DataFrame([{"تاریخ": item.get("created_at_jalali"), "نرخ": float(item["rate"])} for item in rates])
    fig = px.line(chart, x="تاریخ", y="نرخ", markers=True)
    st.plotly_chart(chart_layout(fig, dark, 320), use_container_width=True)
    st.subheader("📋 تاریخچه")
    for item in reversed(rates):
        with st.expander(f"{fmt_num(item['rate'])} ریال — {item.get('created_at_jalali', '—')}"):
            with st.form(f"edit_rate_{item['id']}"):
                c1, c2 = st.columns(2)
                edit_date = c1.text_input("تاریخ", value=item.get("created_at_jalali", today_jalali_str()))
                edit_rate = c2.number_input("نرخ", value=int(float(item["rate"])), min_value=1, step=1000, format="%d")
                edit_note = st.text_input("توضیح", value=item.get("note", ""))
                sc, dc = st.columns(2)
                if sc.form_submit_button("💾 ذخیره", use_container_width=True):
                    jdate = parse_jalali(edit_date)
                    if jdate:
                        item.update({
                            "rate": edit_rate, "note": edit_note.strip(),
                            "created_at": jalali_to_gregorian_iso(jdate, datetime.now().strftime("%H:%M")),
                            "created_at_jalali": jdate.strftime("%Y/%m/%d"),
                        })
                        save_all(data)
                        st.rerun()
                if dc.form_submit_button("🗑️ حذف", use_container_width=True):
                    data["usd_rates"] = [row for row in data["usd_rates"] if row.get("id") != item["id"]]
                    save_all(data)
                    st.rerun()


def page_gold(data, dark: bool) -> None:
    st.header("🥇 صندوق‌های طلا")
    with st.container(border=True):
        with st.form("add_gold_fund", clear_on_submit=True):
            c1, c2 = st.columns([3, 2])
            name = c1.text_input("نام صندوق", placeholder="عیار، لوتوس، ...")
            icon = c2.text_input("نماد", value="🥇", max_chars=8)
            if st.form_submit_button("💾 ایجاد صندوق", use_container_width=True):
                if name.strip():
                    data["gold_funds"].append({
                        "id": short_id(), "name": name.strip(), "icon": icon.strip() or "🥇",
                        "created_at": datetime.now().isoformat(), "records": [],
                    })
                    save_all(data)
                    st.rerun()
                else:
                    st.error("نام صندوق را وارد کنید.")
    funds = data.get("gold_funds", [])
    if not funds:
        st.info("هنوز صندوقی اضافه نشده است.")
        return
    for fund in funds:
        render_gold_fund(data, fund, dark)
        st.divider()


def page_synthetic(data, dark: bool) -> None:
    st.header("🔀 جفت ارز مصنوعی")
    st.caption("نسبت قیمت دو ابزار دارای تاریخچه؛ برای نمونه «صندوق طلا / دلار» یا «وبملت / صندوق طلا». قیمت‌ها برای مقایسه به ریال تبدیل می‌شوند.")
    instruments = get_instruments(data)
    if len(instruments) < 2:
        st.info("برای ساخت جفت، دست‌کم دو ابزار دارای داده لازم است. یک دارایی، صندوق طلا یا نرخ دلار ثبت کنید.")
        return
    labels = {item["id"]: item["label"] for item in instruments}
    with st.container(border=True):
        st.subheader("➕ ساخت جفت جدید")
        c1, c2 = st.columns(2)
        left_id = c1.selectbox("سمت اول (صورت)", list(labels), format_func=labels.get, key="pair_left")
        right_id = c2.selectbox("سمت دوم (مخرج)", list(labels), index=min(1, len(labels) - 1), format_func=labels.get, key="pair_right")
        duplicate = any(pair.get("left") == left_id and pair.get("right") == right_id for pair in data.get("synthetic_pairs", []))
        if st.button("🔀 ساخت جفت مصنوعی", use_container_width=True, disabled=(left_id == right_id or duplicate)):
            data["synthetic_pairs"].append({
                "id": short_id(), "left": left_id, "right": right_id,
                "name": f"{labels[left_id]} / {labels[right_id]}",
                "created_at": datetime.now().isoformat(),
            })
            save_all(data)
            st.rerun()
        if left_id == right_id:
            st.caption("دو سمت باید متفاوت باشند.")
        elif duplicate:
            st.caption("این جفت قبلاً ساخته شده است.")

    pairs = data.get("synthetic_pairs", [])
    if not pairs:
        st.info("هنوز جفتی نساخته‌اید.")
        return
    pair_labels = {pair["id"]: pair.get("name", "") for pair in pairs}
    selected = st.selectbox("جفت‌های ذخیره‌شده", list(pair_labels), format_func=pair_labels.get)
    pair = next(item for item in pairs if item["id"] == selected)
    left_label = labels.get(pair.get("left"), pair.get("left", ""))
    right_label = labels.get(pair.get("right"), pair.get("right", ""))
    frame = build_pair_series(data, pair.get("left"), pair.get("right"))
    c1, c2, c3 = st.columns(3)
    if frame.empty:
        c1.metric("نسبت فعلی", "—")
        c2.metric("تغییر از ابتدا", "—")
        c3.metric("تعداد نقاط", "0")
        st.warning("داده‌ای برای این جفت موجود نیست؛ ممکن است منبع حذف شده باشد.")
    else:
        last = frame.iloc[-1]
        first = frame.iloc[0]
        c1.metric("نسبت فعلی", f"{last['ratio']:,.5f}", help=f"{left_label} ÷ {right_label}")
        c2.metric("تغییر نسبت از ابتدا", f"{last['ratio_index'] - 100:+.2f}٪")
        c3.metric("تعداد نقاط", f"{len(frame):,}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=frame["label"], y=frame["ratio"], mode="lines+markers", name="نسبت مصنوعی", line={"color": "#8b5cf6", "width": 3}, fill="tozeroy"))
        fig.update_layout(yaxis_title="نسبت", xaxis_title="تاریخ")
        st.plotly_chart(chart_layout(fig, dark, 400), use_container_width=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=frame["label"], y=frame["left_index"], mode="lines+markers", name=left_label, line={"color": "#3b82f6", "width": 3}))
        fig2.add_trace(go.Scatter(x=frame["label"], y=frame["right_index"], mode="lines+markers", name=right_label, line={"color": "#10b981", "width": 3}))
        fig2.update_layout(yaxis_title="شاخص (پایه = ۱۰۰)")
        st.plotly_chart(chart_layout(fig2, dark, 360), use_container_width=True)
        table = frame[["label", "left", "right", "ratio", "ratio_index"]].copy()
        table.columns = ["تاریخ", left_label, right_label, "نسبت", "شاخص"]
        render_table(table.sort_values("تاریخ", ascending=False).head(15))
        with st.expander("🗑️ حذف این جفت"):
            if st.button("حذف جفت مصنوعی", key=f"del_pair_{pair['id']}", use_container_width=True):
                data["synthetic_pairs"] = [item for item in pairs if item["id"] != pair["id"]]
                save_all(data)
                st.rerun()


def compute_monthly_returns(data, year_jalali: int) -> dict:
    rates_sorted = sorted(data.get("usd_rates", []), key=lambda item: item.get("created_at", ""))

    def get_rate(date_str: str):
        value = None
        for item in rates_sorted:
            if item.get("created_at", "")[:10] <= date_str:
                try:
                    candidate = float(item.get("rate", 0) or 0)
                    if candidate > 0:
                        value = candidate
                except (TypeError, ValueError):
                    continue
            else:
                break
        return value

    def price_irr(record, kind, currency):
        try:
            unit = float(record.get("unit_price", 0) or 0)
        except (TypeError, ValueError):
            return None
        if unit <= 0:
            return None
        if kind == "gold" or currency == "IRR":
            return unit
        rate = get_rate(record.get("date_gregorian", "")[:10])
        return unit * rate if rate else None

    items = [
        {"name": asset["name"], "type": "asset", "currency": asset.get("currency", "IRR"), "records": asset.get("records", [])}
        for asset in data.get("assets", [])
    ]
    items += [
        {"name": f"🥇 {fund['name']}", "type": "gold", "currency": "IRR", "records": fund.get("records", [])}
        for fund in data.get("gold_funds", [])
    ]
    results = {}
    for item in items:
        records = sorted(item["records"], key=lambda row: row.get("date_gregorian", ""))
        monthly = {}
        for month in range(1, 13):
            try:
                start = jdatetime.date(year_jalali, month, 1).togregorian().strftime("%Y-%m-%d")
                end = (jdatetime.date(year_jalali + 1, 1, 1) if month == 12 else jdatetime.date(year_jalali, month + 1, 1)).togregorian().strftime("%Y-%m-%d")
            except Exception:
                monthly[month] = None
                continue
            in_month = [row for row in records if start <= row.get("date_gregorian", "")[:10] < end]
            if not in_month:
                monthly[month] = None
                continue
            before = [row for row in records if row.get("date_gregorian", "")[:10] < start]
            start_rec = before[-1] if before else in_month[0]
            end_rec = in_month[-1]
            if start_rec is end_rec:
                monthly[month] = None
                continue
            start_price = price_irr(start_rec, item["type"], item["currency"])
            end_price = price_irr(end_rec, item["type"], item["currency"])
            if not start_price or not end_price:
                monthly[month] = None
                continue
            monthly[month] = {
                "return_pct": (end_price / start_price - 1) * 100,
                "profit_irr": (end_price - start_price) * float(start_rec.get("quantity", 0) or 0),
            }
        results[item["name"]] = monthly
    return results


def page_monthly(data, dark: bool) -> None:
    st.header("📅 بازده ماهانه")
    st.caption("بازده بر پایهٔ تغییر قیمت هر واحد؛ خرید و فروش تعداد، بازده ساختگی ایجاد نمی‌کند.")
    dates = []
    for asset in data.get("assets", []):
        dates += [row.get("date_jalali", "") for row in asset.get("records", [])]
    for fund in data.get("gold_funds", []):
        dates += [row.get("date_jalali", "") for row in fund.get("records", [])]
    years = sorted({int(value[:4]) for value in dates if value[:4].isdigit()}, reverse=True)
    if not years:
        st.info("هنوز داده‌ای ثبت نشده است.")
        return
    month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    c1, c2, c3, c4 = st.columns(4)
    year = c1.selectbox("سال (شمسی)", years)
    month_from = c2.selectbox("از ماه", month_names, index=0)
    month_to = c3.selectbox("تا ماه", month_names, index=11)
    mode = c4.selectbox("نمایش", ["درصد بازده", "سود / زیان ریالی"])
    start_idx = month_names.index(month_from) + 1
    end_idx = month_names.index(month_to) + 1
    if start_idx > end_idx:
        st.warning("ماه شروع باید قبل از ماه پایان باشد.")
        return
    results = compute_monthly_returns(data, year)
    labels = month_names[start_idx - 1:end_idx]
    rows = []
    figure = go.Figure()
    for name, monthly in results.items():
        values = [monthly.get(month) for month in range(start_idx, end_idx + 1)]
        if not any(values):
            continue
        if mode == "درصد بازده":
            y_values = [value["return_pct"] if value else 0 for value in values]
        else:
            y_values = [value["profit_irr"] if value else 0 for value in values]
        rows.append({"نام": name, **{labels[index]: (f"{value['return_pct']:+.2f}٪" if value else "—") for index, value in enumerate(values)}})
        figure.add_trace(go.Bar(name=name, x=labels, y=y_values))
    if not rows:
        st.info("برای این بازه بازدهی قابل محاسبه نیست.")
        return
    figure.update_layout(barmode="group", yaxis_title="درصد" if mode == "درصد بازده" else "ریال")
    st.plotly_chart(chart_layout(figure, dark, 420), use_container_width=True)
    render_table(pd.DataFrame(rows))


def render_sidebar_settings(data) -> None:
    settings = data["settings"]
    with st.expander("🎨 اولویت سربرگ‌ها", expanded=False):
        order = list(settings.get("nav_order") or DEFAULT_NAV_ORDER)
        for index, key in enumerate(order):
            cols = st.columns([4, 1, 1])
            cols[0].markdown(f"**{index + 1}.** {NAV_EMOJI.get(key, '')} {NAV_LABELS.get(key, key)}")
            if cols[1].button("▲", key=f"nav_up_{key}", disabled=index == 0):
                order[index - 1], order[index] = order[index], order[index - 1]
                settings["nav_order"] = order
                save_all(data)
                st.rerun()
            if cols[2].button("▼", key=f"nav_down_{key}", disabled=index == len(order) - 1):
                order[index + 1], order[index] = order[index], order[index + 1]
                settings["nav_order"] = order
                save_all(data)
                st.rerun()
    with st.expander("🌗 حالت روز / شب", expanded=False):
        auto = st.checkbox("تغییر خودکار بر اساس ساعت", value=bool(settings.get("auto_theme", True)))
        c1, c2 = st.columns(2)
        day_start = c1.text_input("شروع روز", value=settings.get("day_start", "07:00"))
        night_start = c2.text_input("شروع شب", value=settings.get("night_start", "19:00"))
        if st.button("💾 ذخیرهٔ زمان‌بندی", key="save_theme_schedule", use_container_width=True):
            settings["auto_theme"] = auto
            settings["day_start"] = day_start
            settings["night_start"] = night_start
            save_all(data)
            st.rerun()
        if not settings.get("auto_theme", True):
            manual_dark = st.checkbox("حالت شب دستی", value=bool(settings.get("dark_mode", False)))
            if manual_dark != bool(settings.get("dark_mode", False)):
                settings["dark_mode"] = manual_dark
                save_all(data)
                st.rerun()
        st.caption(f"اکنون: {'🌙 شب' if auto_theme(settings) else '☀️ روز'} (ساعت تهران)")


def page_settings(data) -> None:
    st.header("⚙️ تنظیمات")
    render_sidebar_settings(data)
    with st.expander("💾 وضعیت ذخیره‌سازی", expanded=True):
        local_ok = os.path.exists(DATA_FILE)
        st.caption(f"{'✅' if local_ok else '❌'} فایل محلی data.json")
        st.caption(f"{'✅' if (GITHUB_TOKEN and GITHUB_REPO) else '❌'} اتصال GitHub")
        st.caption(f"آخرین ذخیره: {data.get('last_saved_jalali', '—')}")
    st.download_button(
        "📥 دانلود پشتیبان JSON",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )


# ----------------------------- احراز هویت -----------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    token = st.query_params.get("auth")
    if token and token == AUTH_TOKEN:
        st.session_state.authenticated = True

if not st.session_state.authenticated:
    inject_login()
    st.markdown(
        "<div class='login-card'><h2>🔐 داشبورد مالی</h2>"
        "<p>برای دیدن دارایی‌ها و تحلیل‌ها، رمز عبور را وارد کنید.</p></div>",
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        password = st.text_input("رمز عبور", type="password", label_visibility="collapsed")
        if st.form_submit_button("🚪 ورود", use_container_width=True):
            if password == str(APP_PASSWORD):
                st.session_state.authenticated = True
                st.query_params["auth"] = AUTH_TOKEN
                st.rerun()
            else:
                st.error("❌ رمز عبور اشتباه است.")
    st.stop()

# ----------------------------- بارگذاری داده -----------------------------
if "data" not in st.session_state:
    local = load_local_file()
    remote = load_github_file()
    chosen = local
    if local and remote:
        chosen = local if local.get("last_saved", "") >= remote.get("last_saved", "") else remote
    elif remote:
        chosen = remote
    st.session_state.data = migrate_data(chosen or {})
data = migrate_data(st.session_state.data)
st.session_state.data = data
inject_app(data)
dark = auto_theme(data["settings"])

# ----------------------------- سایدبار (سمت راست) -----------------------------
with st.sidebar:
    st.markdown("### 💼 داشبورد مالی")
    st.caption(f"🗓️ {today_jalali_str()}")
    rate, rate_date = current_rate(data)
    if rate:
        st.markdown(
            "<div class='fin-card'><div class='stCaption'>💵 نرخ فعلی دلار</div>"
            f"<div style='font-size:1.35rem;font-weight:800;color:#3b82f6;'>{fmt_num(rate)} <span style='font-size:0.75rem;'>ریال</span></div>"
            f"<div class='stCaption'>آخرین: {rate_date}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("💡 هنوز نرخی ثبت نشده است.")
    st.divider()
    order = data["settings"].get("nav_order") or DEFAULT_NAV_ORDER
    pages = [key for key in order if key in NAV_LABELS] + ["settings"]
    pages = list(dict.fromkeys(pages))
    selected = st.radio(
        "ناوبری",
        pages,
        format_func=lambda key: f"{NAV_EMOJI.get(key, '')} {NAV_LABELS.get(key, key)}",
        label_visibility="collapsed",
    )
    st.divider()
    render_sidebar_settings(data)
    st.divider()
    if st.button("💾 ذخیره فوری", use_container_width=True):
        save_all(data)
    uploaded = st.file_uploader("📤 بازیابی از JSON", type=["json"])
    if uploaded is not None:
        try:
            imported = migrate_data(json.loads(uploaded.read().decode("utf-8")))
            st.session_state.data = imported
            save_all(imported)
            st.rerun()
        except Exception as exc:
            st.error(f"فایل معتبر نیست: {exc}")
    if st.button("🚪 خروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.pop("data", None)
        st.query_params.clear()
        st.rerun()

# ----------------------------- مسیر صفحات -----------------------------
if selected == "overview":
    page_overview(data, dark)
    st.subheader("📈 روند ارزش سبد")
    timeline = []
    all_dates = sorted({row.get("date_gregorian", "")[:10] for asset in data.get("assets", []) for row in asset.get("records", [])}
                       | {row.get("created_at", "")[:10] for row in data.get("usd_rates", [])})
    for date_str in all_dates:
        total = 0.0
        for asset in data.get("assets", []):
            history = [row for row in asset.get("records", []) if row.get("date_gregorian", "")[:10] <= date_str]
            record = history[-1] if history else None
            if not record:
                continue
            rate_value = rate_at(data, date_str)
            unit = float(record.get("unit_price", 0) or 0)
            if asset.get("currency", "IRR") == "USD":
                unit *= rate_value or 0
            total += unit * float(record.get("quantity", 0) or 0)
        timeline.append({"تاریخ": iso_to_jalali(date_str + "T00:00:00", False), "ارزش": total})
    if len(timeline) >= 2:
        figure = px.line(pd.DataFrame(timeline), x="تاریخ", y="ارزش", markers=True)
        st.plotly_chart(chart_layout(figure, dark, 320), use_container_width=True)
elif selected == "journal":
    page_add_asset(data)
elif selected == "assets":
    st.header("🧾 دارایی‌ها")
    rate, _rate_date = current_rate(data)
    assets = data.get("assets", [])
    if not assets:
        st.info("هنوز دارایی‌ای ثبت نشده است. از صفحهٔ «➕ افزودن دارایی» شروع کنید.")
    else:
        labels = {asset["id"]: asset.get("name", "") for asset in assets}
        asset_id = st.selectbox("دارایی", list(labels), format_func=labels.get)
        asset = next(item for item in assets if item["id"] == asset_id)
        render_asset_detail(data, asset, dark)
        st.divider()
        st.subheader("📋 همهٔ دارایی‌ها")
        render_table(pd.DataFrame([{
            "دارایی": item.get("name"),
            "ارز": currency_label(item.get("currency", "IRR")),
            "ارزش": fmt_num(asset_value(item, rate)[0]),
            "معادل دلاری": f"${asset_value(item, rate)[1]:,.2f}" if asset_value(item, rate)[1] else "—",
        } for item in assets]))
elif selected == "usd":
    page_usd(data, dark)
elif selected == "gold":
    page_gold(data, dark)
elif selected == "synthetic":
    page_synthetic(data, dark)
elif selected == "monthly":
    page_monthly(data, dark)
elif selected == "settings":
    page_settings(data)

