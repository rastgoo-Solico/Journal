"""Detailed asset and gold-fund pages, preserving the original analysis workflow."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from financial_core import (
    _short_id,
    asset_color,
    asset_icon,
    compute_asset_value,
    currency_label,
    dollar_trap_analysis,
    fmt_num,
    get_current_usd_rate,
    get_effective_theme,
    gold_fund_analytics,
    jalali_to_gregorian_iso,
    ounce_signal,
    parse_jalali,
    plotly_layout,
    save_all,
    sync_usd_rates_to_gold_funds,
    today_jalali_str,
)


def _persist(data):
    st.session_state.data = data
    save_all(data)


def _rate_at(rates, date):
    found = None
    for rate in rates:
        if rate.get("created_at", "")[:10] <= date:
            found = rate["rate"]
        else:
            break
    return found


def render_asset_page(data, asset):
    rate, _ = get_current_usd_rate(data)
    value, usd_value, latest = compute_asset_value(asset, rate)
    dark = get_effective_theme(data) == "dark"
    st.markdown(
        f'<h1 style="text-align:right"><i class="fa-solid {asset_icon(asset)}" style="color:{asset_color(asset)}"></i> {asset["name"]}</h1>',
        unsafe_allow_html=True,
    )
    st.caption(f"ارز: **{currency_label(asset['currency'])}** | ایجاد: {asset.get('created_at_jalali', '—')}")

    with st.expander("⚙️ ویرایش نام و ارز"):
        with st.form(f"edit_asset_{asset['id']}"):
            col1, col2 = st.columns([3, 2])
            new_name = col1.text_input("نام", value=asset["name"])
            new_currency = col2.selectbox(
                "ارز", ["IRR", "USD"], index=0 if asset["currency"] == "IRR" else 1,
                format_func=currency_label,
            )
            if st.form_submit_button("💾 ذخیره", use_container_width=True):
                if new_name.strip():
                    asset["name"] = new_name.strip()
                    asset["currency"] = new_currency
                    _persist(data)
                    st.rerun()
                st.error("نام نمی‌تواند خالی باشد.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 تعداد", fmt_num(latest["quantity"]) if latest else "—")
    col2.metric("💲 قیمت هر واحد", f"{fmt_num(latest['unit_price'])} {currency_label(asset['currency'])}" if latest else "—")
    col3.metric("💰 ارزش کل", f"{fmt_num(value)} {currency_label(asset['currency'])}" if latest else "—")
    col4.metric("💵 ارزش دلاری", f"${usd_value:,.2f}" if usd_value is not None else "—")

    with st.container(border=True):
        st.subheader("➕ ثبت رکورد روزانه")
        with st.form(f"add_record_{asset['id']}", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
            date_text = col1.text_input("تاریخ", value=today_jalali_str())
            quantity = col2.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
            price = col3.number_input(f"قیمت هر واحد ({currency_label(asset['currency'])})", min_value=0.0, format="%.2f", step=1000.0)
            note = col4.text_input("توضیح")
            if st.form_submit_button("💾 ثبت", use_container_width=True):
                jalali_date = parse_jalali(date_text)
                if jalali_date and quantity > 0 and price > 0:
                    asset.setdefault("records", []).append({
                        "id": _short_id(),
                        "date_gregorian": jalali_to_gregorian_iso(jalali_date, datetime.now().strftime("%H:%M")),
                        "date_jalali": jalali_date.strftime("%Y/%m/%d"),
                        "quantity": quantity, "unit_price": price, "note": note.strip(),
                    })
                    _persist(data)
                    st.rerun()
                st.error("تاریخ، تعداد و قیمت معتبر وارد کنید.")

    records = sorted(asset.get("records", []), key=lambda record: record.get("date_gregorian", ""))
    if len(records) >= 2:
        st.subheader("📈 روند ارزش کل")
        st.caption("این نمودار ارزش کل را نشان می‌دهد (تعداد × قیمت) و با خرید و فروش نیز تغییر می‌کند.")
        chart = pd.DataFrame([{"تاریخ": record["date_jalali"], "ارزش": float(record["quantity"]) * float(record["unit_price"])} for record in records])
        fig = px.line(chart, x="تاریخ", y="ارزش", markers=True, color_discrete_sequence=[asset_color(asset)])
        fig.update_traces(line=dict(width=3), marker=dict(size=7))
        plotly_layout(fig, dark, height=390)
        fig.update_yaxes(title=currency_label(asset["currency"]), tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)
    elif records:
        st.info("برای رسم روند ارزش کل، حداقل دو رکورد لازم است.")

    rates = sorted(data.get("usd_rates", []), key=lambda item: item.get("created_at", ""))
    comparison_rows = []
    for record in records:
        date = record.get("date_gregorian", "")[:10]
        rate_at = _rate_at(rates, date)
        if not rate_at or rate_at <= 0:
            continue
        native = float(record["unit_price"])
        if asset["currency"] == "IRR":
            price_irr, price_usd = native, native / rate_at
        else:
            price_usd, price_irr = native, native * rate_at
        comparison_rows.append({
            "date_jalali": record["date_jalali"], "record": record, "unit_price_irr": price_irr,
            "unit_price_usd": price_usd, "usd_rate": rate_at, "quantity": float(record["quantity"]),
        })

    if len(comparison_rows) >= 2:
        base_irr = comparison_rows[0]["unit_price_irr"]
        base_usd = comparison_rows[0]["unit_price_usd"]
        base_rate = comparison_rows[0]["usd_rate"]
        dates = [row["date_jalali"] for row in comparison_rows]
        irr_index = [row["unit_price_irr"] / base_irr * 100 for row in comparison_rows]
        usd_index = [row["unit_price_usd"] / base_usd * 100 for row in comparison_rows]
        rate_index = [row["usd_rate"] / base_rate * 100 for row in comparison_rows]
        st.subheader("📈 نمودار مقایسه‌ای «قیمت هر واحد» (نرمال‌شده به ۱۰۰)")
        st.caption("🔵 قیمت هر واحد به ریال | 🟢 قیمت هر واحد به دلار | 🟠 نرخ دلار — مستقل از تعداد دارایی")
        fig_compare = go.Figure()
        fig_compare.add_trace(go.Scatter(x=dates, y=irr_index, mode="lines+markers", name="قیمت واحد (ریال)", line=dict(color="#3b82f6", width=3)))
        fig_compare.add_trace(go.Scatter(x=dates, y=usd_index, mode="lines+markers", name="قیمت واحد (دلار)", line=dict(color="#10b981", width=3)))
        fig_compare.add_trace(go.Scatter(x=dates, y=rate_index, mode="lines+markers", name="نرخ دلار", line=dict(color="#f59e0b", width=2, dash="dot")))
        plotly_layout(fig_compare, dark, height=450)
        fig_compare.update_yaxes(title="شاخص قیمت هر واحد (پایه=۱۰۰)")
        st.plotly_chart(fig_compare, use_container_width=True)
        last_irr, last_usd, last_rate = irr_index[-1], usd_index[-1], rate_index[-1]
        if last_irr > 105 and last_usd < 95:
            st.error(f"🔴 **تله دلار:** رشد ریالی {last_irr-100:+.1f}% ولی تغییر دلاری {last_usd-100:+.1f}%. نرخ دلار {last_rate-100:+.1f}% رشد کرده است.")
        elif last_usd > 105:
            st.success(f"🟢 **سود دلاری واقعی:** قیمت هر واحد به دلار {last_usd-100:+.1f}% رشد کرده؛ نرخ دلار {last_rate-100:+.1f}%.")
        elif last_usd < 95:
            st.warning(f"🟡 **ضرر دلاری:** قیمت هر واحد به دلار {last_usd-100:+.1f}% تغییر کرده؛ نرخ دلار {last_rate-100:+.1f}%.")
        else:
            st.info(f"⚪ قیمت هر واحد به دلار {last_usd-100:+.1f}% — تعادل نسبی.")
    elif records:
        st.info("برای نمودار مقایسه‌ای، حداقل دو رکورد با نرخ دلار معتبر در همان تاریخ لازم است.")

    st.subheader("📋 تاریخچه رکوردها")
    if not comparison_rows:
        st.info("رکوردی با نرخ دلار معتبر وجود ندارد.")
    else:
        header = st.columns([1.8, 1.3, 1.6, 1.6, 1.5, 1.5, 0.6, 0.6])
        for column, label in zip(header, ["تاریخ", "تعداد", "قیمت (ریال)", "قیمت (دلار)", "نرخ دلار", "بازده دلاری", "", ""]):
            column.caption(f"**{label}**")
        base_usd = comparison_rows[0]["unit_price_usd"]
        for row in reversed(comparison_rows):
            record = row["record"]
            usd_return = (row["unit_price_usd"] / base_usd - 1) * 100 if base_usd else 0
            columns = st.columns([1.8, 1.3, 1.6, 1.6, 1.5, 1.5, 0.6, 0.6])
            columns[0].markdown(f"📅 {row['date_jalali']}")
            columns[1].markdown(f"{row['quantity']:,.2f}")
            columns[2].markdown(f"{row['unit_price_irr']:,.0f} ریال")
            columns[3].markdown(f"${row['unit_price_usd']:,.4f}")
            columns[4].markdown(f"{row['usd_rate']:,.0f}")
            if abs(usd_return) >= 0.05:
                color = "#10b981" if usd_return > 0 else "#ef4444"
                columns[5].markdown(f'<span style="color:{color};font-weight:700">{usd_return:+.1f}%</span>', unsafe_allow_html=True)
            else:
                columns[5].markdown("—")
            if columns[6].button("✏️", key=f"edit_btn_rec_{record['id']}"):
                st.session_state[f"edit_open_rec_{record['id']}"] = not st.session_state.get(f"edit_open_rec_{record['id']}", False)
            if columns[7].button("🗑️", key=f"del_rec_{record['id']}"):
                asset["records"] = [item for item in asset["records"] if item["id"] != record["id"]]
                _persist(data)
                st.rerun()
            if st.session_state.get(f"edit_open_rec_{record['id']}", False):
                with st.form(f"edit_rec_{record['id']}"):
                    edit1, edit2, edit3 = st.columns(3)
                    edit_date = edit1.text_input("تاریخ", value=record["date_jalali"])
                    edit_quantity = edit2.number_input("تعداد", value=float(record["quantity"]), min_value=0.0, format="%.4f")
                    edit_price = edit3.number_input("قیمت هر واحد", value=float(record["unit_price"]), min_value=0.0, format="%.2f")
                    edit_note = st.text_input("توضیح", value=record.get("note", ""))
                    if st.form_submit_button("💾 ذخیره", use_container_width=True):
                        jalali_date = parse_jalali(edit_date)
                        if jalali_date and edit_quantity > 0 and edit_price > 0:
                            time_part = record.get("date_gregorian", "")[11:16] or "00:00"
                            record.update({
                                "date_gregorian": jalali_to_gregorian_iso(jalali_date, time_part),
                                "date_jalali": jalali_date.strftime("%Y/%m/%d"), "quantity": edit_quantity,
                                "unit_price": edit_price, "note": edit_note.strip(),
                            })
                            st.session_state[f"edit_open_rec_{record['id']}"] = False
                            _persist(data)
                            st.rerun()
                        st.error("مقادیر معتبر وارد کنید.")
            st.divider()

    with st.expander("⚠️ حذف کل دارایی"):
        confirm = st.checkbox("مطمئنم", key=f"confirm_del_{asset['id']}")
        if st.button("🗑️ حذف دارایی", disabled=not confirm, key=f"del_btn_{asset['id']}", use_container_width=True):
            data["assets"] = [item for item in data["assets"] if item["id"] != asset["id"]]
            data["synthetic_pairs"] = [pair for pair in data.get("synthetic_pairs", []) if asset["id"] not in (pair.get("left_id"), pair.get("right_id"))]
            _persist(data)
            st.session_state.pending_nav = "overview"
            st.rerun()


def _gold_arbitrage(fund, records, current_rate):
    with st.expander("🧮 ماشین‌حساب آربیتراژ دلاری"):
        if current_rate is None:
            st.warning("ابتدا نرخ دلار را ثبت کنید.")
            return
        st.caption(f"نرخ دلار فعلی: **{current_rate:,.0f} ریال**")
        latest_price = float(records[-1]["unit_price"])
        col1, col2, col3, col4 = st.columns(4)
        units = col1.number_input("تعداد واحد", min_value=0.0, value=1.0, step=1.0, key=f"calc_units_{fund['id']}")
        sell = col2.number_input("قیمت فروش (ریال)", min_value=0.0, value=latest_price, step=1000.0, key=f"calc_sell_{fund['id']}")
        rebuy_rate = col3.number_input("نرخ دلار پیش‌بینی", min_value=0.0, value=float(current_rate), step=1000.0, key=f"calc_rebuy_rate_{fund['id']}")
        rebuy = col4.number_input("قیمت خرید مجدد (ریال)", min_value=0.0, value=latest_price, step=1000.0, key=f"calc_rebuy_{fund['id']}")
        fee1, fee2, fee3 = st.columns(3)
        fee_sell = fee1.number_input("کارمزد فروش صندوق (%)", min_value=0.0, value=0.5, step=0.1, key=f"fee_sell_{fund['id']}")
        fee_usd = fee2.number_input("اسپرد دلار (% هر طرف)", min_value=0.0, value=1.0, step=0.1, key=f"fee_usd_{fund['id']}")
        fee_buy = fee3.number_input("کارمزد خرید صندوق (%)", min_value=0.0, value=0.5, step=0.1, key=f"fee_buy_{fund['id']}")
        if units > 0 and sell > 0 and rebuy_rate > 0 and rebuy > 0:
            gross_irr = units * sell * (1 - fee_sell / 100)
            dollars = gross_irr / (rebuy_rate * (1 + fee_usd / 100))
            irr_back = dollars * rebuy_rate * (1 - fee_usd / 100)
            new_units = irr_back / rebuy * (1 - fee_buy / 100)
            net_units = new_units - units
            net_irr = net_units * rebuy
            result1, result2, result3 = st.columns(3)
            result1.metric("💵 دلار به‌دست‌آمده", f"${dollars:,.4f}")
            result2.metric("📦 واحد پس از خرید مجدد", f"{new_units:,.4f}")
            result3.metric("✅ سود خالص" if net_units > 0 else "❌ ضرر خالص", f"{net_units:+,.4f} واحد", delta=f"{net_irr:+,.0f} ریال")
            if net_units > 0:
                st.success(f"✅ سودآور: **{net_units:,.4f} واحد** بیشتر")
                if net_units < units * 0.05:
                    st.info("💡 سود کمتر از ۵٪ است.")
            else:
                st.error(f"❌ ضرر: {abs(net_units):,.4f} واحد")


def _add_gold_record(data, fund, records, current_rate, current_rate_date):
    with st.expander(f"➕ افزودن رکورد برای {fund['name']}", expanded=len(records) == 0):
        if current_rate is None:
            st.warning("ابتدا نرخ دلار را در صفحهٔ دلار ثبت کنید.")
            return
        st.caption(f"نرخ دلار فعلی: **{current_rate:,.0f} ریال** ({current_rate_date})")
        col1, col2, col3 = st.columns(3)
        date_text = col1.text_input("تاریخ (شمسی)", value=today_jalali_str(), key=f"gdate_{fund['id']}")
        price = col2.number_input("قیمت واحد (ریال)", min_value=0.0, format="%.0f", step=1000.0, key=f"gprice_{fund['id']}")
        ounce = col3.number_input("انس طلا (دلار)", min_value=0.0, format="%.2f", step=1.0, value=3000.0, key=f"gounce_{fund['id']}")
        note = st.text_input("توضیح (اختیاری)", key=f"gnote_{fund['id']}")
        if price > 0 and ounce > 0:
            st.success(f"📊 واحد برای ۱ انس: **{(ounce * current_rate) / price:,.0f}** | معادل دلاری: **${price/current_rate:.4f}**")
        if st.button("💾 ثبت رکورد", key=f"gsave_{fund['id']}", use_container_width=True):
            jalali_date = parse_jalali(date_text)
            if jalali_date and price > 0 and ounce > 0:
                fund.setdefault("records", []).append({
                    "id": _short_id(), "date_gregorian": jalali_to_gregorian_iso(jalali_date, datetime.now().strftime("%H:%M")),
                    "date_jalali": jalali_date.strftime("%Y/%m/%d"), "unit_price": price,
                    "ounce_price_usd": ounce, "usd_rate_used": current_rate, "note": note.strip(),
                })
                sync_usd_rates_to_gold_funds(data)
                _persist(data)
                st.rerun()
            st.error("تاریخ و مقادیر معتبر وارد کنید.")


def render_gold_page(data):
    st.header("🥇 صندوق‌های طلا")
    st.caption(f"📅 {today_jalali_str()}")
    dark = get_effective_theme(data) == "dark"
    updated, missing = sync_usd_rates_to_gold_funds(data)
    if updated:
        st.session_state.data = data
    if missing:
        st.warning(f"⚠️ {missing} رکورد تاریخشان قبل از اولین نرخ دلار است.")
    with st.container(border=True):
        st.subheader("➕ افزودن صندوق جدید")
        with st.form("add_gold_fund_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 2])
            name = col1.text_input("نام صندوق", placeholder="طلا، عیار، لوتوس، ...")
            icon = col2.text_input("ایموجی", value="🥇", max_chars=4)
            if st.form_submit_button("💾 ایجاد صندوق", use_container_width=True):
                if name.strip():
                    data.setdefault("gold_funds", []).append({"id": _short_id(), "name": name.strip(), "icon": (icon.strip() or "🥇")[:4], "created_at": datetime.now().isoformat(), "records": []})
                    _persist(data)
                    st.rerun()
                st.error("نام صندوق را وارد کنید.")
    current_rate, current_rate_date = get_current_usd_rate(data)
    if not data.get("gold_funds"):
        st.info("هنوز صندوقی اضافه نشده.")
        return

    for fund in data["gold_funds"]:
        st.markdown(f"### {fund.get('icon', '🥇')} {fund['name']}")
        records = sorted(fund.get("records", []), key=lambda record: record.get("date_gregorian", ""))
        trap = dollar_trap_analysis(fund, days=30)
        if trap and trap["gap"] > 10:
            st.warning(f"⚠️ **هشدار تله دلار** — {trap['older_date']} تا {trap['last_date']}: دلار **{trap['usd_change']:+.1f}%**، انس **{trap['ounce_change']:+.1f}%**، شکاف **{trap['gap']:+.1f}%**.")
        analytics = gold_fund_analytics(fund)
        prices = [float(record["unit_price"]) for record in records if float(record.get("unit_price", 0) or 0) > 0]
        units_list = [(float(record["ounce_price_usd"]) * float(record["usd_rate_used"])) / float(record["unit_price"]) for record in records if float(record.get("unit_price", 0) or 0) > 0 and float(record.get("usd_rate_used", 0) or 0) > 0 and float(record.get("ounce_price_usd", 0) or 0) > 0]
        if prices:
            st.markdown("**💰 قیمت واحد صندوق**")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📉 کمترین قیمت", f"{min(prices):,.0f} ریال")
            col2.metric("📊 میانگین قیمت", f"{sum(prices)/len(prices):,.0f} ریال")
            col3.metric("📈 بیشترین قیمت", f"{max(prices):,.0f} ریال")
            col4.metric("📋 تعداد رکورد", len(records))
        if units_list:
            st.markdown("**📦 تعداد واحد مورد نیاز برای یک انس**")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📉 کمترین واحد", f"{min(units_list):,.0f}")
            col2.metric("📊 میانگین واحد", f"{sum(units_list)/len(units_list):,.0f}")
            col3.metric("📈 بیشترین واحد", f"{max(units_list):,.0f}")
            col4.metric("📊 میانگین ارزش", f"{(sum(units_list)/len(units_list))*(sum(prices)/len(prices)):,.0f} ریال")
        if analytics and analytics[-1]["usd_equivalent"] is not None:
            last = analytics[-1]
            first_usd = next((row["usd_equivalent"] for row in analytics if row["usd_equivalent"] is not None), None)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💵 معادل دلاری فعلی", f"${last['usd_equivalent']:,.4f}")
            if last["usd_return_pct"] is not None:
                col2.metric("📈 بازده دلاری از خرید", f"{last['usd_return_pct']:+.1f}%", delta=f"${last['usd_equivalent']-first_usd:+.4f}" if first_usd else None)
            if last["gram_per_unit"]:
                valid_grams = [row["gram_per_unit"] for row in analytics if row["gram_per_unit"]]
                average_gram = sum(valid_grams) / len(valid_grams)
                col3.metric("⚖️ گرم/واحد", f"{last['gram_per_unit']*1000:.3f} mg", delta=f"{(last['gram_per_unit']/average_gram-1)*100:+.1f}% vs avg")
            col4.metric("📊 سیگنال انس", ounce_signal(fund).split("—")[0].strip())
            st.caption(f"**سیگنال فعلی:** {ounce_signal(fund)}")
        else:
            st.caption("هنوز رکورد معتبری ثبت نشده.")

        if records:
            _gold_arbitrage(fund, records, current_rate)
        _add_gold_record(data, fund, records, current_rate, current_rate_date)

        valid = [row for row in analytics if row["usd_equivalent"] is not None and float(row["record"].get("ounce_price_usd", 0) or 0) > 0]
        if len(valid) >= 2:
            st.markdown("**📈 نمودار مقایسه‌ای صندوق (نرمال‌شده به ۱۰۰)**")
            base_irr = float(valid[0]["record"]["unit_price"])
            base_usd = valid[0]["usd_equivalent"]
            base_ounce = float(valid[0]["record"]["ounce_price_usd"])
            dates = [row["record"]["date_jalali"] for row in valid]
            irr_index = [float(row["record"]["unit_price"]) / base_irr * 100 for row in valid]
            usd_index = [row["usd_equivalent"] / base_usd * 100 for row in valid]
            ounce_index = [float(row["record"]["ounce_price_usd"]) / base_ounce * 100 for row in valid]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=irr_index, mode="lines+markers", name="قیمت ریالی", line=dict(color="#3b82f6", width=3)))
            fig.add_trace(go.Scatter(x=dates, y=usd_index, mode="lines+markers", name="معادل دلاری", line=dict(color="#10b981", width=3)))
            fig.add_trace(go.Scatter(x=dates, y=ounce_index, mode="lines+markers", name="انس طلا", line=dict(color="#f59e0b", width=2, dash="dot")))
            plotly_layout(fig, dark, height=440)
            fig.update_yaxes(title="شاخص (پایه=۱۰۰)")
            st.plotly_chart(fig, use_container_width=True)
            if irr_index[-1] > 105 and usd_index[-1] < 95:
                st.error(f"🔴 **تله دلار:** ریالی {irr_index[-1]-100:+.1f}% ولی دلاری {usd_index[-1]-100:+.1f}%")
            elif usd_index[-1] > 105:
                st.success(f"🟢 **سود دلاری واقعی:** {usd_index[-1]-100:+.1f}%")

        if analytics:
            st.markdown("**📋 تاریخچه رکوردها**")
            for row in reversed(analytics):
                record = row["record"]
                with st.container(border=True):
                    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
                    col1.markdown(f"📅 **{record['date_jalali']}**")
                    col2.markdown(f"قیمت: **{float(record['unit_price']):,.0f}**")
                    col3.markdown(f"دلاری: **${row['usd_equivalent']:,.4f}**" if row["usd_equivalent"] else "دلاری: —")
                    col4.markdown(f"انس: **${float(record['ounce_price_usd']):,.0f}**")
                    units_for_ounce = (float(record["ounce_price_usd"]) * float(record.get("usd_rate_used", 0))) / float(record["unit_price"]) if float(record.get("unit_price", 0)) > 0 else 0
                    col5.markdown(f"واحد/انس: **{units_for_ounce:,.0f}**")
                    if col6.button("🗑️", key=f"del_gold_rec_{record['id']}"):
                        fund["records"] = [item for item in fund["records"] if item["id"] != record["id"]]
                        _persist(data)
                        st.rerun()
                    with st.expander("✏️ ویرایش رکورد"):
                        with st.form(f"edit_gold_rec_{record['id']}"):
                            edit1, edit2, edit3 = st.columns(3)
                            edit_date = edit1.text_input("تاریخ", value=record["date_jalali"])
                            edit_price = edit2.number_input("قیمت واحد", value=float(record["unit_price"]), min_value=0.0)
                            edit_ounce = edit3.number_input("انس (دلار)", value=float(record["ounce_price_usd"]), min_value=0.0)
                            edit4, edit5 = st.columns([2, 3])
                            edit_rate = edit4.number_input("نرخ دلار", value=float(record.get("usd_rate_used", 0)), min_value=0.0)
                            edit_note = edit5.text_input("توضیح", value=record.get("note", ""))
                            if edit_price > 0 and edit_ounce > 0 and edit_rate > 0:
                                st.info(f"واحد برای ۱ انس: {(edit_ounce*edit_rate)/edit_price:,.0f}")
                            if st.form_submit_button("💾 ذخیره", use_container_width=True):
                                jalali_date = parse_jalali(edit_date)
                                if jalali_date and edit_price > 0 and edit_ounce > 0 and edit_rate > 0:
                                    time_part = record.get("date_gregorian", "")[11:16] or "00:00"
                                    record.update({"date_gregorian": jalali_to_gregorian_iso(jalali_date, time_part), "date_jalali": jalali_date.strftime("%Y/%m/%d"),
                                                   "unit_price": edit_price, "ounce_price_usd": edit_ounce, "usd_rate_used": edit_rate, "note": edit_note.strip()})
                                    _persist(data)
                                    st.rerun()
                                st.error("مقادیر معتبر وارد کنید.")
        with st.expander(f"⚠️ حذف صندوق {fund['name']}"):
            confirm = st.checkbox("مطمئنم", key=f"confirm_del_gold_{fund['id']}")
            if st.button("🗑️ حذف صندوق", disabled=not confirm, key=f"del_gold_fund_{fund['id']}", use_container_width=True):
                data["gold_funds"] = [item for item in data["gold_funds"] if item["id"] != fund["id"]]
                data["synthetic_pairs"] = [pair for pair in data.get("synthetic_pairs", []) if fund["id"] not in (pair.get("left_id"), pair.get("right_id"))]
                _persist(data)
                st.rerun()
        st.divider()
