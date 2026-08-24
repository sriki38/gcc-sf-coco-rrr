# Regulatory Reporting Dashboard for Basel III, MiFID II, AIFMD, EMIR, UCITS, and AML/KYC
# Co-authored with CoCo
import os
import streamlit as st

st.set_page_config(page_title="Regulatory Reporting Dashboard", layout="wide")

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))


@st.cache_data
def load_available_months():
    return conn.query("""
        SELECT DISTINCT
            TO_CHAR(d.CALENDAR_DATE, 'YYYY-MM') AS MONTH_LABEL,
            TO_CHAR(LAST_DAY(d.CALENDAR_DATE), 'YYYY-MM-DD') AS MONTH_END_DATE
        FROM REGULATORY_DW.REG_MODEL.DIM_DATE d
        WHERE d.IS_MONTH_END = TRUE
          AND (
            EXISTS (SELECT 1 FROM REGULATORY_DW.REG_MODEL.FACT_POSITION p WHERE p.AS_OF_DATE = d.CALENDAR_DATE)
            OR EXISTS (SELECT 1 FROM REGULATORY_DW.REG_MODEL.FACT_TRANSACTION t
                       JOIN REGULATORY_DW.REG_MODEL.DIM_DATE dd ON t.TRADE_DATE_KEY = dd.DATE_KEY
                       WHERE dd.CALENDAR_DATE BETWEEN DATE_TRUNC('MONTH', d.CALENDAR_DATE) AND d.CALENDAR_DATE)
          )
        ORDER BY MONTH_END_DATE DESC
    """)


@st.cache_data
def load_basel_summary(month_end):
    return conn.query("""
        SELECT
            f.FUND_NAME,
            f.FUND_TYPE,
            f.LEVERAGE_RATIO,
            SUM(p.MARKET_VALUE_BASE) AS TOTAL_EXPOSURE,
            SUM(p.VAR_95) AS TOTAL_VAR_95,
            SUM(p.VAR_99) AS TOTAL_VAR_99,
            SUM(p.LEVERAGE_CONTRIBUTION * p.MARKET_VALUE_BASE) / NULLIF(SUM(p.MARKET_VALUE_BASE), 0) AS WEIGHTED_LEVERAGE,
            SUM(CASE WHEN p.CONCENTRATION_BREACH = TRUE THEN 1 ELSE 0 END) AS CONCENTRATION_BREACHES,
            COUNT(*) AS POSITION_COUNT
        FROM REGULATORY_DW.REG_MODEL.FACT_POSITION p
        JOIN REGULATORY_DW.REG_MODEL.DIM_FUND f ON p.FUND_KEY = f.FUND_KEY
        WHERE p.AS_OF_DATE = :1
        GROUP BY f.FUND_NAME, f.FUND_TYPE, f.LEVERAGE_RATIO
        ORDER BY TOTAL_EXPOSURE DESC
    """, params=[month_end])


@st.cache_data
def load_mifid_summary(month_start, month_end):
    return conn.query("""
        SELECT
            ft.EXECUTION_VENUE,
            ft.EXECUTION_VENUE_MIC,
            tm.TRADE_MODEL_NAME,
            tm.EXECUTION_METHOD,
            COUNT(*) AS TOTAL_TRADES,
            SUM(ft.GROSS_AMOUNT) AS TOTAL_NOTIONAL,
            SUM(CASE WHEN ft.BEST_EXECUTION_FLAG = TRUE THEN 1 ELSE 0 END) AS BEST_EXEC_PASS,
            SUM(CASE WHEN ft.ALGO_EXECUTION_FLAG = TRUE THEN 1 ELSE 0 END) AS ALGO_TRADES,
            SUM(CASE WHEN ft.REPORTING_STATUS = 'REPORTED' THEN 1 ELSE 0 END) AS REPORTED_TRADES,
            SUM(CASE WHEN ft.IS_CROSS_BORDER = TRUE THEN 1 ELSE 0 END) AS CROSS_BORDER_TRADES,
            SUM(CASE WHEN ft.EXECUTION_VENUE_MIC IS NULL AND ft.EXECUTION_VENUE != 'OTC' THEN 1 ELSE 0 END) AS MISSING_MIC
        FROM REGULATORY_DW.REG_MODEL.FACT_TRANSACTION ft
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_TRADE_MODEL tm ON ft.TRADE_MODEL_KEY = tm.TRADE_MODEL_KEY
        JOIN REGULATORY_DW.REG_MODEL.DIM_DATE d ON ft.TRADE_DATE_KEY = d.DATE_KEY
        WHERE d.CALENDAR_DATE BETWEEN :1 AND :2
        GROUP BY ft.EXECUTION_VENUE, ft.EXECUTION_VENUE_MIC, tm.TRADE_MODEL_NAME, tm.EXECUTION_METHOD
        ORDER BY TOTAL_NOTIONAL DESC
    """, params=[month_start, month_end])


