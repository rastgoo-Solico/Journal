"""Core data, storage and analytics for the original Streamlit dashboard.

The data schema intentionally remains compatible with the user's existing data.json.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import jdatetime
import pandas as pd
import requests
import streamlit as st

DATA_FILE = Path(__file__).resolve().with_name("data.json")
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"
TEHRAN = ZoneInfo("Asia/Tehran")

DEFAULT_NAV_ICONS = {
    "overview": {"icon": "fa-chart-pie", "color": "#3b82f6"},
    "journal": {"icon": "fa-circle-plus", "color": "#10b981"},
    "usd": {"icon": "fa-dollar-sign", "color": "#f59e0b"},
    "gold": {"icon": "fa-coins", "color": "#eab308"},
    "synthetic": {"icon": "fa-scale-balanced", "color": "#8b5cf6"},
    "monthly": {"icon": "fa-calendar-days", "color": "#ec4899"},
}
NAV_LABELS = {
    "overview": "نمای کلی",
    "journal": "افزودن دارایی",
    "usd": "دلار",
    "gold": "صندوق‌های طلا",
    "synthetic": "جفت ارز مصنوعی",
    "monthly": "بازده ماهانه",
}
NAV_EMOJI = {
    "overview": "📊", "journal": "➕", "usd": "💵", "gold": "🥇",
    "synthetic": "⚖️", "monthly": "📅",
}
DEFAULT_NAV_ORDER = ["overview", "journal", "usd", "gold", "synthetic", "monthly"]
FALLBACK_ICONS = [
    {"class": "fa-folder", "label": "Folder"}, {"class": "fa-coins", "label": "Coins"},
    {"class": "fa-wallet", "label": "Wallet"}, {"class": "fa-money-bill-wave", "label": "Money"},
    {"class": "fa-dollar-sign", "label": "Dollar"}, {"class": "fa-building-columns", "label": "Bank"},
    {"class": "fa-piggy-bank", "label": "Piggy Bank"}, {"class": "fa-vault", "label": "Vault"},
    {"class": "fa-gem", "label": "Gem"}, {"class": "fa-crown", "label": "Crown"},
    {"class": "fa-house", "label": "House"}, {"class": "fa-building", "label": "Building"},
    {"class": "fa-car", "label": "Car"}, {"class": "fa-chart-line", "label": "Chart Line"},
    {"class": "fa-chart-pie", "label": "Chart Pie"}, {"class": "fa-bitcoin-sign", "label": "Bitcoin"},
    {"class": "fa-ethereum", "label": "Ethereum"}, {"class": "fa-landmark", "label": "Landmark"},
    {"class": "fa-industry", "label": "Industry"}, {"class": "fa-seedling", "label": "Seedling"},
    {"class": "fa-briefcase", "label": "Briefcase"}, {"class": "fa-store", "label": "Store"},
    {"class": "fa-sack-dollar", "label": "Sack Dollar"}, {"class": "fa-receipt", "label": "Receipt"},
    {"class": "fa-tag", "label": "Tag"}, {"class": "fa-fire", "label": "Fire"},
    {"class": "fa-bolt", "label": "Bolt"}, {"class": "fa-box", "label": "Box"},
    {"class": "fa-gear", "label": "Gear"}, {"class": "fa-circle-plus", "label": "Circle Plus"},
    {"class": "fa-scale-balanced", "label": "Scale Balanced"},
]
CATEGORY_KEYWORDS = {
    "money": ["coin", "dollar", "money", "wallet", "bank", "cash", "currency", "receipt", "sack", "piggy", "vault", "bitcoin", "ethereum", "exchange"],
    "chart": ["chart", "graph", "trend", "analytics", "percent", "scale"],
    "gems": ["gem", "crown", "diamond", "gift", "award", "medal", "star", "trophy"],
    "building": ["building", "house", "home", "office", "factory", "industry", "warehouse", "store", "landmark"],
    "transport": ["car", "truck", "plane", "ship", "train", "bus", "motorcycle", "rocket"],
    "goods": ["box", "package", "shipping", "cart", "basket", "cubes", "cube"],
    "business": ["briefcase", "handshake", "user-tie", "file-invoice", "clipboard-check"],
    "file": ["folder", "file", "save", "download", "upload", "document", "paper", "clipboard", "book"],
    "user": ["user", "person", "people", "group", "team", "users"],
    "system": ["gear", "cog", "tool", "wrench", "key", "lock", "shield", "bell", "power-off"],
    "media": ["camera", "photo", "image", "video", "music", "headphone", "play", "microphone", "film"],
    "symbol": ["circle", "square", "triangle", "heart", "plus", "minus", "equals", "question", "check"],
    "time": ["clock", "calendar", "time", "hourglass", "stopwatch", "timer", "watch"],
    "nature": ["fire", "bolt", "sun", "leaf", "tree", "seedling", "water", "droplet", "wind", "snow", "cloud", "moon"],
}
CATEGORY_LABELS = {
    "money": "💰 پول و ارز", "chart": "📊 سرمایه و نمودار", "gems": "🥇 طلا و جواهر",
    "building": "🏢 ملک و ساختمان", "transport": "🚗 حمل و نقل", "goods": "📦 کالا",
    "business": "💼 کسب و کار", "file": "📁 فایل و سند", "user": "👤 کاربر",
    "system": "⚙️ تنظیمات", "media": "🎬 رسانه", "symbol": "🔷 نماد",
    "time": "⏰ زمان", "nature": "🌿 طبیعت", "other": "📌 سایر",
}


def _secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.environ.get(name, ""))


APP_PASSWORD = _secret("APP_PASSWORD")
GITHUB_TOKEN = _secret("GITHUB_TOKEN")
GITHUB_REPO = _secret("GITHUB_REPO")
AUTH_TOKEN = hashlib.sha256((APP_PASSWORD + "_salt_v2_2024").encode()).hexdigest() if APP_PASSWORD else ""


def categorize_icon(icon_class: str, label: str) -> list[str]:
    text = f"{icon_class} {label}".lower()
    categories = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            categories.append(category)
    return categories or ["other"]


@st.cache_data(ttl=86400, show_spinner=False)
def load_fa_icons(cache_v: str = "v8") -> list[dict]:
    try:
        response = requests.get(
            "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/metadata/icons.json",
            timeout=15,
        )
        if response.status_code == 200:
            icons = []
            for name, info in response.json().items():
                if "solid" not in info.get("free", []):
                    continue
                label = info.get("label", name)
                css_class = f"fa-{name}"
                icons.append({"class": css_class, "label": label, "categories": categorize_icon(css_class, label)})
            if icons:
                return sorted(icons, key=lambda item: item["label"].lower())
    except Exception:
        pass
    return [
        {"class": item["class"], "label": item["label"], "categories": categorize_icon(item["class"], item["label"])}
        for item in FALLBACK_ICONS
    ]


def icon_emoji(fa_class: str) -> str:
    emojis = {
        "fa-folder": "📁", "fa-coins": "🪙", "fa-wallet": "👛", "fa-dollar-sign": "💲",
        "fa-building-columns": "🏦", "fa-gem": "💎", "fa-crown": "👑", "fa-house": "🏠",
        "fa-car": "🚗", "fa-chart-line": "📈", "fa-chart-pie": "📊", "fa-bitcoin-sign": "₿",
        "fa-briefcase": "💼", "fa-store": "🏪", "fa-sack-dollar": "💰", "fa-fire": "🔥",
        "fa-bolt": "⚡", "fa-box": "📦", "fa-gear": "⚙️", "fa-circle-plus": "➕",
        "fa-scale-balanced": "⚖️",
    }
    return emojis.get(fa_class, "📁")


def now_tehran() -> datetime:
    return datetime.now(TEHRAN).replace(tzinfo=None)


def today_jalali_str() -> str:
    return jdatetime.date.today().strftime("%Y/%m/%d")


def iso_to_jalali(iso_str: str, with_time: bool = True) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(TEHRAN).replace(tzinfo=None)
        jalali = jdatetime.datetime.fromgregorian(datetime=dt)
        return jalali.strftime("%Y/%m/%d - %H:%M") if with_time else jalali.strftime("%Y/%m/%d")
    except Exception:
        return "—"


def parse_jalali(value: str):
    try:
        parts = value.strip().replace("-", "/").replace(".", "/").split("/")
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


def _compact_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _decompress_if_needed(raw_bytes: bytes) -> bytes:
    if len(raw_bytes) >= 2 and raw_bytes[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(raw_bytes)
        except Exception:
            pass
    return raw_bytes


def _short_id() -> str:
    return f"{int(datetime.now().timestamp() * 1000)}{uuid.uuid4().hex[:6]}"


def github_headers() -> dict[str, str]:
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}


@st.cache_data(ttl=60, show_spinner=False)
def check_github_status(token: str, repo: str):
    if not token and not repo:
        return "no_config", "تنظیم نشده"
    if not token:
        return "no_token", "توکن ندارد"
    if not repo:
        return "no_repo", "مخزن ندارد"
    try:
        response = requests.get(f"https://api.github.com/repos/{repo}", headers=github_headers(), timeout=8)
        if response.status_code == 200:
            return "ok", f"متصل به {repo}"
        if response.status_code == 401:
            return "error", "توکن نامعتبر (401)"
        if response.status_code == 404:
            return "error", "مخزن یافت نشد (404)"
        return "error", f"HTTP {response.status_code}"
    except Exception as exc:
        return "error", f"خطای شبکه: {str(exc)[:40]}"


def load_local_file():
    try:
        if DATA_FILE.exists():
            return json.loads(_decompress_if_needed(DATA_FILE.read_bytes()).decode("utf-8"))
    except Exception:
        pass
    return None


def save_local_file(data) -> bool:
    try:
        DATA_FILE.write_text(_compact_json(data), encoding="utf-8")
        return True
    except Exception:
        return False


def _github_content_bytes(info: dict) -> bytes | None:
    content_b64 = info.get("content", "")
    if content_b64:
        return base64.b64decode(content_b64)
    raw_url = info.get("download_url") or f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_FILE_PATH}"
    response = requests.get(raw_url, timeout=30)
    return response.content if response.status_code == 200 else None


def load_github_file():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        response = requests.get(url, headers=github_headers(), timeout=20)
        if response.status_code != 200:
            return None
        content = _github_content_bytes(response.json())
        return json.loads(_decompress_if_needed(content).decode("utf-8")) if content else None
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
            sha = response.json()["sha"]
        elif response.status_code == 401:
            return False, "توکن نامعتبر (401)"
    except Exception as exc:
        return False, f"خطای شبکه: {str(exc)[:50]}"
    raw = _compact_json(data).encode("utf-8")
    compressed = gzip.compress(raw, mtime=0)
    payload = {
        "message": f"update {today_jalali_str()} {datetime.now().strftime('%H:%M')} ({len(compressed):,}B gz)",
        "content": base64.b64encode(compressed).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    try:
        response = requests.put(url, headers=github_headers(), json=payload, timeout=30)
        messages = {401: "توکن نامعتبر (401)", 403: "دسترسی write ندارد (403)", 404: "مخزن یافت نشد (404)", 409: "تضاد SHA (409)"}
        if response.status_code in (200, 201):
            return True, ""
        return False, messages.get(response.status_code, f"HTTP {response.status_code}")
    except Exception as exc:
        return False, f"خطای شبکه: {str(exc)[:50]}"


def verify_github_save(expected_data):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GitHub تنظیم نشده", None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        response = requests.get(url, headers=github_headers(), timeout=20)
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}", None
        info = response.json()
        content = _github_content_bytes(info)
        if not content:
            return False, "خواندن ناموفق", info.get("sha", "")[:8]
        github_data = json.loads(_decompress_if_needed(content).decode("utf-8"))
        if github_data.get("last_saved") != expected_data.get("last_saved"):
            return False, "timestamp متفاوت", info.get("sha", "")[:8]
        kind = "gzip" if content[:2] == b"\x1f\x8b" else "plain"
        return True, f"تأیید شد — {info.get('size', 0):,}B ({kind})", info.get("sha", "")[:8]
    except Exception as exc:
        return False, str(exc)[:50], None


def _fresh_data() -> dict:
    return {
        "assets": [], "usd_rates": [], "gold_funds": [], "synthetic_pairs": [],
        "settings": {
            "font": "vazirmatn", "nav_icons": {k: v.copy() for k, v in DEFAULT_NAV_ICONS.items()},
            "custom_fonts": {}, "dark_mode": False, "auto_theme": False,
            "day_start": "07:00", "night_start": "19:00", "nav_order": DEFAULT_NAV_ORDER.copy(),
        },
    }


def migrate_data(data):
    """Migrate old backups in-place without renaming or dropping existing fields."""
    if not isinstance(data, dict) or not data:
        return _fresh_data()
    if not isinstance(data.get("usd_rates"), list):
        data["usd_rates"] = []
        old_rate = data.get("usd_rate")
        if old_rate:
            data["usd_rates"].append({
                "id": _short_id(), "rate": old_rate, "note": "منتقل‌شده",
                "created_at": datetime.now().isoformat(), "created_at_jalali": today_jalali_str(),
            })
        data.pop("usd_rate", None)
    if isinstance(data.get("journals"), list):
        data.setdefault("assets", [])
        for journal in data["journals"]:
            asset_id = journal.get("id") or _short_id()
            created_iso = journal.get("created_at_gregorian") or journal.get("created_at") or datetime.now().isoformat()
            created_jalali = journal.get("created_at_jalali") or iso_to_jalali(created_iso, with_time=False)
            data["assets"].append({
                "id": asset_id, "name": journal.get("asset_name", "بدون نام"), "icon": "fa-folder",
                "color": "#3b82f6", "overview_emoji": "", "currency": journal.get("currency", "IRR"),
                "created_at_gregorian": created_iso, "created_at_jalali": created_jalali,
                "records": [{"id": f"{asset_id}_r", "date_gregorian": created_iso, "date_jalali": created_jalali,
                             "quantity": journal.get("amount", 0), "unit_price": 1, "note": "منتقل‌شده"}],
            })
        data.pop("journals", None)
    for key in ("assets", "usd_rates", "gold_funds", "synthetic_pairs"):
        if not isinstance(data.get(key), list):
            data[key] = []
    settings = data.setdefault("settings", {})
    settings.setdefault("font", "vazirmatn")
    settings.setdefault("dark_mode", False)
    settings.setdefault("auto_theme", False)
    settings.setdefault("day_start", "07:00")
    settings.setdefault("night_start", "19:00")
    settings.setdefault("custom_fonts", {})
    nav_icons = settings.setdefault("nav_icons", {})
    for key, value in DEFAULT_NAV_ICONS.items():
        nav_icons.setdefault(key, value.copy())
    order = settings.get("nav_order")
    if not isinstance(order, list):
        order = []
    settings["nav_order"] = [key for key in order if key in DEFAULT_NAV_ORDER] + [key for key in DEFAULT_NAV_ORDER if key not in order]
    seen = set()
    data["assets"] = [asset for asset in data["assets"] if asset.get("id") and not (asset["id"] in seen or seen.add(asset["id"]))]
    for asset in data["assets"]:
        if not isinstance(asset.get("icon"), str) or not asset["icon"].startswith("fa-"):
            asset["icon"] = "fa-folder"
        asset.setdefault("color", "#3b82f6")
        asset.setdefault("overview_emoji", "")
        asset.setdefault("records", [])
    seen_gold = set()
    data["gold_funds"] = [fund for fund in data["gold_funds"] if fund.get("id") and not (fund["id"] in seen_gold or seen_gold.add(fund["id"]))]
    for fund in data["gold_funds"]:
        fund.setdefault("records", [])
        fund.setdefault("icon", "🥇")
    return data


def load_all():
    local = load_local_file()
    github = load_github_file()
    local_has = local and (local.get("assets") or local.get("usd_rates") or local.get("gold_funds"))
    github_has = github and (github.get("assets") or github.get("usd_rates") or github.get("gold_funds"))
    if local_has and github_has:
        local_saved, github_saved = local.get("last_saved", ""), github.get("last_saved", "")
        chosen = (local if local_saved > github_saved else github) if (local_saved and github_saved) else github
        save_local_file(chosen)
        return migrate_data(chosen)
    if github_has:
        save_local_file(github)
        return migrate_data(github)
    return migrate_data(local if local_has else {})


def save_all(data, verify: bool = True) -> bool:
    now = now_tehran()
    data["last_saved"] = now.isoformat()
    data["last_saved_jalali"] = jdatetime.datetime.fromgregorian(datetime=now).strftime("%Y/%m/%d - %H:%M")
    local_ok = save_local_file(data)
    github_ok, github_error = save_github_file(data)
    if github_ok:
        if verify:
            verified, message, _ = verify_github_save(data)
            if verified:
                st.toast("✅ ذخیره و تأیید شد", icon="✅")
                return True
            st.warning(f"⚠️ ذخیره شد ولی تأیید ناقص: {message}")
            return False
        st.toast("✅ ذخیره شد", icon="✅")
        return True
    if local_ok:
        st.warning(f"⚠️ فقط در فایل محلی ذخیره شد؛ GitHub: {github_error}")
    else:
        st.error(f"❌ هیچ جا ذخیره نشد! {github_error}")
    return local_ok


def get_settings(data):
    settings = data.get("settings") or {}
    return {
        "font": settings.get("font", "vazirmatn"),
        "nav_icons": settings.get("nav_icons", DEFAULT_NAV_ICONS),
        "custom_fonts": settings.get("custom_fonts", {}) or {},
        "dark_mode": bool(settings.get("dark_mode", False)),
        "auto_theme": bool(settings.get("auto_theme", False)),
        "day_start": settings.get("day_start", "07:00"),
        "night_start": settings.get("night_start", "19:00"),
        "nav_order": settings.get("nav_order", DEFAULT_NAV_ORDER),
    }


def get_effective_theme(data, now: datetime | None = None) -> str:
    settings = get_settings(data)
    if not settings["auto_theme"]:
        return "dark" if settings["dark_mode"] else "light"
    current = now or now_tehran()
    minutes = current.hour * 60 + current.minute

    def parse_time(value: str) -> int:
        try:
            hour, minute = map(int, value.split(":"))
            return hour * 60 + minute
        except Exception:
            return 0

    day_start = parse_time(settings["day_start"])
    night_start = parse_time(settings["night_start"])
    is_day = day_start <= minutes < night_start if day_start < night_start else minutes >= day_start or minutes < night_start
    return "light" if is_day else "dark"


def asset_icon(asset):
    icon = asset.get("icon", "fa-folder")
    return icon if isinstance(icon, str) and icon.startswith("fa-") else "fa-folder"


def asset_color(asset):
    return asset.get("color", "#3b82f6")


def asset_overview_emoji(asset):
    return (asset.get("overview_emoji") or "").strip() or icon_emoji(asset_icon(asset))


def currency_label(currency):
    return "ریال" if currency == "IRR" else "دلار"


def get_current_usd_rate(data):
    rates = data.get("usd_rates", [])
    if not rates:
        return None, None
    latest = max(rates, key=lambda item: item.get("created_at", ""))
    return latest["rate"], latest.get("created_at_jalali", "—")


def latest_record(asset):
    records = asset.get("records", [])
    return max(records, key=lambda record: (record.get("date_gregorian", ""), record.get("id", ""))) if records else None


def compute_asset_value(asset, usd_rate):
    record = latest_record(asset)
    if not record:
        return 0, None, None
    value = float(record["quantity"]) * float(record["unit_price"])
    usd_value = value / usd_rate if asset["currency"] == "IRR" and usd_rate and usd_rate > 0 else value if asset["currency"] == "USD" else None
    return value, usd_value, record


def sync_usd_rates_to_gold_funds(data):
    rates = sorted(data.get("usd_rates", []), key=lambda item: item.get("created_at", ""))
    updated = missing = 0
    for fund in data.get("gold_funds", []):
        for record in fund.get("records", []):
            record_date = record.get("date_gregorian", "")[:10]
            if not record_date:
                continue
            rate_at = None
            for usd_rate in rates:
                if usd_rate.get("created_at", "")[:10] <= record_date:
                    rate_at = usd_rate["rate"]
                else:
                    break
            if rate_at is not None:
                if record.get("usd_rate_used") != rate_at:
                    record["usd_rate_used"] = rate_at
                    updated += 1
            else:
                missing += 1
    return updated, missing


def build_portfolio_timeline(data):
    assets = data.get("assets", [])
    rates = sorted(data.get("usd_rates", []), key=lambda item: item.get("created_at", ""))
    dates = {record["date_gregorian"][:10] for asset in assets for record in asset.get("records", []) if record.get("date_gregorian")}
    dates |= {rate["created_at"][:10] for rate in rates if rate.get("created_at")}
    rows = []
    for date in sorted(dates):
        rate_at = None
        for usd_rate in rates:
            if usd_rate.get("created_at", "")[:10] <= date:
                rate_at = usd_rate["rate"]
            else:
                break
        total_irr = total_usd = 0.0
        for asset in assets:
            records = [record for record in asset.get("records", []) if record.get("date_gregorian", "")[:10] <= date]
            if not records:
                continue
            latest = max(records, key=lambda record: record.get("date_gregorian", ""))
            value = float(latest["quantity"]) * float(latest["unit_price"])
            if asset["currency"] == "IRR":
                total_irr += value
                if rate_at and rate_at > 0:
                    total_usd += value / rate_at
            else:
                total_usd += value
                if rate_at and rate_at > 0:
                    total_irr += value * rate_at
        rows.append({"date_gregorian": date, "date_jalali": iso_to_jalali(date + "T00:00:00", False), "total_irr": total_irr, "total_usd": total_usd})
    return pd.DataFrame(rows)


def unit_usd_equivalent(record):
    rate = float(record.get("usd_rate_used", 0) or 0)
    return float(record["unit_price"]) / rate if rate > 0 else None


def gold_gram_per_unit(record):
    ounce = float(record.get("ounce_price_usd", 0) or 0)
    rate = float(record.get("usd_rate_used", 0) or 0)
    price = float(record.get("unit_price", 0) or 0)
    return (price * 31.1035) / (ounce * rate) if ounce > 0 and rate > 0 and price > 0 else None


def gold_fund_analytics(fund):
    records = sorted(fund.get("records", []), key=lambda record: record.get("date_gregorian", ""))
    rows, first_usd = [], None
    for index, record in enumerate(records):
        usd_equivalent = unit_usd_equivalent(record)
        if first_usd is None and usd_equivalent:
            first_usd = usd_equivalent
        ounce_change = usd_change = None
        if index > 0:
            previous = records[index - 1]
            if float(previous.get("ounce_price_usd", 0) or 0) > 0:
                ounce_change = (float(record["ounce_price_usd"]) / float(previous["ounce_price_usd"]) - 1) * 100
            if float(previous.get("usd_rate_used", 0) or 0) > 0 and float(record.get("usd_rate_used", 0) or 0) > 0:
                usd_change = (float(record["usd_rate_used"]) / float(previous["usd_rate_used"]) - 1) * 100
        usd_return = (usd_equivalent / first_usd - 1) * 100 if first_usd and usd_equivalent else None
        rows.append({"record": record, "usd_equivalent": usd_equivalent, "usd_return_pct": usd_return,
                     "ounce_change_pct": ounce_change, "usd_change_pct": usd_change, "gram_per_unit": gold_gram_per_unit(record)})
    return rows


def dollar_trap_analysis(fund, days=30):
    records = sorted(fund.get("records", []), key=lambda record: record.get("date_gregorian", ""))
    if len(records) < 2:
        return None
    last = records[-1]
    try:
        last_date = datetime.fromisoformat(last.get("date_gregorian", "")[:10] + "T00:00:00")
        cutoff = (last_date - timedelta(days=days)).strftime("%Y-%m-%d")
    except Exception:
        return None
    older = next((record for record in records if record.get("date_gregorian", "")[:10] >= cutoff), None)
    if not older or older.get("id") == last.get("id"):
        return None
    ounce_change = (float(last["ounce_price_usd"]) / float(older["ounce_price_usd"]) - 1) * 100 if float(older.get("ounce_price_usd", 0) or 0) > 0 else 0
    usd_change = (float(last["usd_rate_used"]) / float(older["usd_rate_used"]) - 1) * 100 if float(older.get("usd_rate_used", 0) or 0) > 0 else 0
    return {"usd_change": usd_change, "ounce_change": ounce_change, "gap": usd_change - ounce_change,
            "days": days, "older_date": older.get("date_jalali"), "last_date": last.get("date_jalali")}


def ounce_signal(fund, days=90):
    records = sorted(fund.get("records", []), key=lambda record: record.get("date_gregorian", ""))
    if len(records) < 3:
        return "⚪ داده کافی نیست"
    last = records[-1]
    try:
        last_date = datetime.fromisoformat(last.get("date_gregorian", "")[:10] + "T00:00:00")
        cutoff = (last_date - timedelta(days=days)).strftime("%Y-%m-%d")
    except Exception:
        return "⚪"
    recent = [record for record in records if record.get("date_gregorian", "")[:10] >= cutoff and float(record.get("ounce_price_usd", 0) or 0) > 0]
    if len(recent) < 3:
        recent = [record for record in records if float(record.get("ounce_price_usd", 0) or 0) > 0]
    if not recent or float(last.get("ounce_price_usd", 0) or 0) <= 0:
        return "⚪ داده انس کافی نیست"
    average = sum(float(record["ounce_price_usd"]) for record in recent) / len(recent)
    difference = (float(last["ounce_price_usd"]) / average - 1) * 100 if average else 0
    if difference > 5:
        return f"🔴 انس {difference:+.1f}% بالای میانگین {days}روزه — فروش"
    if difference > 0:
        return f"🟡 انس {difference:+.1f}% بالای میانگین — کمی فروش"
    if difference > -5:
        return f"🟢 انس {difference:+.1f}% زیر میانگین — کمی خرید"
    return f"🟢🟢 انس {difference:+.1f}% زیر میانگین — خرید قوی"


def instrument_options(data):
    options = []
    for asset in data.get("assets", []):
        if asset.get("records"):
            options.append({"id": f"asset:{asset['id']}", "label": asset["name"], "kind": "دارایی", "color": asset_color(asset)})
    for fund in data.get("gold_funds", []):
        if fund.get("records"):
            options.append({"id": f"gold:{fund['id']}", "label": f"{fund.get('icon', '🥇')} {fund['name']}", "kind": "صندوق طلا", "color": "#eab308"})
    if data.get("usd_rates"):
        options.append({"id": "usd", "label": "💵 دلار", "kind": "نرخ ارز", "color": "#3b82f6"})
    return options


def instrument_label(data, instrument_id: str) -> str:
    return next((item["label"] for item in instrument_options(data) if item["id"] == instrument_id), instrument_id)


def _rate_at(data, date: str):
    rate = None
    for item in sorted(data.get("usd_rates", []), key=lambda row: row.get("created_at", "")):
        if item.get("created_at", "")[:10] <= date:
            rate = float(item.get("rate", 0) or 0)
        else:
            break
    return rate if rate and rate > 0 else None


def instrument_history(data, instrument_id: str):
    """Return chronological unit prices converted to IRR at each record's own date."""
    if instrument_id == "usd":
        return sorted([{"date": row["created_at"][:10], "date_jalali": row.get("created_at_jalali") or iso_to_jalali(row["created_at"], False),
                        "price_irr": float(row["rate"]), "source": row} for row in data.get("usd_rates", []) if float(row.get("rate", 0) or 0) > 0], key=lambda row: row["date"])
    kind, _, raw_id = instrument_id.partition(":")
    if kind == "asset":
        asset = next((item for item in data.get("assets", []) if item["id"] == raw_id), None)
        if not asset:
            return []
        rows = []
        for record in asset.get("records", []):
            date = record.get("date_gregorian", "")[:10]
            price = float(record.get("unit_price", 0) or 0)
            if asset.get("currency") == "USD":
                rate = _rate_at(data, date)
                price = price * rate if rate else 0
            if date and price > 0:
                rows.append({"date": date, "date_jalali": record.get("date_jalali") or iso_to_jalali(date + "T00:00:00", False), "price_irr": price, "source": record})
        return sorted(rows, key=lambda row: row["date"])
    if kind == "gold":
        fund = next((item for item in data.get("gold_funds", []) if item["id"] == raw_id), None)
        if not fund:
            return []
        return sorted([{"date": record["date_gregorian"][:10], "date_jalali": record.get("date_jalali") or iso_to_jalali(record["date_gregorian"], False),
                        "price_irr": float(record["unit_price"]), "source": record} for record in fund.get("records", [])
                       if record.get("date_gregorian") and float(record.get("unit_price", 0) or 0) > 0], key=lambda row: row["date"])
    return []


