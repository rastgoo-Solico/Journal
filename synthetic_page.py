"""User-defined synthetic instrument pairs built from existing historical data."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from financial_core import (
    _short_id, build_synthetic_series, get_effective_theme, instrument_history,
    instrument_label, instrument_options, plotly_layout, render_html_table, save_all,
)


def _instrument_key(pair, side):
    kind = pair.get(f"{side}_type", "asset")
    raw_id = pair.get(f"{side}_id", "")
    return "usd" if kind == "usd" else f"{kind}:{raw_id}"


def _persist(data):
    st.session_state.data = data
    save_all(data)


def render_synthetic_page(data):
    st.header("⚖️ جفت ارز مصنوعی")
    st.caption("نسبت قیمت دو دارایی را بر مبنای ریال و با استفاده از داده‌های واقعی ثبت‌شده بسازید.")
    options = instrument_options(data)
    option_ids = [item["id"] for item in options]
    labels = {item["id"]: f"{item['label']} — {item['kind']}" for item in options}

    with st.container(border=True):
        st.subheader("➕ ساخت جفت جدید")
        st.markdown("مثال‌ها: **صندوق طلا / دلار**، **وبملت / صندوق طلا** یا هر ترکیب دیگری که برای هر دو سمت داده ثبت کرده‌اید.")
        if len(options) < 2:
            st.info("برای ساخت جفت، حداقل دو ابزار دارای رکورد لازم است. ابتدا دارایی، صندوق طلا یا نرخ دلار ثبت کنید.")
        else:
            col1, col2 = st.columns(2)
            left_key = col1.selectbox("دارایی صورت (سمت اول)", option_ids, format_func=lambda key: labels.get(key, key), key="synthetic_left_new")
            right_default = 1 if len(option_ids) > 1 else 0
            right_key = col2.selectbox("دارایی مخرج (سمت دوم)", option_ids, index=right_default, format_func=lambda key: labels.get(key, key), key="synthetic_right_new")
            left_history = instrument_history(data, left_key)
            right_history = instrument_history(data, right_key)
            preview1, preview2 = st.columns(2)
            preview1.caption(f"آخرین قیمت {instrument_label(data, left_key)}: **{left_history[-1]['price_irr']:,.2f} ریال**" if left_history else "داده‌ای نیست")
            preview2.caption(f"آخرین قیمت {instrument_label(data, right_key)}: **{right_history[-1]['price_irr']:,.2f} ریال**" if right_history else "داده‌ای نیست")
            left_kind, _, left_id = left_key.partition(":")
            right_kind, _, right_id = right_key.partition(":")
            if left_key == "usd":
                left_kind, left_id = "usd", "usd"
            if right_key == "usd":
                right_kind, right_id = "usd", "usd"
            duplicate = any(_instrument_key(pair, "left") == left_key and _instrument_key(pair, "right") == right_key for pair in data.get("synthetic_pairs", []))
            if duplicate:
                st.info("این جفت قبلاً ساخته شده و در فهرست پایین قابل انتخاب است.")
            if st.button("💾 ساخت جفت مصنوعی", use_container_width=True, disabled=left_key == right_key or duplicate):
                pair = {
                    "id": _short_id(), "name": f"{instrument_label(data, left_key)} / {instrument_label(data, right_key)}",
                    "left_type": left_kind, "left_id": left_id, "right_type": right_kind, "right_id": right_id,
                    "created_at": datetime.now().isoformat(),
                }
                data.setdefault("synthetic_pairs", []).append(pair)
                _persist(data)
                st.session_state.selected_synthetic_pair = pair["id"]
                st.rerun()
            if left_key == right_key:
                st.warning("دو سمت جفت باید متفاوت باشند.")

    pairs = data.get("synthetic_pairs", [])
    if not pairs:
        st.info("هنوز جفتی ساخته نشده است.")
        return
    st.subheader("📚 جفت‌های ذخیره‌شده")
    pair_ids = [pair["id"] for pair in pairs]
    selected_id = st.session_state.get("selected_synthetic_pair")
    if selected_id not in pair_ids:
        selected_id = pair_ids[0]
    selected_id = st.selectbox("انتخاب جفت", pair_ids, index=pair_ids.index(selected_id), format_func=lambda pair_id: next((pair["name"] for pair in pairs if pair["id"] == pair_id), pair_id), key="synthetic_pair_selector")
    st.session_state.selected_synthetic_pair = selected_id
    pair = next(pair for pair in pairs if pair["id"] == selected_id)
    left_key, right_key = _instrument_key(pair, "left"), _instrument_key(pair, "right")
    left_label, right_label = instrument_label(data, left_key), instrument_label(data, right_key)
    action1, action2 = st.columns([1, 4])
    if action1.button("🗑️ حذف جفت", key=f"delete_pair_{pair['id']}"):
        data["synthetic_pairs"] = [item for item in pairs if item["id"] != pair["id"]]
        st.session_state.pop("selected_synthetic_pair", None)
        _persist(data)
        st.rerun()
    if action2.button("🔁 ساخت جفت معکوس", key=f"reverse_pair_{pair['id']}"):
        reversed_exists = any(_instrument_key(item, "left") == right_key and _instrument_key(item, "right") == left_key for item in pairs)
        if not reversed_exists:
            reversed_pair = dict(pair)
            reversed_pair.update({
                "id": _short_id(), "name": f"{right_label} / {left_label}",
                "left_type": pair["right_type"], "left_id": pair["right_id"],
                "right_type": pair["left_type"], "right_id": pair["left_id"], "created_at": datetime.now().isoformat(),
            })
            data["synthetic_pairs"].append(reversed_pair)
            st.session_state.selected_synthetic_pair = reversed_pair["id"]
            _persist(data)
            st.rerun()
        st.info("جفت معکوس قبلاً ساخته شده است.")

    series = build_synthetic_series(data, left_key, right_key)
    if not series:
        st.warning("هیچ تاریخ مشترک معتبری برای این جفت وجود ندارد. برای هر دو سمت و در صورت نیاز نرخ دلار، دادهٔ بیشتری ثبت کنید.")
        return
    dark = get_effective_theme(data) == "dark"
    first, last = series[0], series[-1]
    change = (last["ratio"] / first["ratio"] - 1) * 100
    st.subheader(f"📊 {left_label} / {right_label}")
    st.caption("نسبت = قیمت ریالی هر واحد سمت اول ÷ قیمت ریالی هر واحد سمت دوم. برای روزهای بین دو ثبت، آخرین قیمت معتبر همان ابزار حفظ می‌شود.")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("نسبت فعلی", f"{last['ratio']:,.6f}")
    col2.metric("تغییر نسبت از مبنا", f"{change:+.2f}%")
    col3.metric("تعداد نقاط", len(series))
    col4.metric("آخرین تاریخ", last["date_jalali"])

    mode = st.radio("نمایش نمودار", ["نسبت واقعی جفت", "شاخص نسبت (پایه ۱۰۰)"], horizontal=True, key=f"pair_mode_{pair['id']}")
    ratio_values = [row["ratio"] if mode == "نسبت واقعی جفت" else row["ratio_index"] for row in series]
    fig_ratio = go.Figure()
    fig_ratio.add_trace(go.Scatter(x=[row["date_jalali"] for row in series], y=ratio_values, mode="lines+markers", name=pair["name"], line=dict(color="#8b5cf6", width=3), marker=dict(size=7)))
    plotly_layout(fig_ratio, dark, height=430)
    fig_ratio.update_yaxes(title="نسبت جفت" if mode == "نسبت واقعی جفت" else "شاخص (پایه=۱۰۰)")
    fig_ratio.update_xaxes(title="تاریخ")
    st.plotly_chart(fig_ratio, use_container_width=True)

    st.subheader("📈 مقایسهٔ دو دارایی (نرمال‌شده به ۱۰۰)")
    st.caption("این نمودار مشخص می‌کند تغییر نسبت بیشتر از کدام سمت جفت آمده است.")
    fig_compare = go.Figure()
    fig_compare.add_trace(go.Scatter(x=[row["date_jalali"] for row in series], y=[row["left_index"] for row in series], mode="lines+markers", name=left_label, line=dict(color="#3b82f6", width=3)))
    fig_compare.add_trace(go.Scatter(x=[row["date_jalali"] for row in series], y=[row["right_index"] for row in series], mode="lines+markers", name=right_label, line=dict(color="#10b981", width=3)))
    fig_compare.add_trace(go.Scatter(x=[row["date_jalali"] for row in series], y=[row["ratio_index"] for row in series], mode="lines", name="جفت مصنوعی", line=dict(color="#8b5cf6", width=2, dash="dot")))
    plotly_layout(fig_compare, dark, height=460)
    fig_compare.update_yaxes(title="شاخص (پایه=۱۰۰)")
    st.plotly_chart(fig_compare, use_container_width=True)

    if last["ratio_index"] > 105:
        st.success(f"سمت اول نسبت به سمت دوم **{last['ratio_index']-100:+.2f}%** قوی‌تر شده است.")
    elif last["ratio_index"] < 95:
        st.warning(f"سمت اول نسبت به سمت دوم **{last['ratio_index']-100:+.2f}%** ضعیف‌تر شده است.")
    else:
        st.info("نسبت جفت نزدیک به نقطهٔ مبنا است.")

    st.subheader("📋 تاریخچهٔ جفت")
    rows = [{"تاریخ": row["date_jalali"], f"قیمت {left_label} (ریال)": f"{row['left_price_irr']:,.2f}",
             f"قیمت {right_label} (ریال)": f"{row['right_price_irr']:,.2f}", "نسبت": f"{row['ratio']:,.6f}",
             "شاخص جفت": f"{row['ratio_index']:,.2f}", "تغییر از مبنا": f"{row['ratio_index']-100:+.2f}%"} for row in reversed(series)]
    render_html_table(pd.DataFrame(rows), dark)