@st.cache_data
def load_aifmd_summary(month_start, month_end):
    return conn.query("""
        SELECT
            f.FUND_ID,
            f.FUND_NAME,
            f.FUND_TYPE,
            f.FUND_STRUCTURE,
            f.BASE_CURRENCY,
            f.TOTAL_AUM,
            f.LEVERAGE_RATIO AS GROSS_LEVERAGE,
            f.AIFMD_REPORTING_REQUIRED,
            f.FORM_PF_REPORTING_REQUIRED,
            g.COUNTRY_NAME AS DOMICILE,
            rr.REPORT_STATUS,
            rr.ACTUAL_SUBMISSION_DATE,
            rr.SUBMISSION_DEADLINE,
            rr.BREACHES_REPORTED
        FROM REGULATORY_DW.REG_MODEL.DIM_FUND f
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_GEOGRAPHY g ON f.DOMICILE_GEOGRAPHY_KEY = g.GEOGRAPHY_KEY
        LEFT JOIN REGULATORY_DW.REG_MODEL.FACT_REGULATORY_REPORT rr
            ON rr.FUND_KEY = f.FUND_KEY AND rr.REPORT_TYPE IN ('AIFMD_ANNEX_IV', 'FORM_PF')
            AND rr.REPORTING_PERIOD_START <= :2 AND rr.REPORTING_PERIOD_END >= :1
        WHERE f.AIFMD_REPORTING_REQUIRED = TRUE OR f.FORM_PF_REPORTING_REQUIRED = TRUE
        ORDER BY f.TOTAL_AUM DESC
    """, params=[month_start, month_end])


@st.cache_data
def load_emir_summary(month_end):
    return conn.query("""
        SELECT
            s.SECURITY_NAME,
            s.SECURITY_TYPE,
            s.SUB_ASSET_CLASS,
            s.IS_OTC,
            cp.COUNTERPARTY_NAME,
            cp.COUNTERPARTY_TYPE,
            cp.CENTRAL_CLEARING_ELIGIBLE,
            cp.CSA_IN_PLACE,
            cp.NETTING_AGREEMENT,
            p.MARKET_VALUE_BASE AS EXPOSURE,
            p.MARGIN_REQUIREMENT,
            p.COLLATERAL_PLEDGED,
            f.FUND_NAME
        FROM REGULATORY_DW.REG_MODEL.FACT_POSITION p
        JOIN REGULATORY_DW.REG_MODEL.DIM_SECURITY s ON p.SECURITY_KEY = s.SECURITY_KEY
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_COUNTERPARTY cp ON p.COUNTERPARTY_KEY = cp.COUNTERPARTY_KEY
        JOIN REGULATORY_DW.REG_MODEL.DIM_FUND f ON p.FUND_KEY = f.FUND_KEY
        WHERE s.IS_DERIVATIVE = TRUE
        AND p.AS_OF_DATE = :1
        ORDER BY p.MARKET_VALUE_BASE DESC
    """, params=[month_end])


@st.cache_data
def load_ucits_summary(month_end):
    return conn.query("""
        SELECT
            f.FUND_ID,
            f.FUND_NAME,
            f.TOTAL_AUM,
            f.LEVERAGE_RATIO,
            f.UCITS_COMPLIANT,
            f.BASE_CURRENCY,
            f.BENCHMARK_INDEX,
            COUNT(p.POSITION_KEY) AS POSITIONS,
            SUM(p.MARKET_VALUE_BASE) AS TOTAL_MV,
            MAX(p.WEIGHT_IN_FUND_PCT) AS MAX_SINGLE_POSITION_PCT,
            SUM(CASE WHEN p.CONCENTRATION_BREACH = TRUE THEN 1 ELSE 0 END) AS BREACHES,
            SUM(CASE WHEN s.ASSET_CLASS = 'DERIVATIVE' THEN p.MARKET_VALUE_BASE ELSE 0 END) AS DERIVATIVE_EXPOSURE
        FROM REGULATORY_DW.REG_MODEL.DIM_FUND f
        LEFT JOIN REGULATORY_DW.REG_MODEL.FACT_POSITION p ON f.FUND_KEY = p.FUND_KEY AND p.AS_OF_DATE = :1
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_SECURITY s ON p.SECURITY_KEY = s.SECURITY_KEY
        WHERE f.UCITS_COMPLIANT = TRUE
        GROUP BY f.FUND_ID, f.FUND_NAME, f.TOTAL_AUM, f.LEVERAGE_RATIO, f.UCITS_COMPLIANT, f.BASE_CURRENCY, f.BENCHMARK_INDEX
        ORDER BY f.TOTAL_AUM DESC
    """, params=[month_end])


@st.cache_data
def load_aml_summary():
    return conn.query("""
        SELECT
            a.ACCOUNT_ID,
            a.ACCOUNT_NAME,
            a.CLIENT_TYPE,
            a.CLIENT_CLASSIFICATION,
            a.AML_RISK_RATING,
            a.KYC_STATUS,
            a.KYC_LAST_REVIEWED,
            a.ONBOARDING_DATE,
            a.RISK_PROFILE,
            a.AUM_BAND,
            g.COUNTRY_NAME AS DOMICILE,
            g.REGULATORY_ZONE,
            DATEDIFF('day', a.KYC_LAST_REVIEWED, CURRENT_DATE()) AS DAYS_SINCE_KYC_REVIEW,
            CASE
                WHEN DATEDIFF('day', a.KYC_LAST_REVIEWED, CURRENT_DATE()) > 365 THEN 'OVERDUE'
                WHEN DATEDIFF('day', a.KYC_LAST_REVIEWED, CURRENT_DATE()) > 270 THEN 'DUE_SOON'
                ELSE 'CURRENT'
            END AS REVIEW_STATUS
        FROM REGULATORY_DW.REG_MODEL.DIM_ACCOUNT a
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_GEOGRAPHY g ON a.DOMICILE_GEOGRAPHY_KEY = g.GEOGRAPHY_KEY
        WHERE a.IS_CURRENT = TRUE
        ORDER BY a.AML_RISK_RATING DESC, DAYS_SINCE_KYC_REVIEW DESC
    """)