def build_synthetic_series(data, left_id: str, right_id: str):
    left_history, right_history = instrument_history(data, left_id), instrument_history(data, right_id)
    dates = sorted({row["date"] for row in left_history + right_history})

    def value_at(history, date):
        found = None
        for row in history:
            if row["date"] <= date:
                found = row
            else:
                break
        return found

    rows = []
    for date in dates:
        left, right = value_at(left_history, date), value_at(right_history, date)
        if not left or not right or left["price_irr"] <= 0 or right["price_irr"] <= 0:
            continue
        rows.append({"date_gregorian": date, "date_jalali": left["date_jalali"] if left["date"] == date else iso_to_jalali(date + "T00:00:00", False),
                     "left_price_irr": left["price_irr"], "right_price_irr": right["price_irr"], "ratio": left["price_irr"] / right["price_irr"]})
    if not rows:
        return []
    base_ratio, base_left, base_right = rows[0]["ratio"], rows[0]["left_price_irr"], rows[0]["right_price_irr"]
    for row in rows:
        row["ratio_index"] = row["ratio"] / base_ratio * 100
        row["left_index"] = row["left_price_irr"] / base_left * 100
        row["right_index"] = row["right_price_irr"] / base_right * 100
    return rows


def compute_monthly_returns(data, year_jalali: int):
    """Original IRR unit-price monthly return algorithm, including gold funds."""
    rates = sorted(data.get("usd_rates", []), key=lambda item: item.get("created_at", ""))

    def rate_at(date):
        rate = None
        for item in rates:
            if item.get("created_at", "")[:10] <= date:
                candidate = float(item.get("rate", 0) or 0)
                if candidate > 0:
                    rate = candidate
            else:
                break
        return rate

    def price_irr(record, item_type, currency):
        price = float(record.get("unit_price", 0) or 0)
        if price <= 0:
            return None
        if item_type == "gold" or currency == "IRR":
            return price
        rate = rate_at(record.get("date_gregorian", "")[:10])
        return price * rate if rate else None

    items = [{"id": f"asset_{asset['id']}", "name": asset["name"], "type": "asset", "currency": asset.get("currency", "IRR"), "records": asset.get("records", [])} for asset in data.get("assets", [])]
    items += [{"id": f"gold_{fund['id']}", "name": f"🥇 {fund['name']}", "type": "gold", "currency": "IRR", "records": fund.get("records", [])} for fund in data.get("gold_funds", [])]
    results = {}
    for item in items:
        records = sorted(item["records"], key=lambda record: record.get("date_gregorian", ""))
        monthly = {}
        for month in range(1, 13):
            try:
                start = jdatetime.date(year_jalali, month, 1).togregorian().strftime("%Y-%m-%d")
                end_date = jdatetime.date(year_jalali + 1, 1, 1) if month == 12 else jdatetime.date(year_jalali, month + 1, 1)
                end = end_date.togregorian().strftime("%Y-%m-%d")
            except Exception:
                monthly[month] = None
                continue
            month_records = [record for record in records if start <= record.get("date_gregorian", "")[:10] < end]
            if not month_records:
                monthly[month] = None
                continue
            before = [record for record in records if record.get("date_gregorian", "")[:10] < start]
            start_record = before[-1] if before else month_records[0]
            end_record = month_records[-1]
            if start_record is end_record:
                monthly[month] = None
                continue
            start_price = price_irr(start_record, item["type"], item["currency"])
            end_price = price_irr(end_record, item["type"], item["currency"])
            if not start_price or not end_price or start_price <= 0:
                monthly[month] = None
                continue
            quantity = float(start_record.get("quantity", 0) or 0)
            monthly[month] = {"return_pct": (end_price / start_price - 1) * 100,
                              "profit_irr": (end_price - start_price) * quantity,
                              "start_price_irr": start_price, "end_price_irr": end_price, "start_quantity": quantity}
        results[item["id"]] = {"name": item["name"], "monthly": monthly, "type": item["type"]}
    return results


