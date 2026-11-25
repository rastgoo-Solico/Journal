"""Overview, journal, USD and monthly-return pages for the Streamlit app."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from financial_core import (
    _short_id, asset_color, asset_icon, asset_overview_emoji, build_portfolio_timeline,
    compute_asset_value, compute_monthly_returns, currency_label, fmt_num,
    get_current_usd_rate, get_effective_theme, iso_to_jalali, jalali_to_gregorian_iso,
    load_fa_icons, parse_jalali, plotly_layout, render_html_table, save_all,
    sync_usd_rates_to_gold_funds, today_jalali_str,
)

MONTH_NAMES = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]


def _persist(data):
    st.session_state.data = data
    save_all(data)


def render_overview(data):
    st.header("📊 نمای کلی دارایی‌ها")
    dark = get_effective_theme(data) == "dark"
    rate, _ = get_current_usd_rate(data)
    assets = data.get("assets", [])
    if not assets:
        st.info("هنوز دارایی‌ای ثبت نشده.")
        return
    rows, total_usd = [], 0.0
    for asset in assets:
        value, usd_value, record = compute_asset_value(asset, rate)
        if usd_value is not None:
            total_usd += usd_value
        rows.append({
            "دارایی": f"{asset_overview_emoji(asset)} {asset['name']}", "ارز": currency_label(asset["currency"]),
            "تعداد": record["quantity"] if record else 0, "قیمت واحد": record["unit_price"] if record else 0,
            "ارزش": value, "معادل_دلاری": usd_value, "آخرین_تاریخ": record["date_jalali"] if record else "—",
        })
    frame = pd.DataFrame(rows)
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 کل ارزش (دلاری)", f"${total_usd:,.2f}")
    col2.metric("📁 دارایی‌ها", len(assets))
    col3.metric("💵 نرخ دلار", f"{rate:,.0f} ریال" if rate else "ثبت نشده")

    st.subheader("🥧 ترکیب")
    pie = frame.dropna(subset=["معادل_دلاری"])
    pie = pie[pie["معادل_دلاری"] > 0]
    if not pie.empty:
        fig = px.pie(pie, values="معادل_دلاری", names="دارایی", hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
        plotly_layout(fig, dark, height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("برای نمایش ترکیب، نرخ دلار و رکوردهای دارایی لازم است.")

    st.subheader("📈 روند رشد")
    timeline = build_portfolio_timeline(data)
    if len(timeline) >= 2:
        for metric, title, color in [("total_usd", "💵 ارزش به دلار", "#3b82f6"), ("total_irr", "🇮🇷 ارزش به ریال", "#10b981")]:
            fig = px.line(timeline, x="date_jalali", y=metric, markers=True, color_discrete_sequence=[color])
            fig.update_traces(line=dict(width=3), marker=dict(size=7))
            plotly_layout(fig, dark, height=390)
            fig.update_layout(title=title)
            fig.update_yaxes(tickformat=",.0f")
            st.plotly_chart(fig, use_container_width=True)
        first_usd, last_usd = timeline["total_usd"].iloc[0], timeline["total_usd"].iloc[-1]
        first_irr, last_irr = timeline["total_irr"].iloc[0], timeline["total_irr"].iloc[-1]
        col1, col2 = st.columns(2)
        col1.metric("تغییر دلاری", f"${last_usd:,.2f}", delta=f"{last_usd-first_usd:+,.2f}")
        col2.metric("تغییر ریالی", f"{last_irr:,.0f}", delta=f"{last_irr-first_irr:+,.0f}")
    else:
        st.info("حداقل دو رکورد لازم است.")

    st.subheader("📋 جدول دارایی‌ها")
    display = frame.copy()
    display["تعداد"] = display["تعداد"].apply(fmt_num)
    display["قیمت واحد"] = display.apply(lambda row: f"{fmt_num(row['قیمت واحد'])} {row['ارز']}" if row["قیمت واحد"] else "—", axis=1)
    display["ارزش"] = display.apply(lambda row: f"{fmt_num(row['ارزش'])} {row['ارز']}" if row["ارزش"] else "—", axis=1)
    display["معادل_دلاری"] = display["معادل_دلاری"].apply(lambda value: f"${value:,.2f}" if pd.notna(value) else "—")
    display = display[["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل_دلاری", "آخرین_تاریخ"]]
    display.columns = ["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل دلاری", "آخرین بروزرسانی"]
    render_html_table(display, dark)


def render_journal(data):
    st.header("➕ افزودن دارایی")
    icons = load_fa_icons()
    classes = [icon["class"] for icon in icons]
    labels = {icon["class"]: f"{icon['label']} ({icon['class']})" for icon in icons}
    with st.container(border=True):
        st.subheader("➕ ثبت دارایی جدید")
        with st.form("add_asset_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([3, 2, 2])
            name = col1.text_input("نام", placeholder="طلا، سهام...")
            currency = col2.selectbox("ارز", ["IRR", "USD"], format_func=currency_label)
            icon = col3.selectbox("آیکون", classes, index=classes.index("fa-coins") if "fa-coins" in classes else 0, format_func=lambda value: labels.get(value, value))
            color = st.color_picker("رنگ آیکون", value="#3b82f6")
            st.markdown("**📝 رکورد اولیه (اختیاری)**")
            col1, col2, col3 = st.columns([2, 2, 3])
            quantity = col1.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
            price = col2.number_input("قیمت واحد", min_value=0.0, format="%.2f", step=1000.0)
            note = col3.text_input("توضیح")
            if st.form_submit_button("💾 ایجاد", use_container_width=True):
                if not name.strip():
                    st.error("نام را وارد کنید.")
                else:
                    asset_id = _short_id()
                    records = []
                    if quantity > 0 and price > 0:
                        records.append({"id": f"{asset_id}_r0", "date_gregorian": datetime.now().isoformat(), "date_jalali": today_jalali_str(),
                                        "quantity": quantity, "unit_price": price, "note": note.strip() or "رکورد اولیه"})
                    data.setdefault("assets", []).append({
                        "id": asset_id, "name": name.strip(), "icon": icon, "color": color, "overview_emoji": "",
                        "currency": currency, "created_at_gregorian": datetime.now().isoformat(),
                        "created_at_jalali": today_jalali_str(), "records": records,
                    })
                    _persist(data)
                    st.session_state.pending_nav = f"asset_{asset_id}"
                    st.rerun()

    if data.get("assets"):
        st.subheader("📝 لیست دارایی‌ها")
        rate, _ = get_current_usd_rate(data)
        for asset in data["assets"]:
            value, _, record = compute_asset_value(asset, rate)
            with st.container(border=True):
                col1, col2, col3, col4, col5, col6 = st.columns([3, 1.5, 2.5, 2.5, 1, 1])
                col1.markdown(f'**<i class="fa-solid {asset_icon(asset)}" style="color:{asset_color(asset)}"></i> {asset["name"]}**', unsafe_allow_html=True)
                col2.caption(currency_label(asset["currency"]))
                col3.caption(f"آخرین: {record['date_jalali'] if record else '—'}")
                col4.write(f"{fmt_num(value)} {currency_label(asset['currency'])}" if value else "—")
                if col5.button("📈", key=f"open_asset_{asset['id']}", help="تحلیل دارایی"):
                    st.session_state.pending_nav = f"asset_{asset['id']}"
                    st.rerun()
                if col6.button("🗑️", key=f"del_asset_{asset['id']}"):
                    data["assets"] = [item for item in data["assets"] if item["id"] != asset["id"]]
                    data["synthetic_pairs"] = [pair for pair in data.get("synthetic_pairs", []) if asset["id"] not in (pair.get("left_id"), pair.get("right_id"))]
                    _persist(data)
                    st.session_state.pending_nav = "overview"
                    st.rerun()


def render_usd_page(data):
    st.header("💵 نرخ دلار")
    st.caption(f"📅 {today_jalali_str()}")
    dark = get_effective_theme(data) == "dark"
    with st.container(border=True):
        st.subheader("➕ ثبت نرخ")
        with st.form("usd_rate_form", clear_on_submit=True):
            col1, col2 = st.columns([2, 3])
            rate = col1.number_input("نرخ (ریال)", min_value=0, step=1000, format="%d")
            note = col2.text_input("توضیح")
            if st.form_submit_button("💾 ثبت", use_container_width=True):
                if rate > 0:
                    data.setdefault("usd_rates", []).append({"id": _short_id(), "rate": rate, "note": note.strip(), "created_at": datetime.now().isoformat(), "created_at_jalali": today_jalali_str()})
                    updated, _ = sync_usd_rates_to_gold_funds(data)
                    if updated:
                        st.toast(f"🔄 {updated} رکورد صندوق طلا همگام شد")
                    _persist(data)
                    st.rerun()
                st.error("نرخ باید بزرگ‌تر از صفر باشد.")
    rates = data.get("usd_rates", [])
    if not rates:
        st.info("هنوز نرخی ثبت نشده.")
        return
    sorted_rates = sorted(rates, key=lambda item: item.get("created_at", ""))
    current, current_date = get_current_usd_rate(data)
    col1, col2, col3 = st.columns(3)
    col1.metric("نرخ فعلی", f"{current:,.0f} ریال")
    col2.metric("تعداد", len(rates))
    col3.metric("آخرین", current_date or "—")
    st.subheader("📈 روند")
    chart = pd.DataFrame([{"تاریخ": rate.get("created_at_jalali", "—"), "rate": rate["rate"]} for rate in sorted_rates])
    fig = px.line(chart, x="تاریخ", y="rate", markers=True, color_discrete_sequence=["#3b82f6"])
    plotly_layout(fig, dark, height=390)
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("📋 تاریخچه")
    for rate in reversed(sorted_rates):
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 2.5, 3, 0.7, 0.7])
            col1.markdown(f"**{rate['rate']:,.0f} ریال**")
            col2.caption(f"📅 {rate.get('created_at_jalali', '—')}")
            col3.caption(rate.get("note", "—") or "—")
            if col4.button("✏️", key=f"edit_btn_rate_{rate['id']}"):
                st.session_state[f"edit_open_rate_{rate['id']}"] = not st.session_state.get(f"edit_open_rate_{rate['id']}", False)
            if col5.button("🗑️", key=f"delrate_{rate['id']}"):
                data["usd_rates"] = [item for item in data["usd_rates"] if item["id"] != rate["id"]]
                sync_usd_rates_to_gold_funds(data)
                _persist(data)
                st.rerun()
            if st.session_state.get(f"edit_open_rate_{rate['id']}", False):
                with st.form(f"edit_rate_{rate['id']}"):
                    edit1, edit2 = st.columns([2, 3])
                    edit_date = edit1.text_input("تاریخ", value=rate.get("created_at_jalali", today_jalali_str()))
                    edit_rate = edit2.number_input("نرخ", value=int(rate["rate"]), min_value=1, step=1000, format="%d")
                    edit_note = st.text_input("توضیح", value=rate.get("note", ""))
                    if st.form_submit_button("💾 ذخیره", use_container_width=True):
                        jalali_date = parse_jalali(edit_date)
                        if jalali_date and edit_rate > 0:
                            time_part = rate.get("created_at", "")[11:16] or "00:00"
                            rate.update({"rate": edit_rate, "note": edit_note.strip(), "created_at": jalali_to_gregorian_iso(jalali_date, time_part), "created_at_jalali": jalali_date.strftime("%Y/%m/%d")})
                            sync_usd_rates_to_gold_funds(data)
                            st.session_state[f"edit_open_rate_{rate['id']}"] = False
                            _persist(data)
                            st.rerun()
                        st.error("تاریخ و نرخ معتبر وارد کنید.")


def render_monthly_returns_page(data):
    st.header("📅 بازده ماهانه")
    st.caption("بازده بر مبنای تغییر ارزش ریالی هر واحد؛ خرید و فروش به‌عنوان بازده محاسبه نمی‌شود.")
    dark = get_effective_theme(data) == "dark"
    dates = [record.get("date_jalali", "") for asset in data.get("assets", []) for record in asset.get("records", [])]
    dates += [record.get("date_jalali", "") for fund in data.get("gold_funds", []) for record in fund.get("records", [])]
    years = sorted({int(value[:4]) for value in dates if value[:4].isdigit()}, reverse=True)
    if not years:
        st.info("هنوز داده‌ای ثبت نشده.")
        return
    col1, col2, col3 = st.columns(3)
    year = col1.selectbox("سال (شمسی)", years)
    type_filter = col2.selectbox("نوع", ["همه", "دارایی‌ها", "صندوق‌های طلا"])
    month_from = col3.selectbox("از ماه", MONTH_NAMES, index=0)
    month_to = st.selectbox("تا ماه", MONTH_NAMES, index=11)
    start_index, end_index = MONTH_NAMES.index(month_from) + 1, MONTH_NAMES.index(month_to) + 1
    if start_index > end_index:
        st.warning("ماه شروع باید قبل از ماه پایان باشد.")
        return
    results = compute_monthly_returns(data, year)
    if type_filter == "دارایی‌ها":
        results = {key: value for key, value in results.items() if value["type"] == "asset"}
    elif type_filter == "صندوق‌های طلا":
        results = {key: value for key, value in results.items() if value["type"] == "gold"}
    labels = MONTH_NAMES[start_index - 1:end_index]
    plot_data = {}
    for info in results.values():
        values = [info["monthly"].get(month) for month in range(start_index, end_index + 1)]
        if any(value is not None for value in values):
            plot_data[info["name"]] = values
    if not plot_data:
        st.info("برای این بازه بازده قابل محاسبه‌ای وجود ندارد.")
        return
    mode = st.radio("نوع نمایش", ["📊 درصد بازده", "💰 سود / زیان به ریال"], horizontal=True)
    fig = go.Figure()
    for name, values in plot_data.items():
        percent_mode = mode.startswith("📊")
        y_values = [(value["return_pct"] if percent_mode else value["profit_irr"]) if value else 0 for value in values]
        texts = [(f"{value['return_pct']:+.2f}%" if percent_mode else f"{value['profit_irr']:+,.0f} ریال") if value else "—" for value in values]
        fig.add_trace(go.Bar(name=name, x=labels, y=y_values, text=texts, textposition="outside"))
    plotly_layout(fig, dark, height=510)
    fig.update_layout(barmode="group", title=f"بازده ماهانه سال {year}", xaxis_title="ماه", yaxis_title="بازده ماهانه (%)" if mode.startswith("📊") else "سود / زیان ماهانه (ریال)")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 جدول بازده ماهانه")
    table = pd.DataFrame({"ماه": labels})
    for name, values in plot_data.items():
        table[name] = [(f"{value['return_pct']:+.2f}%" if mode.startswith("📊") else f"{value['profit_irr']:+,.0f} ریال") if value else "—" for value in values]
    render_html_table(table, dark)

    st.subheader("📊 خلاصه بازده در بازه انتخابی")
    summary = []
    for name, values in plot_data.items():
        valid = [value for value in values if value]
        if not valid:
            continue
        cumulative = 1.0
        for value in valid:
            cumulative *= 1 + value["return_pct"] / 100
        percentages = [value["return_pct"] for value in valid]
        summary.append({"نام": name, "سود / زیان ریالی بازه": f"{sum(value['profit_irr'] for value in valid):+,.0f} ریال",
                        "بازده کل بازه": f"{(cumulative-1)*100:+.2f}%", "میانگین ماهانه": f"{sum(percentages)/len(percentages):+.2f}%",
                        "بهترین ماه": f"{max(percentages):+.2f}%", "بدترین ماه": f"{min(percentages):+.2f}%", "تعداد ماه": len(valid)})
    render_html_table(pd.DataFrame(summary), dark)