@st.cache_data
def load_reporting_gaps(month_start, month_end):
    """Transactions/positions that cannot be reported or categorized under a regulatory regime."""
    txn_gaps = conn.query("""
        SELECT * FROM (
        SELECT
            ft.TRANSACTION_ID,
            ft.TRADE_TIMESTAMP,
            ft.TRANSACTION_TYPE,
            ft.BUY_SELL_INDICATOR,
            ft.GROSS_AMOUNT,
            ft.TRADE_CURRENCY,
            ft.EXECUTION_VENUE,
            ft.EXECUTION_VENUE_MIC,
            ft.REPORTING_STATUS,
            ft.IS_CROSS_BORDER,
            ft.IS_SHORT_SALE,
            ft.ALGO_EXECUTION_FLAG,
            ft.BEST_EXECUTION_FLAG,
            s.SECURITY_NAME,
            s.ASSET_CLASS,
            s.ISIN,
            f.FUND_NAME,
            f.FUND_TYPE,
            f.UCITS_COMPLIANT,
            f.AIFMD_REPORTING_REQUIRED,
            tm.TRADE_MODEL_NAME,
            tm.ALGO_INDICATOR AS MODEL_IS_ALGO,
            tm.SHORT_SELLING_PERMITTED,
            tm.PRE_TRADE_TRANSPARENCY,
            tm.POST_TRADE_TRANSPARENCY,
            rj.JURISDICTION_NAME,
            rj.REGULATION_FRAMEWORK,
            -- Categorize the gap type
            CASE
                WHEN ft.JURISDICTION_KEY IS NULL THEN 'NO_JURISDICTION_MAPPED'
                WHEN ft.EXECUTION_VENUE_MIC IS NULL AND ft.EXECUTION_VENUE != 'OTC' THEN 'MISSING_VENUE_MIC'
                WHEN tm.ALGO_INDICATOR = TRUE AND ft.ALGO_EXECUTION_FLAG = FALSE THEN 'ALGO_FLAG_MISMATCH'
                WHEN ft.IS_SHORT_SALE = TRUE AND tm.SHORT_SELLING_PERMITTED = FALSE THEN 'SHORT_SALE_MODEL_VIOLATION'
                WHEN ft.REPORTING_STATUS != 'REPORTED' THEN 'NOT_YET_REPORTED'
                WHEN ft.BEST_EXECUTION_FLAG = FALSE THEN 'BEST_EXECUTION_FAILURE'
                WHEN s.ISIN IS NULL AND s.ASSET_CLASS != 'DERIVATIVE' THEN 'MISSING_ISIN'
                WHEN ft.IS_CROSS_BORDER = TRUE AND ft.SETTLEMENT_CURRENCY IS NULL THEN 'CROSS_BORDER_NO_SETTLEMENT_CCY'
                ELSE NULL
            END AS GAP_TYPE,
            CASE
                WHEN ft.JURISDICTION_KEY IS NULL THEN 'Cannot determine reporting regime'
                WHEN ft.EXECUTION_VENUE_MIC IS NULL AND ft.EXECUTION_VENUE != 'OTC' THEN 'MiFID II RTS 25 requires venue MIC'
                WHEN tm.ALGO_INDICATOR = TRUE AND ft.ALGO_EXECUTION_FLAG = FALSE THEN 'MiFID II Field 62 algo flag inconsistency'
                WHEN ft.IS_SHORT_SALE = TRUE AND tm.SHORT_SELLING_PERMITTED = FALSE THEN 'EU Short Selling Regulation breach'
                WHEN ft.REPORTING_STATUS != 'REPORTED' THEN 'Transaction not reported within deadline'
                WHEN ft.BEST_EXECUTION_FLAG = FALSE THEN 'MiFID II Best Execution obligation not met'
                WHEN s.ISIN IS NULL AND s.ASSET_CLASS != 'DERIVATIVE' THEN 'EMIR/MiFID require ISIN for instrument identification'
                WHEN ft.IS_CROSS_BORDER = TRUE AND ft.SETTLEMENT_CURRENCY IS NULL THEN 'Cross-border settlement currency required'
                ELSE NULL
            END AS GAP_DESCRIPTION,
            CASE
                WHEN ft.JURISDICTION_KEY IS NULL THEN 'ALL'
                WHEN ft.EXECUTION_VENUE_MIC IS NULL AND ft.EXECUTION_VENUE != 'OTC' THEN 'MiFID II'
                WHEN tm.ALGO_INDICATOR = TRUE AND ft.ALGO_EXECUTION_FLAG = FALSE THEN 'MiFID II'
                WHEN ft.IS_SHORT_SALE = TRUE AND tm.SHORT_SELLING_PERMITTED = FALSE THEN 'EU_SSR'
                WHEN ft.REPORTING_STATUS != 'REPORTED' THEN 'MiFID II / EMIR'
                WHEN ft.BEST_EXECUTION_FLAG = FALSE THEN 'MiFID II'
                WHEN s.ISIN IS NULL AND s.ASSET_CLASS != 'DERIVATIVE' THEN 'EMIR / MiFID II'
                WHEN ft.IS_CROSS_BORDER = TRUE AND ft.SETTLEMENT_CURRENCY IS NULL THEN 'EMIR / Basel III'
                ELSE NULL
            END AS AFFECTED_REGIME
        FROM REGULATORY_DW.REG_MODEL.FACT_TRANSACTION ft
        JOIN REGULATORY_DW.REG_MODEL.DIM_DATE d ON ft.TRADE_DATE_KEY = d.DATE_KEY
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_SECURITY s ON ft.SECURITY_KEY = s.SECURITY_KEY
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_FUND f ON ft.FUND_KEY = f.FUND_KEY
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_TRADE_MODEL tm ON ft.TRADE_MODEL_KEY = tm.TRADE_MODEL_KEY
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_REGULATORY_JURISDICTION rj ON ft.JURISDICTION_KEY = rj.JURISDICTION_KEY
        WHERE d.CALENDAR_DATE BETWEEN :1 AND :2
        ) WHERE GAP_TYPE IS NOT NULL
        ORDER BY GROSS_AMOUNT DESC
    """, params=[month_start, month_end])

    pos_gaps = conn.query("""
        SELECT * FROM (
        SELECT
            p.POSITION_KEY,
            p.AS_OF_DATE,
            p.QUANTITY,
            p.MARKET_VALUE_BASE,
            p.POSITION_TYPE,
            p.CONCENTRATION_BREACH,
            p.LEVERAGE_CONTRIBUTION,
            p.VAR_95,
            p.LIQUIDITY_DAYS,
            s.SECURITY_NAME,
            s.SECURITY_TYPE,
            s.ASSET_CLASS,
            s.ISIN,
            s.IS_OTC,
            s.IS_DERIVATIVE,
            s.LIQUIDITY_CLASSIFICATION,
            f.FUND_NAME,
            f.FUND_TYPE,
            f.UCITS_COMPLIANT,
            f.AIFMD_REPORTING_REQUIRED,
            cp.COUNTERPARTY_NAME,
            cp.CENTRAL_CLEARING_ELIGIBLE,
            cp.CSA_IN_PLACE,
            rj.JURISDICTION_NAME,
            -- Categorize position gap
            CASE
                WHEN p.JURISDICTION_KEY IS NULL THEN 'NO_JURISDICTION_MAPPED'
                WHEN p.CONCENTRATION_BREACH = TRUE THEN 'CONCENTRATION_LIMIT_BREACH'
                WHEN s.IS_DERIVATIVE = TRUE AND s.IS_OTC = TRUE AND cp.CENTRAL_CLEARING_ELIGIBLE = TRUE AND cp.COUNTERPARTY_NAME IS NOT NULL THEN 'OTC_NOT_CENTRALLY_CLEARED'
                WHEN s.IS_DERIVATIVE = TRUE AND p.COUNTERPARTY_KEY IS NULL THEN 'DERIVATIVE_NO_COUNTERPARTY'
                WHEN f.UCITS_COMPLIANT = TRUE AND p.LEVERAGE_CONTRIBUTION > 2.0 THEN 'UCITS_LEVERAGE_BREACH'
                WHEN s.ISIN IS NULL AND s.ASSET_CLASS != 'DERIVATIVE' THEN 'MISSING_ISIN'
                WHEN p.LIQUIDITY_DAYS > 7 AND f.FUND_TYPE = 'UCITS' THEN 'UCITS_LIQUIDITY_CONCERN'
                WHEN s.IS_DERIVATIVE = TRUE AND s.IS_OTC = TRUE AND cp.CSA_IN_PLACE = FALSE THEN 'OTC_NO_CSA'
                ELSE NULL
            END AS GAP_TYPE,
            CASE
                WHEN p.JURISDICTION_KEY IS NULL THEN 'Position cannot be assigned to any regulatory regime'
                WHEN p.CONCENTRATION_BREACH = TRUE THEN 'UCITS/Basel single-name concentration limit exceeded'
                WHEN s.IS_DERIVATIVE = TRUE AND s.IS_OTC = TRUE AND cp.CENTRAL_CLEARING_ELIGIBLE = TRUE AND cp.COUNTERPARTY_NAME IS NOT NULL THEN 'EMIR mandates central clearing for eligible OTC derivatives'
                WHEN s.IS_DERIVATIVE = TRUE AND p.COUNTERPARTY_KEY IS NULL THEN 'EMIR requires counterparty identification for all derivatives'
                WHEN f.UCITS_COMPLIANT = TRUE AND p.LEVERAGE_CONTRIBUTION > 2.0 THEN 'UCITS leverage limit (2x NAV) breached'
                WHEN s.ISIN IS NULL AND s.ASSET_CLASS != 'DERIVATIVE' THEN 'Instrument lacks ISIN for regulatory identification'
                WHEN p.LIQUIDITY_DAYS > 7 AND f.FUND_TYPE = 'UCITS' THEN 'UCITS requires adequate liquidity (redemption within 7 days)'
                WHEN s.IS_DERIVATIVE = TRUE AND s.IS_OTC = TRUE AND cp.CSA_IN_PLACE = FALSE THEN 'EMIR bilateral margin rules require CSA'
                ELSE NULL
            END AS GAP_DESCRIPTION,
            CASE
                WHEN p.JURISDICTION_KEY IS NULL THEN 'ALL'
                WHEN p.CONCENTRATION_BREACH = TRUE THEN 'UCITS / Basel III'
                WHEN s.IS_DERIVATIVE = TRUE AND s.IS_OTC = TRUE AND cp.CENTRAL_CLEARING_ELIGIBLE = TRUE THEN 'EMIR'
                WHEN s.IS_DERIVATIVE = TRUE AND p.COUNTERPARTY_KEY IS NULL THEN 'EMIR'
                WHEN f.UCITS_COMPLIANT = TRUE AND p.LEVERAGE_CONTRIBUTION > 2.0 THEN 'UCITS'
                WHEN s.ISIN IS NULL AND s.ASSET_CLASS != 'DERIVATIVE' THEN 'MiFID II / EMIR'
                WHEN p.LIQUIDITY_DAYS > 7 AND f.FUND_TYPE = 'UCITS' THEN 'UCITS'
                WHEN s.IS_DERIVATIVE = TRUE AND s.IS_OTC = TRUE AND cp.CSA_IN_PLACE = FALSE THEN 'EMIR'
                ELSE NULL
            END AS AFFECTED_REGIME
        FROM REGULATORY_DW.REG_MODEL.FACT_POSITION p
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_SECURITY s ON p.SECURITY_KEY = s.SECURITY_KEY
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_FUND f ON p.FUND_KEY = f.FUND_KEY
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_COUNTERPARTY cp ON p.COUNTERPARTY_KEY = cp.COUNTERPARTY_KEY
        LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_REGULATORY_JURISDICTION rj ON p.JURISDICTION_KEY = rj.JURISDICTION_KEY
        WHERE p.AS_OF_DATE = :1
        ) WHERE GAP_TYPE IS NOT NULL
        ORDER BY MARKET_VALUE_BASE DESC
    """, params=[month_end])

    return txn_gaps, pos_gaps