def render_html_table(df: pd.DataFrame, dark: bool = False):
    bg_head = "#161b22" if dark else "#f3f4f6"
    bg_odd = "#0d1117" if dark else "#f9fafb"
    bg_even = "#161b22" if dark else "#ffffff"
    border = "#30363d" if dark else "#e5e7eb"
    text_color = "#e6edf3" if dark else "#1f2937"
    html = f'<div style="overflow-x:auto;margin:8px 0"><table style="width:100%;border-collapse:collapse;direction:rtl;font-family:inherit;font-size:.9rem;color:{text_color}"><thead><tr style="background:{bg_head};font-weight:bold">'
    for column in df.columns:
        html += f'<th style="padding:10px 12px;text-align:right;border-bottom:2px solid {border};white-space:nowrap">{column}</th>'
    html += "</tr></thead><tbody>"
    for index, row in df.iterrows():
        html += f'<tr style="background:{bg_odd if index % 2 == 0 else bg_even}">'
        for value in row:
            html += f'<td style="padding:8px 12px;text-align:right;border-bottom:1px solid {border}">{value}</td>'
        html += "</tr>"
    st.markdown(html + "</tbody></table></div>", unsafe_allow_html=True)


def plotly_layout(fig, dark=False, height=500):
    fig.update_layout(
        font=dict(family="Vazirmatn, Tahoma", size=12, color="#e6edf3" if dark else "#1f2937"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=height,
        hovermode="x unified", margin=dict(t=45, b=30, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )
    return fig