def clear_all_caches():
    load_available_months.clear()
    load_basel_summary.clear()
    load_mifid_summary.clear()
    load_aifmd_summary.clear()
    load_emir_summary.clear()
    load_ucits_summary.clear()
    load_aml_summary.clear()
    load_reporting_gaps.clear()


# Header
st.title("Regulatory Reporting Dashboard")
st.caption("Multi-jurisdictional compliance monitoring | REGULATORY_DW.REG_MODEL")

# Month filter in sidebar
with st.sidebar:
    st.header("Report Period")
    months_df = load_available_months()
    if months_df.empty:
        st.warning("No data available. Check REGULATORY_DW.REG_MODEL tables.")
        st.stop()
    month_options = months_df["MONTH_LABEL"].tolist()
    selected_month = st.selectbox("Select Month / Year", month_options, index=0)

    # Derive month_start and month_end from selection (already VARCHAR from TO_CHAR)
    selected_row = months_df[months_df["MONTH_LABEL"] == selected_month].iloc[0]
    month_end = selected_row["MONTH_END_DATE"]  # already 'YYYY-MM-DD' string
    month_start = month_end[:8] + "01"  # first day of same month

    st.caption(f"Period: {month_start} to {month_end}")
    st.button("Refresh Data", on_click=clear_all_caches)

# Tabs
tab_basel, tab_mifid, tab_aifmd, tab_emir, tab_ucits, tab_aml, tab_gaps = st.tabs(
    ["Basel III", "MiFID II", "AIFMD", "EMIR", "UCITS", "AML/KYC", "Reporting Gaps & Breaches"]
)

# ─── BASEL III ────────────────────────────────────────────────────────────────
with tab_basel:
    st.header("Basel III — Capital & Risk Metrics")
    df = load_basel_summary(month_end)

    if df.empty:
        st.info(f"No position data for {month_end}. Select a quarter-end with position snapshots.")
    else:
        with st.container(horizontal=True):
            st.metric("Total Exposure", f"${df['TOTAL_EXPOSURE'].sum():,.0f}", border=True)
            st.metric("Aggregate VaR (95%)", f"${df['TOTAL_VAR_95'].sum():,.0f}", border=True)
            st.metric("Aggregate VaR (99%)", f"${df['TOTAL_VAR_99'].sum():,.0f}", border=True)
            st.metric("Concentration Breaches", f"{int(df['CONCENTRATION_BREACHES'].sum())}", border=True)

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.subheader("Risk Exposure by Fund")
                st.bar_chart(df, x="FUND_NAME", y="TOTAL_EXPOSURE", horizontal=True)
        with col2:
            with st.container(border=True):
                st.subheader("VaR by Fund (95% vs 99%)")
                chart_df = df[["FUND_NAME", "TOTAL_VAR_95", "TOTAL_VAR_99"]].set_index("FUND_NAME")
                st.bar_chart(chart_df)

        st.subheader("Detailed Risk Data")
        st.dataframe(df, use_container_width=True, hide_index=True, column_config={
            "TOTAL_EXPOSURE": st.column_config.NumberColumn("Total Exposure", format="$%,.0f"),
            "TOTAL_VAR_95": st.column_config.NumberColumn("VaR 95%", format="$%,.0f"),
            "TOTAL_VAR_99": st.column_config.NumberColumn("VaR 99%", format="$%,.0f"),
            "WEIGHTED_LEVERAGE": st.column_config.NumberColumn("Wtd Leverage", format="%.2f"),
        })
        st.download_button("Download Basel III Data", df.to_csv(index=False), "basel_iii_data.csv", "text/csv")

# ─── MiFID II ─────────────────────────────────────────────────────────────────
with tab_mifid:
    st.header("MiFID II — Transaction Reporting & Best Execution")
    df = load_mifid_summary(month_start, month_end)

    total_trades = int(df["TOTAL_TRADES"].sum())
    best_exec_pct = 100.0 * df["BEST_EXEC_PASS"].sum() / max(total_trades, 1)
    algo_pct = 100.0 * df["ALGO_TRADES"].sum() / max(total_trades, 1)
    reported_pct = 100.0 * df["REPORTED_TRADES"].sum() / max(total_trades, 1)
    missing_mic = int(df["MISSING_MIC"].sum())

    with st.container(horizontal=True):
        st.metric("Total Trades", f"{total_trades}", border=True)
        st.metric("Best Execution %", f"{best_exec_pct:.1f}%", border=True)
        st.metric("Algo Execution %", f"{algo_pct:.1f}%", border=True)
        st.metric("Reporting Compliance", f"{reported_pct:.1f}%", border=True)
        st.metric("Missing Venue MIC", f"{missing_mic}", delta=f"{missing_mic} gaps" if missing_mic > 0 else "0", delta_color="inverse", border=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Notional by Execution Venue")
            venue_df = df.groupby("EXECUTION_VENUE", as_index=False)["TOTAL_NOTIONAL"].sum()
            st.bar_chart(venue_df, x="EXECUTION_VENUE", y="TOTAL_NOTIONAL")
    with col2:
        with st.container(border=True):
            st.subheader("Trades by Execution Method")
            method_df = df.groupby("EXECUTION_METHOD", as_index=False)["TOTAL_TRADES"].sum()
            st.bar_chart(method_df, x="EXECUTION_METHOD", y="TOTAL_TRADES")

    st.subheader("Detailed MiFID II Compliance Data")
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={
        "TOTAL_NOTIONAL": st.column_config.NumberColumn("Total Notional", format="$%,.0f"),
    })
    st.download_button("Download MiFID II Data", df.to_csv(index=False), "mifid_ii_data.csv", "text/csv")

# ─── AIFMD ────────────────────────────────────────────────────────────────────
with tab_aifmd:
    st.header("AIFMD — Alternative Investment Fund Reporting")
    df = load_aifmd_summary(month_start, month_end)

    total_aum = df["TOTAL_AUM"].sum()
    funds_in_scope = len(df)
    submitted = len(df[df["REPORT_STATUS"] == "SUBMITTED"])
    breaches = int(df["BREACHES_REPORTED"].sum())

    with st.container(horizontal=True):
        st.metric("Total AUM (In-Scope)", f"${total_aum:,.0f}", border=True)
        st.metric("Funds In Scope", f"{funds_in_scope}", border=True)
        st.metric("Reports Submitted", f"{submitted}/{funds_in_scope}", border=True)
        st.metric("Breaches Reported", f"{breaches}", border=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Gross Leverage by Fund")
            st.bar_chart(df, x="FUND_NAME", y="GROSS_LEVERAGE", horizontal=True)
    with col2:
        with st.container(border=True):
            st.subheader("AUM by Fund Type")
            type_df = df.groupby("FUND_TYPE", as_index=False)["TOTAL_AUM"].sum()
            st.bar_chart(type_df, x="FUND_TYPE", y="TOTAL_AUM")

    st.subheader("Detailed AIFMD Reporting Data")
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={
        "TOTAL_AUM": st.column_config.NumberColumn("Total AUM", format="$%,.0f"),
        "GROSS_LEVERAGE": st.column_config.NumberColumn("Gross Leverage", format="%.2fx"),
    })
    st.download_button("Download AIFMD Data", df.to_csv(index=False), "aifmd_data.csv", "text/csv")

# ─── EMIR ─────────────────────────────────────────────────────────────────────
with tab_emir:
    st.header("EMIR — Derivative Reporting & Counterparty Exposure")
    df = load_emir_summary(month_end)

    total_deriv_exposure = df["EXPOSURE"].sum()
    otc_count = len(df[df["IS_OTC"] == True])
    clearing_eligible = len(df[df["CENTRAL_CLEARING_ELIGIBLE"] == True])
    csa_coverage = len(df[df["CSA_IN_PLACE"] == True])

    with st.container(horizontal=True):
        st.metric("Derivative Exposure", f"${total_deriv_exposure:,.0f}", border=True)
        st.metric("OTC Positions", f"{otc_count}", border=True)
        st.metric("Clearing Eligible", f"{clearing_eligible}/{len(df)}", border=True)
        st.metric("CSA Coverage", f"{csa_coverage}/{len(df)}", border=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Exposure by Derivative Type")
            type_df = df.groupby("SUB_ASSET_CLASS", as_index=False)["EXPOSURE"].sum()
            st.bar_chart(type_df, x="SUB_ASSET_CLASS", y="EXPOSURE")
    with col2:
        with st.container(border=True):
            st.subheader("Exposure by Counterparty")
            cp_df = df[df["COUNTERPARTY_NAME"].notna()].groupby("COUNTERPARTY_NAME", as_index=False)["EXPOSURE"].sum()
            if not cp_df.empty:
                st.bar_chart(cp_df, x="COUNTERPARTY_NAME", y="EXPOSURE", horizontal=True)
            else:
                st.info("No counterparty-linked derivative positions found.")

    st.subheader("Detailed EMIR Derivative Data")
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={
        "EXPOSURE": st.column_config.NumberColumn("Exposure", format="$%,.0f"),
        "MARGIN_REQUIREMENT": st.column_config.NumberColumn("Margin Req", format="$%,.0f"),
        "COLLATERAL_PLEDGED": st.column_config.NumberColumn("Collateral", format="$%,.0f"),
    })
    st.download_button("Download EMIR Data", df.to_csv(index=False), "emir_data.csv", "text/csv")

# ─── UCITS ────────────────────────────────────────────────────────────────────
with tab_ucits:
    st.header("UCITS — Fund Compliance & Concentration Limits")
    df = load_ucits_summary(month_end)

    total_ucits_aum = df["TOTAL_AUM"].sum()
    ucits_funds = len(df)
    total_breaches = int(df["BREACHES"].sum())
    max_concentration = df["MAX_SINGLE_POSITION_PCT"].max()

    with st.container(horizontal=True):
        st.metric("UCITS Fund Count", f"{ucits_funds}", border=True)
        st.metric("Total UCITS AUM", f"${total_ucits_aum:,.0f}", border=True)
        st.metric("Concentration Breaches", f"{total_breaches}", border=True)
        st.metric("Max Single Position %", f"{max_concentration:.2f}%", border=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("AUM by UCITS Fund")
            st.bar_chart(df, x="FUND_NAME", y="TOTAL_AUM")
    with col2:
        with st.container(border=True):
            st.subheader("Leverage Ratio vs Limit (1.0x)")
            st.bar_chart(df, x="FUND_NAME", y="LEVERAGE_RATIO")

    st.subheader("Detailed UCITS Compliance Data")
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={
        "TOTAL_AUM": st.column_config.NumberColumn("Total AUM", format="$%,.0f"),
        "TOTAL_MV": st.column_config.NumberColumn("Total MV", format="$%,.0f"),
        "DERIVATIVE_EXPOSURE": st.column_config.NumberColumn("Derivative Exp", format="$%,.0f"),
        "LEVERAGE_RATIO": st.column_config.NumberColumn("Leverage", format="%.2fx"),
        "MAX_SINGLE_POSITION_PCT": st.column_config.NumberColumn("Max Position %", format="%.2f%%"),
    })
    st.download_button("Download UCITS Data", df.to_csv(index=False), "ucits_data.csv", "text/csv")

# ─── AML/KYC ──────────────────────────────────────────────────────────────────
with tab_aml:
    st.header("AML/KYC — Client Due Diligence & Risk Monitoring")
    df = load_aml_summary()

    total_clients = len(df)
    high_risk = len(df[df["AML_RISK_RATING"] == "MEDIUM"]) + len(df[df["AML_RISK_RATING"] == "HIGH"])
    overdue_reviews = len(df[df["REVIEW_STATUS"] == "OVERDUE"])
    due_soon = len(df[df["REVIEW_STATUS"] == "DUE_SOON"])

    with st.container(horizontal=True):
        st.metric("Total Clients", f"{total_clients}", border=True)
        st.metric("Medium/High Risk", f"{high_risk}", border=True)
        st.metric("KYC Reviews Overdue", f"{overdue_reviews}", delta=f"{overdue_reviews} overdue" if overdue_reviews > 0 else "0", delta_color="inverse", border=True)
        st.metric("Reviews Due Soon", f"{due_soon}", border=True)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("AML Risk Distribution")
            risk_df = df.groupby("AML_RISK_RATING", as_index=False).size()
            risk_df.columns = ["AML_RISK_RATING", "COUNT"]
            st.bar_chart(risk_df, x="AML_RISK_RATING", y="COUNT")
    with col2:
        with st.container(border=True):
            st.subheader("KYC Review Status")
            status_df = df.groupby("REVIEW_STATUS", as_index=False).size()
            status_df.columns = ["REVIEW_STATUS", "COUNT"]
            st.bar_chart(status_df, x="REVIEW_STATUS", y="COUNT")

    st.subheader("Detailed AML/KYC Client Data")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Download AML/KYC Data", df.to_csv(index=False), "aml_kyc_data.csv", "text/csv")

# ─── REPORTING GAPS & BREACHES ────────────────────────────────────────────────
with tab_gaps:
    st.header("Reporting Gaps & Regulatory Breaches")
    st.caption("Transactions and positions that cannot be reported or are in breach of regulatory regime requirements")

    txn_gaps, pos_gaps = load_reporting_gaps(month_start, month_end)

    total_txn_gaps = len(txn_gaps)
    total_pos_gaps = len(pos_gaps)
    total_exposure_at_risk = pos_gaps["MARKET_VALUE_BASE"].sum() if not pos_gaps.empty else 0
    total_notional_at_risk = txn_gaps["GROSS_AMOUNT"].sum() if not txn_gaps.empty else 0

    with st.container(horizontal=True):
        st.metric("Transaction Gaps", f"{total_txn_gaps}", delta=f"{total_txn_gaps} issues" if total_txn_gaps > 0 else "0", delta_color="inverse", border=True)
        st.metric("Position Gaps", f"{total_pos_gaps}", delta=f"{total_pos_gaps} issues" if total_pos_gaps > 0 else "0", delta_color="inverse", border=True)
        st.metric("Notional at Risk (Txns)", f"${total_notional_at_risk:,.0f}", border=True)
        st.metric("Exposure at Risk (Pos)", f"${total_exposure_at_risk:,.0f}", border=True)

    # Summary by regime
    st.subheader("Gap Distribution by Regulatory Regime")
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("**Transaction Gaps by Regime**")
            if not txn_gaps.empty:
                regime_txn = txn_gaps.groupby("AFFECTED_REGIME", as_index=False).agg(
                    COUNT=("TRANSACTION_ID", "count"),
                    TOTAL_NOTIONAL=("GROSS_AMOUNT", "sum")
                )
                st.bar_chart(regime_txn, x="AFFECTED_REGIME", y="COUNT")
                st.dataframe(regime_txn, use_container_width=True, hide_index=True, column_config={
                    "TOTAL_NOTIONAL": st.column_config.NumberColumn("Total Notional", format="$%,.0f"),
                })
            else:
                st.success("No transaction reporting gaps found.")

    with col2:
        with st.container(border=True):
            st.markdown("**Position Gaps by Regime**")
            if not pos_gaps.empty:
                regime_pos = pos_gaps.groupby("AFFECTED_REGIME", as_index=False).agg(
                    COUNT=("POSITION_KEY", "count"),
                    TOTAL_EXPOSURE=("MARKET_VALUE_BASE", "sum")
                )
                st.bar_chart(regime_pos, x="AFFECTED_REGIME", y="COUNT")
                st.dataframe(regime_pos, use_container_width=True, hide_index=True, column_config={
                    "TOTAL_EXPOSURE": st.column_config.NumberColumn("Total Exposure", format="$%,.0f"),
                })
            else:
                st.success("No position reporting gaps found.")

    # Gap type breakdown
    st.subheader("Breach Details by Gap Type")
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("**Transaction Gap Types**")
            if not txn_gaps.empty:
                gap_type_txn = txn_gaps.groupby("GAP_TYPE", as_index=False).agg(
                    COUNT=("TRANSACTION_ID", "count"),
                    TOTAL_NOTIONAL=("GROSS_AMOUNT", "sum")
                )
                st.bar_chart(gap_type_txn, x="GAP_TYPE", y="TOTAL_NOTIONAL", horizontal=True)
            else:
                st.success("No transaction gaps.")

    with col2:
        with st.container(border=True):
            st.markdown("**Position Gap Types**")
            if not pos_gaps.empty:
                gap_type_pos = pos_gaps.groupby("GAP_TYPE", as_index=False).agg(
                    COUNT=("POSITION_KEY", "count"),
                    TOTAL_EXPOSURE=("MARKET_VALUE_BASE", "sum")
                )
                st.bar_chart(gap_type_pos, x="GAP_TYPE", y="TOTAL_EXPOSURE", horizontal=True)
            else:
                st.success("No position gaps.")

    # Detailed data tables
    st.subheader("Transaction Reporting Gaps — Detail")
    if not txn_gaps.empty:
        st.dataframe(txn_gaps, use_container_width=True, hide_index=True, column_config={
            "GROSS_AMOUNT": st.column_config.NumberColumn("Gross Amount", format="$%,.0f"),
        })
        st.download_button(
            "Download Transaction Gaps",
            txn_gaps.to_csv(index=False),
            "transaction_reporting_gaps.csv",
            "text/csv",
        )
    else:
        st.success("All transactions are reportable under their assigned regulatory regimes.")

    st.subheader("Position Reporting Gaps — Detail")
    if not pos_gaps.empty:
        st.dataframe(pos_gaps, use_container_width=True, hide_index=True, column_config={
            "MARKET_VALUE_BASE": st.column_config.NumberColumn("Market Value", format="$%,.0f"),
            "VAR_95": st.column_config.NumberColumn("VaR 95%", format="$%,.0f"),
        })
        st.download_button(
            "Download Position Gaps",
            pos_gaps.to_csv(index=False),
            "position_reporting_gaps.csv",
            "text/csv",
        )
    else:
        st.success("All positions are reportable under their assigned regulatory regimes.")
