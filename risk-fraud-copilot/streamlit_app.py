# Regulatory Risk & Compliance Copilot — NL chat interface for fraud, risk, and regulatory reporting
# Co-authored with CoCo
import os
import json
import streamlit as st
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark import Session
from datetime import datetime

st.set_page_config(
    page_title="Risk & Regulatory Copilot",
    page_icon=":material/shield:",
    layout="wide",
)

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))

# ─── SCHEMA CONTEXT FOR THE LLM ──────────────────────────────────────────────
SCHEMA_CONTEXT = """
You are a regulatory compliance copilot for a multi-geographical investment management firm.
You have access to the REGULATORY_DW.REG_MODEL data warehouse with these tables:

DIMENSION TABLES:
- DIM_ACCOUNT: Institutional clients (ACCOUNT_KEY, ACCOUNT_ID, ACCOUNT_NAME, ACCOUNT_TYPE [PENSION_FUND, SOVEREIGN_WEALTH, ENDOWMENT, INSURANCE, ASSET_MANAGER], CLIENT_CLASSIFICATION, LEI_CODE, DOMICILE_GEOGRAPHY_KEY, PRIMARY_CURRENCY, AUM_BAND, RISK_PROFILE, KYC_STATUS, KYC_LAST_REVIEWED, AML_RISK_RATING [LOW/MEDIUM/HIGH], ONBOARDING_DATE, STATUS, IS_CURRENT)
- DIM_SECURITY: Instruments (SECURITY_KEY, SECURITY_ID, ISIN, CUSIP, SEDOL, TICKER, SECURITY_NAME, SECURITY_TYPE, ASSET_CLASS [EQUITY/FIXED_INCOME/DERIVATIVE/CREDIT], SUB_ASSET_CLASS, ISSUER_NAME, ISSUER_LEI, ISSUE_CURRENCY, MATURITY_DATE, COUPON_RATE, CREDIT_RATING, IS_OTC, IS_DERIVATIVE, EXCHANGE_CODE, TRADING_VENUE_MIC, LIQUIDITY_CLASSIFICATION, ESG_RATING, SFDR_CLASSIFICATION, IS_CURRENT)
- DIM_FUND: Funds (FUND_KEY, FUND_ID, FUND_NAME, FUND_TYPE [HEDGE_FUND/UCITS/MUTUAL_FUND/AIF/PRIVATE_FUND], FUND_STRUCTURE, INVESTMENT_STRATEGY, ASSET_CLASS_FOCUS, BENCHMARK_INDEX, BASE_CURRENCY, TOTAL_AUM, UCITS_COMPLIANT, AIFMD_REPORTING_REQUIRED, FORM_PF_REPORTING_REQUIRED, LEVERAGE_RATIO, IS_CURRENT)
- DIM_TRADE_MODEL: Execution models (TRADE_MODEL_KEY, TRADE_MODEL_NAME, MODEL_CATEGORY [QUANTITATIVE/DISCRETIONARY/PASSIVE/ILLIQUID], EXECUTION_METHOD [ALGORITHMIC/MANUAL/HYBRID], ALGO_INDICATOR, HFT_INDICATOR, SHORT_SELLING_PERMITTED, PRE_TRADE_TRANSPARENCY, POST_TRADE_TRANSPARENCY, RISK_LIMIT_TYPE, RISK_LIMIT_VALUE, IS_CURRENT)
- DIM_COUNTERPARTY: Brokers/CCPs (COUNTERPARTY_KEY, COUNTERPARTY_NAME, COUNTERPARTY_TYPE [INVESTMENT_BANK/CCP/MARKET_MAKER/COMMERCIAL_BANK], LEI_CODE, BIC_CODE, CREDIT_RATING, NETTING_AGREEMENT, CSA_IN_PLACE, INITIAL_MARGIN_REQUIRED, CENTRAL_CLEARING_ELIGIBLE, CCP_MEMBER, SANCTIONS_SCREENED_DATE, SANCTIONS_STATUS, IS_CURRENT)
- DIM_REGULATORY_JURISDICTION: Regulators (JURISDICTION_KEY, JURISDICTION_CODE [SEC/FCA/ESMA/MAS/SFC/JFSA/ASIC/CSSF/FINMA/CIMA], JURISDICTION_NAME, REGULATION_FRAMEWORK, REPORTING_FREQUENCY, REPORTING_DEADLINE_DAYS)
- DIM_GEOGRAPHY: Countries (GEOGRAPHY_KEY, COUNTRY_CODE, COUNTRY_NAME, REGION, REGULATORY_ZONE, IS_EU_MEMBER, IS_OECD_MEMBER)
- DIM_DATE: Calendar (DATE_KEY as YYYYMMDD, CALENDAR_DATE, IS_BUSINESS_DAY, IS_QUARTER_END, REGULATORY_REPORTING_PERIOD)

FACT TABLES:
- FACT_TRANSACTION: Trades (TRANSACTION_KEY, TRANSACTION_ID, TRADE_DATE_KEY->DIM_DATE, ACCOUNT_KEY->DIM_ACCOUNT, FUND_KEY->DIM_FUND, SECURITY_KEY->DIM_SECURITY, COUNTERPARTY_KEY->DIM_COUNTERPARTY, TRADE_MODEL_KEY->DIM_TRADE_MODEL, JURISDICTION_KEY->DIM_REGULATORY_JURISDICTION, EXECUTION_GEOGRAPHY_KEY->DIM_GEOGRAPHY, TRANSACTION_TYPE, BUY_SELL_INDICATOR, ORDER_TYPE, EXECUTION_VENUE, EXECUTION_VENUE_MIC, QUANTITY, PRICE, TRADE_CURRENCY, GROSS_AMOUNT, NET_AMOUNT, COMMISSION, FEES, SETTLEMENT_CURRENCY, SETTLEMENT_AMOUNT, FX_RATE, IS_SHORT_SALE, IS_CROSS_BORDER, IS_PRINCIPAL_TRADE, IS_AGENCY_TRADE, ALGO_EXECUTION_FLAG, BEST_EXECUTION_FLAG, REPORTING_STATUS [PENDING/REPORTED/FAILED], TRADE_TIMESTAMP, EXECUTION_TIMESTAMP, REPORTING_TIMESTAMP)
- FACT_POSITION: Holdings (POSITION_KEY, POSITION_DATE_KEY->DIM_DATE, ACCOUNT_KEY, FUND_KEY, SECURITY_KEY, COUNTERPARTY_KEY, JURISDICTION_KEY, GEOGRAPHY_KEY, QUANTITY, MARKET_VALUE_LOCAL, MARKET_VALUE_BASE, COST_BASIS_BASE, UNREALIZED_PNL, ACCRUED_INCOME, LOCAL_CURRENCY, BASE_CURRENCY, FX_RATE, WEIGHT_IN_FUND_PCT, DURATION, DELTA, GAMMA, VEGA, VAR_95, VAR_99, CONCENTRATION_LIMIT_PCT, CONCENTRATION_BREACH, LEVERAGE_CONTRIBUTION, COLLATERAL_PLEDGED, MARGIN_REQUIREMENT, LIQUIDITY_DAYS, POSITION_TYPE [LONG/SHORT], AS_OF_DATE)
- FACT_REGULATORY_REPORT: Filings (REPORT_KEY, REPORT_ID, JURISDICTION_KEY, FUND_KEY, REPORT_TYPE [FORM_PF/AIFMD_ANNEX_IV/MIFID_TRANSACTION_REPORT/UCITS_REPORTING/JFSA_QUARTERLY/CIMA_FAR/MAS_FORM_1A], REPORTING_PERIOD_START, REPORTING_PERIOD_END, SUBMISSION_DEADLINE, ACTUAL_SUBMISSION_DATE, REPORT_STATUS [NOT_STARTED/IN_PROGRESS/SUBMITTED/LATE/AMENDED], TOTAL_AUM_REPORTED, GROSS_LEVERAGE_REPORTED, BREACHES_REPORTED, LATE_REPORTS_COUNT, VALIDATION_ERRORS)

KEY REGULATORY THRESHOLDS:
- Basel III: Leverage ratio minimum 3%; Large exposure single counterparty max 25% of Tier 1 capital
- MiFID II: Transaction reported within T+1 (86400 seconds); Best execution required; Algo flagging mandatory
- UCITS: Single position max 10% of NAV; Total derivative exposure max 100% NAV; Max leverage typically 2x
- EMIR: Mandatory clearing for eligible OTC derivatives; CSA required for bilateral OTC
- AML/KYC: Review within 12 months (DATEDIFF day KYC_LAST_REVIEWED CURRENT_DATE > 365 = overdue)
- AIFMD: Quarterly Annex IV reporting; Leverage disclosure required

RESPONSE FORMAT:
You must respond with a valid JSON object (no markdown, no code fences) with these keys:
{
  "finding": "Clear 2-3 sentence summary of what you found",
  "regulation": "Which regulation(s) apply (e.g. Basel III, MiFID II, UCITS)",
  "severity": "CRITICAL / HIGH / MEDIUM / LOW / INFO",
  "sql": "The exact Snowflake SQL query to execute for evidence. Use REGULATORY_DW.REG_MODEL.TABLE_NAME. Use AS_OF_DATE = '2026-06-30' for positions. Must be a single SELECT statement.",
  "remediation": "Specific recommended action to resolve the finding",
  "audit_note": "One-line note suitable for an audit log entry"
}

RULES:
- Always use fully-qualified table names: REGULATORY_DW.REG_MODEL.<TABLE>
- For current dimension data, filter IS_CURRENT = TRUE
- For positions, use AS_OF_DATE = '2026-06-30' (latest snapshot)
- SQL must be a single executable SELECT statement
- Be specific about which regulatory article/rule applies
- Severity: CRITICAL = immediate action needed, HIGH = material breach, MEDIUM = requires attention, LOW = minor gap, INFO = informational
"""


# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_risk_signals():
    result = conn.query("""
        SELECT
            (SELECT COUNT(*) FROM REGULATORY_DW.REG_MODEL.DIM_FUND
             WHERE IS_CURRENT = TRUE AND LEVERAGE_RATIO > 3.0) AS LEVERAGE_BREACHES,
            (SELECT COUNT(*) FROM REGULATORY_DW.REG_MODEL.DIM_ACCOUNT
             WHERE IS_CURRENT = TRUE AND DATEDIFF('day', KYC_LAST_REVIEWED, CURRENT_DATE()) > 365) AS KYC_OVERDUE,
            (SELECT COUNT(*) FROM REGULATORY_DW.REG_MODEL.FACT_REGULATORY_REPORT
             WHERE REPORT_STATUS = 'LATE') AS LATE_REPORTS,
            (SELECT COUNT(*) FROM REGULATORY_DW.REG_MODEL.FACT_POSITION
             WHERE AS_OF_DATE = '2026-06-30' AND CONCENTRATION_BREACH = TRUE) AS CONCENTRATION_BREACHES,
            (SELECT COUNT(*) FROM REGULATORY_DW.REG_MODEL.FACT_TRANSACTION
             WHERE REPORTING_STATUS != 'REPORTED') AS UNREPORTED_TRADES
    """)
    row = result.iloc[0]
    return row["LEVERAGE_BREACHES"], row["KYC_OVERDUE"], row["LATE_REPORTS"], row["CONCENTRATION_BREACHES"], row["UNREPORTED_TRADES"]


RULE_BASED_QUERIES = {
    "leverage": {
        "finding": "Checking Basel III leverage ratio compliance across all funds. Funds exceeding 3.0x leverage are flagged.",
        "regulation": "Basel III — Leverage Ratio Framework",
        "severity": "HIGH",
        "sql": """SELECT FUND_ID, FUND_NAME, FUND_TYPE, LEVERAGE_RATIO, TOTAL_AUM, BASE_CURRENCY,
    CASE WHEN LEVERAGE_RATIO > 3.0 THEN 'BREACH' ELSE 'COMPLIANT' END AS STATUS
FROM REGULATORY_DW.REG_MODEL.DIM_FUND
WHERE IS_CURRENT = TRUE
ORDER BY LEVERAGE_RATIO DESC""",
        "remediation": "Funds with leverage > 3.0x require immediate deleveraging plan or additional capital buffers.",
        "audit_note": "Basel III leverage ratio check executed"
    },
    "mifid": {
        "finding": "Checking MiFID II transaction reporting compliance — venue MIC codes, algo flagging, and reporting timeliness.",
        "regulation": "MiFID II / MiFIR — RTS 25, Transaction Reporting",
        "severity": "MEDIUM",
        "sql": """SELECT ft.TRANSACTION_ID, ft.EXECUTION_VENUE, ft.EXECUTION_VENUE_MIC,
    ft.ALGO_EXECUTION_FLAG, ft.BEST_EXECUTION_FLAG, ft.REPORTING_STATUS,
    ft.IS_CROSS_BORDER, ft.GROSS_AMOUNT, ft.TRADE_CURRENCY,
    tm.TRADE_MODEL_NAME, tm.ALGO_INDICATOR AS MODEL_IS_ALGO,
    CASE
        WHEN ft.EXECUTION_VENUE_MIC IS NULL AND ft.EXECUTION_VENUE != 'OTC' THEN 'MISSING_VENUE_MIC'
        WHEN tm.ALGO_INDICATOR = TRUE AND ft.ALGO_EXECUTION_FLAG = FALSE THEN 'ALGO_FLAG_MISMATCH'
        WHEN ft.REPORTING_STATUS != 'REPORTED' THEN 'NOT_REPORTED'
        WHEN ft.BEST_EXECUTION_FLAG = FALSE THEN 'BEST_EXEC_FAILURE'
        ELSE 'COMPLIANT'
    END AS COMPLIANCE_STATUS
FROM REGULATORY_DW.REG_MODEL.FACT_TRANSACTION ft
LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_TRADE_MODEL tm ON ft.TRADE_MODEL_KEY = tm.TRADE_MODEL_KEY
ORDER BY ft.GROSS_AMOUNT DESC""",
        "remediation": "Review flagged transactions — ensure MIC codes are populated, algo flags match model config, and all trades are reported within T+1.",
        "audit_note": "MiFID II compliance gap analysis executed"
    },
    "kyc": {
        "finding": "Checking AML/KYC review status for all active accounts. Reviews overdue beyond 365 days are flagged.",
        "regulation": "AML 4th/5th Directive — Customer Due Diligence",
        "severity": "HIGH",
        "sql": """SELECT ACCOUNT_ID, ACCOUNT_NAME, CLIENT_TYPE, AML_RISK_RATING, KYC_STATUS,
    KYC_LAST_REVIEWED, DATEDIFF('day', KYC_LAST_REVIEWED, CURRENT_DATE()) AS DAYS_SINCE_REVIEW,
    CASE
        WHEN DATEDIFF('day', KYC_LAST_REVIEWED, CURRENT_DATE()) > 365 THEN 'OVERDUE'
        WHEN DATEDIFF('day', KYC_LAST_REVIEWED, CURRENT_DATE()) > 270 THEN 'DUE_SOON'
        ELSE 'CURRENT'
    END AS REVIEW_STATUS
FROM REGULATORY_DW.REG_MODEL.DIM_ACCOUNT
WHERE IS_CURRENT = TRUE
ORDER BY DAYS_SINCE_REVIEW DESC""",
        "remediation": "Initiate enhanced due diligence reviews for overdue accounts, prioritizing those with MEDIUM/HIGH AML risk ratings.",
        "audit_note": "AML/KYC periodic review status check executed"
    },
    "emir": {
        "finding": "Checking EMIR derivative reporting — OTC exposure, clearing eligibility, and CSA coverage.",
        "regulation": "EMIR — OTC Derivatives, Central Clearing",
        "severity": "MEDIUM",
        "sql": """SELECT s.SECURITY_NAME, s.SECURITY_TYPE, s.SUB_ASSET_CLASS, s.IS_OTC,
    cp.COUNTERPARTY_NAME, cp.CENTRAL_CLEARING_ELIGIBLE, cp.CSA_IN_PLACE, cp.NETTING_AGREEMENT,
    p.MARKET_VALUE_BASE AS EXPOSURE, f.FUND_NAME,
    CASE
        WHEN s.IS_OTC = TRUE AND cp.CENTRAL_CLEARING_ELIGIBLE = TRUE AND cp.CCP_MEMBER = FALSE THEN 'SHOULD_BE_CLEARED'
        WHEN s.IS_OTC = TRUE AND cp.CSA_IN_PLACE = FALSE THEN 'MISSING_CSA'
        WHEN p.COUNTERPARTY_KEY IS NULL THEN 'NO_COUNTERPARTY_MAPPED'
        ELSE 'COMPLIANT'
    END AS EMIR_STATUS
FROM REGULATORY_DW.REG_MODEL.FACT_POSITION p
JOIN REGULATORY_DW.REG_MODEL.DIM_SECURITY s ON p.SECURITY_KEY = s.SECURITY_KEY
LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_COUNTERPARTY cp ON p.COUNTERPARTY_KEY = cp.COUNTERPARTY_KEY
JOIN REGULATORY_DW.REG_MODEL.DIM_FUND f ON p.FUND_KEY = f.FUND_KEY
WHERE s.IS_DERIVATIVE = TRUE AND p.AS_OF_DATE = '2026-06-30'
ORDER BY p.MARKET_VALUE_BASE DESC""",
        "remediation": "Migrate clearing-eligible OTC positions to CCPs. Establish CSA agreements for remaining bilateral positions.",
        "audit_note": "EMIR derivative clearing and CSA compliance check executed"
    },
    "filing": {
        "finding": "Checking regulatory report submission status — identifying late, overdue, or not-started filings.",
        "regulation": "Multiple — AIFMD, Form PF, UCITS, MiFID II",
        "severity": "HIGH",
        "sql": """SELECT rr.REPORT_ID, rr.REPORT_TYPE, rr.REPORT_STATUS,
    rr.REPORTING_PERIOD_START, rr.REPORTING_PERIOD_END,
    rr.SUBMISSION_DEADLINE, rr.ACTUAL_SUBMISSION_DATE,
    CASE WHEN rr.ACTUAL_SUBMISSION_DATE > rr.SUBMISSION_DEADLINE THEN 'LATE'
         WHEN rr.ACTUAL_SUBMISSION_DATE IS NULL AND rr.SUBMISSION_DEADLINE < CURRENT_DATE() THEN 'OVERDUE'
         ELSE rr.REPORT_STATUS END AS EFFECTIVE_STATUS,
    rj.JURISDICTION_NAME, rj.REGULATION_FRAMEWORK, f.FUND_NAME,
    rr.BREACHES_REPORTED, rr.VALIDATION_ERRORS
FROM REGULATORY_DW.REG_MODEL.FACT_REGULATORY_REPORT rr
JOIN REGULATORY_DW.REG_MODEL.DIM_REGULATORY_JURISDICTION rj ON rr.JURISDICTION_KEY = rj.JURISDICTION_KEY
LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_FUND f ON rr.FUND_KEY = f.FUND_KEY
ORDER BY rr.SUBMISSION_DEADLINE ASC""",
        "remediation": "Escalate overdue filings to compliance officer. Submit late reports with explanatory cover letters to regulators.",
        "audit_note": "Regulatory filing status review executed"
    },
    "counterparty": {
        "finding": "Checking counterparty concentration exposure against Basel III large exposure limits (25% Tier 1 capital).",
        "regulation": "Basel III — Large Exposures Framework (LEX)",
        "severity": "MEDIUM",
        "sql": """SELECT cp.COUNTERPARTY_NAME, cp.COUNTERPARTY_TYPE, cp.CREDIT_RATING,
    SUM(p.MARKET_VALUE_BASE) AS TOTAL_EXPOSURE,
    COUNT(*) AS POSITION_COUNT,
    cp.NETTING_AGREEMENT, cp.CSA_IN_PLACE,
    cp.SANCTIONS_STATUS, cp.SANCTIONS_SCREENED_DATE
FROM REGULATORY_DW.REG_MODEL.FACT_POSITION p
JOIN REGULATORY_DW.REG_MODEL.DIM_COUNTERPARTY cp ON p.COUNTERPARTY_KEY = cp.COUNTERPARTY_KEY
WHERE p.AS_OF_DATE = '2026-06-30'
GROUP BY cp.COUNTERPARTY_NAME, cp.COUNTERPARTY_TYPE, cp.CREDIT_RATING,
         cp.NETTING_AGREEMENT, cp.CSA_IN_PLACE, cp.SANCTIONS_STATUS, cp.SANCTIONS_SCREENED_DATE
ORDER BY TOTAL_EXPOSURE DESC""",
        "remediation": "Review top counterparty exposures against internal limits. Ensure netting agreements and CSA documentation is current.",
        "audit_note": "Counterparty concentration risk check executed"
    },
    "aifmd": {
        "finding": "Checking AIFMD Annex IV reporting compliance — fund leverage, AUM disclosure, and submission status for Alternative Investment Funds.",
        "regulation": "AIFMD — Annex IV Reporting (Articles 3, 24)",
        "severity": "HIGH",
        "sql": """SELECT f.FUND_ID, f.FUND_NAME, f.FUND_TYPE, f.FUND_STRUCTURE, f.TOTAL_AUM,
    f.LEVERAGE_RATIO AS GROSS_LEVERAGE, f.BASE_CURRENCY, f.AIFMD_REPORTING_REQUIRED,
    g.COUNTRY_NAME AS DOMICILE,
    rr.REPORT_TYPE, rr.REPORT_STATUS, rr.REPORTING_PERIOD_START, rr.REPORTING_PERIOD_END,
    rr.SUBMISSION_DEADLINE, rr.ACTUAL_SUBMISSION_DATE, rr.BREACHES_REPORTED,
    rr.GROSS_LEVERAGE_REPORTED, rr.TOTAL_AUM_REPORTED
FROM REGULATORY_DW.REG_MODEL.DIM_FUND f
LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_GEOGRAPHY g ON f.DOMICILE_GEOGRAPHY_KEY = g.GEOGRAPHY_KEY
LEFT JOIN REGULATORY_DW.REG_MODEL.FACT_REGULATORY_REPORT rr
    ON rr.FUND_KEY = f.FUND_KEY AND rr.REPORT_TYPE = 'AIFMD_ANNEX_IV'
WHERE f.AIFMD_REPORTING_REQUIRED = TRUE AND f.IS_CURRENT = TRUE
ORDER BY f.TOTAL_AUM DESC""",
        "remediation": "Ensure all AIFMD-reporting funds have submitted Annex IV within the quarterly deadline. Escalate any late or not-started reports.",
        "audit_note": "AIFMD Annex IV reporting compliance check executed"
    },
    "ucits": {
        "finding": "Checking UCITS fund compliance — concentration limits, leverage constraints, and derivative exposure caps.",
        "regulation": "UCITS Directive — Articles 52-56, Eligible Assets",
        "severity": "MEDIUM",
        "sql": """SELECT f.FUND_ID, f.FUND_NAME, f.TOTAL_AUM, f.LEVERAGE_RATIO, f.BASE_CURRENCY,
    COUNT(p.POSITION_KEY) AS POSITIONS,
    SUM(p.MARKET_VALUE_BASE) AS TOTAL_MV,
    MAX(p.WEIGHT_IN_FUND_PCT) AS MAX_SINGLE_POSITION_PCT,
    SUM(CASE WHEN p.CONCENTRATION_BREACH = TRUE THEN 1 ELSE 0 END) AS BREACHES,
    SUM(CASE WHEN s.ASSET_CLASS = 'DERIVATIVE' THEN p.MARKET_VALUE_BASE ELSE 0 END) AS DERIVATIVE_EXPOSURE
FROM REGULATORY_DW.REG_MODEL.DIM_FUND f
LEFT JOIN REGULATORY_DW.REG_MODEL.FACT_POSITION p ON f.FUND_KEY = p.FUND_KEY AND p.AS_OF_DATE = '2026-06-30'
LEFT JOIN REGULATORY_DW.REG_MODEL.DIM_SECURITY s ON p.SECURITY_KEY = s.SECURITY_KEY
WHERE f.UCITS_COMPLIANT = TRUE AND f.IS_CURRENT = TRUE
GROUP BY f.FUND_ID, f.FUND_NAME, f.TOTAL_AUM, f.LEVERAGE_RATIO, f.BASE_CURRENCY
ORDER BY f.TOTAL_AUM DESC""",
        "remediation": "Reduce positions exceeding 10% NAV single-issuer limit. Ensure total derivative exposure remains below 100% NAV.",
        "audit_note": "UCITS directive compliance check executed"
    },
    "form_pf": {
        "finding": "Checking SEC Form PF reporting status for qualifying hedge funds and private funds.",
        "regulation": "Dodd-Frank — Form PF (SEC/CFTC)",
        "severity": "HIGH",
        "sql": """SELECT f.FUND_ID, f.FUND_NAME, f.FUND_TYPE, f.TOTAL_AUM, f.LEVERAGE_RATIO,
    f.FORM_PF_REPORTING_REQUIRED, f.BASE_CURRENCY,
    rr.REPORT_TYPE, rr.REPORT_STATUS, rr.REPORTING_PERIOD_START, rr.REPORTING_PERIOD_END,
    rr.SUBMISSION_DEADLINE, rr.ACTUAL_SUBMISSION_DATE,
    rr.TOTAL_AUM_REPORTED, rr.GROSS_LEVERAGE_REPORTED, rr.BREACHES_REPORTED
FROM REGULATORY_DW.REG_MODEL.DIM_FUND f
LEFT JOIN REGULATORY_DW.REG_MODEL.FACT_REGULATORY_REPORT rr
    ON rr.FUND_KEY = f.FUND_KEY AND rr.REPORT_TYPE = 'FORM_PF'
WHERE f.FORM_PF_REPORTING_REQUIRED = TRUE AND f.IS_CURRENT = TRUE
ORDER BY f.TOTAL_AUM DESC""",
        "remediation": "Ensure Form PF is filed within 60 days of quarter-end for large hedge fund advisers. Verify AUM and leverage figures match position data.",
        "audit_note": "SEC Form PF reporting status check executed"
    },
    "concentration": {
        "finding": "Checking position concentration breaches — positions exceeding fund-level limits.",
        "regulation": "UCITS / Basel III — Concentration Limits",
        "severity": "HIGH",
        "sql": """SELECT p.POSITION_KEY, s.SECURITY_NAME, f.FUND_NAME, f.FUND_TYPE,
    p.MARKET_VALUE_BASE, p.WEIGHT_IN_FUND_PCT, p.CONCENTRATION_BREACH,
    p.LEVERAGE_CONTRIBUTION, p.POSITION_TYPE
FROM REGULATORY_DW.REG_MODEL.FACT_POSITION p
JOIN REGULATORY_DW.REG_MODEL.DIM_SECURITY s ON p.SECURITY_KEY = s.SECURITY_KEY
JOIN REGULATORY_DW.REG_MODEL.DIM_FUND f ON p.FUND_KEY = f.FUND_KEY
WHERE p.AS_OF_DATE = '2026-06-30'
ORDER BY p.WEIGHT_IN_FUND_PCT DESC NULLS LAST""",
        "remediation": "Reduce oversized positions to within regulatory limits. For UCITS funds, no single position should exceed 10% of NAV.",
        "audit_note": "Position concentration limit check executed"
    },
}


def match_rule_based(question):
    q = question.lower()
    # Check regime-specific keywords FIRST to avoid misrouting
    if any(k in q for k in ["aifmd", "annex iv", "annex 4", "alternative investment fund", "aif reporting"]):
        return RULE_BASED_QUERIES["aifmd"]
    if any(k in q for k in ["ucits", "ucit", "eligible assets", "5/10/40"]):
        return RULE_BASED_QUERIES["ucits"]
    if any(k in q for k in ["form pf", "form-pf", "dodd-frank", "dodd frank", "sec reporting"]):
        return RULE_BASED_QUERIES["form_pf"]
    if any(k in q for k in ["mifid", "mifir", "transaction report", "venue mic", "algo flag", "best execution", "rts 25"]):
        return RULE_BASED_QUERIES["mifid"]
    if any(k in q for k in ["emir", "otc derivative", "central clearing", "csa agreement", "swap reporting"]):
        return RULE_BASED_QUERIES["emir"]
    if any(k in q for k in ["leverage", "basel", "capital adequacy", "rwa", "tier 1"]):
        return RULE_BASED_QUERIES["leverage"]
    if any(k in q for k in ["kyc", "aml", "due diligence", "overdue review", "sanctions", "client risk", "money laundering"]):
        return RULE_BASED_QUERIES["kyc"]
    if any(k in q for k in ["counterparty", "single-counterparty", "large exposure", "broker exposure"]):
        return RULE_BASED_QUERIES["counterparty"]
    if any(k in q for k in ["concentration", "position limit", "weight limit", "single position"]):
        return RULE_BASED_QUERIES["concentration"]
    # Generic terms matched LAST — only if no specific regime was identified above
    if any(k in q for k in ["filing", "late report", "overdue report", "submission", "report status", "deadline"]):
        return RULE_BASED_QUERIES["filing"]
    if any(k in q for k in ["derivative", "otc", "clearing"]):
        return RULE_BASED_QUERIES["emir"]
    return None


def call_copilot(user_question, model):
    # Skip LLM if we already know Cortex AI is unavailable (trial account)
    if st.session_state.get("cortex_unavailable", False):
        matched = match_rule_based(user_question)
        if matched:
            return json.dumps(matched)
        return json.dumps({
            "finding": "Could not match your question to a specific regulatory check. Try asking about: Basel III leverage, MiFID II reporting, AIFMD Annex IV, AML/KYC reviews, EMIR derivatives, UCITS compliance, Form PF, regulatory filings, counterparty exposure, or concentration limits.",
            "regulation": "General",
            "severity": "INFO",
            "sql": "",
            "remediation": "Rephrase your question using regulatory keywords (e.g. AIFMD, leverage, KYC, EMIR, MiFID, UCITS, filings).",
            "audit_note": "Rule-based fallback — Cortex AI not available on this account"
        })

    chat_history = ""
    if len(st.session_state.messages) > 1:
        recent = st.session_state.messages[-6:]
        for m in recent:
            role = m["role"]
            content = m["content"] if isinstance(m["content"], str) else json.dumps(m.get("parsed", ""))
            chat_history += f"{role}: {content[:200]}\n"

    full_prompt = f"""{SCHEMA_CONTEXT}

CHAT HISTORY:
{chat_history}

USER QUESTION: {user_question}

Respond with a JSON object only. No markdown fences. No explanation outside the JSON."""

    try:
        escaped_prompt = full_prompt.replace("'", "''")
        result_df = conn.query(
            f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{escaped_prompt}') AS RESPONSE"
        )
        return result_df.iloc[0]["RESPONSE"]
    except Exception as e:
        error_msg = str(e)
        # Fallback to rule-based matching when Cortex AI is unavailable (e.g. trial accounts)
        if "not available" in error_msg.lower() or "0A000" in error_msg:
            st.session_state["cortex_unavailable"] = True
            matched = match_rule_based(user_question)
            if matched:
                return json.dumps(matched)
            return json.dumps({
                "finding": "Could not match your question to a specific regulatory check. Try asking about: Basel III leverage, MiFID II reporting, AIFMD Annex IV, AML/KYC reviews, EMIR derivatives, UCITS compliance, Form PF, regulatory filings, counterparty exposure, or concentration limits.",
                "regulation": "General",
                "severity": "INFO",
                "sql": "",
                "remediation": "Rephrase your question using regulatory keywords (e.g. AIFMD, leverage, KYC, EMIR, MiFID, UCITS, filings).",
                "audit_note": "Rule-based fallback — Cortex AI not available on this account"
            })
        return json.dumps({
            "finding": f"Error calling model: {error_msg}",
            "regulation": "N/A",
            "severity": "INFO",
            "sql": "",
            "remediation": "Try a different model or rephrase your question.",
            "audit_note": "Model call failed"
        })


def parse_response(response_text):
    try:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        return None


def render_finding(parsed, model_name, show_evidence_flag, show_data_flag):
    severity = parsed.get("severity", "INFO")
    severity_icons = {
        "CRITICAL": ":red[:material/error:]",
        "HIGH": ":orange[:material/warning:]",
        "MEDIUM": ":yellow[:material/info:]",
        "LOW": ":blue[:material/check_circle:]",
        "INFO": ":gray[:material/info:]",
    }
    icon = severity_icons.get(severity, ":gray[:material/info:]")

    # Severity + Regulation badge
    st.markdown(f"{icon} **{severity}** | {parsed.get('regulation', 'N/A')}")

    # Finding
    st.markdown(f"**Finding:** {parsed.get('finding', 'No finding available.')}")

    # Remediation
    remediation = parsed.get("remediation", "")
    if remediation and remediation.lower() != "no action required":
        with st.container(border=True):
            st.markdown(f":material/build: **Recommended Action**")
            st.write(remediation)
    else:
        st.success(":material/check_circle: No action required — compliant.")

    # Evidence
    sql = parsed.get("sql", "")
    if sql and show_evidence_flag:
        with st.expander(":material/database: Evidence — SQL & Data", expanded=True):
            st.code(sql, language="sql")

            if show_data_flag and sql.strip().upper().startswith("SELECT"):
                try:
                    with st.spinner("Executing evidence query..."):
                        evidence_df = conn.query(sql)
                    if not evidence_df.empty:
                        st.dataframe(evidence_df, use_container_width=True, hide_index=True)
                        st.download_button(
                            ":material/download: Download Evidence (CSV)",
                            evidence_df.to_csv(index=False),
                            f"evidence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            "text/csv",
                        )
                    else:
                        st.info("Query returned no results — no issues found for this check.")
                except Exception as e:
                    st.error(f"Query execution error: {str(e)}")
    elif not sql:
        st.caption(":material/info: No SQL evidence query for this check.")

    # Audit trail
    audit_note = parsed.get("audit_note", "")
    if audit_note:
        st.caption(f":material/history: {audit_note} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Model: {model_name}")


def render_history_message(parsed):
    if not parsed or "raw" in parsed:
        st.write(parsed.get("raw", "") if parsed else "")
        return
    severity = parsed.get("severity", "INFO")
    severity_icons = {
        "CRITICAL": ":red[:material/error:]",
        "HIGH": ":orange[:material/warning:]",
        "MEDIUM": ":yellow[:material/info:]",
        "LOW": ":blue[:material/check_circle:]",
        "INFO": ":gray[:material/info:]",
    }
    icon = severity_icons.get(severity, ":gray[:material/info:]")
    st.markdown(f"{icon} **{severity}** | {parsed.get('regulation', 'N/A')}")
    st.markdown(f"{parsed.get('finding', '')}")
    remediation = parsed.get("remediation", "")
    if remediation and remediation.lower() != "no action required":
        st.caption(f":material/build: {remediation}")


# ─── SIDEBAR: RISK SIGNALS ────────────────────────────────────────────────────
with st.sidebar:
    st.title(":material/shield: Risk Copilot")

    # Show mode indicator
    if st.session_state.get("cortex_unavailable", False):
        st.info(":material/rule: **Rule-Based Mode**  \nCortex AI unavailable on this account. Using built-in regulatory rules engine.", icon=":material/info:")
    else:
        st.success(":material/smart_toy: **AI Mode**  \nPowered by Snowflake Cortex AI", icon=":material/check_circle:")

    st.divider()

    model_choice = st.selectbox(
        "LLM Model",
        ["claude-sonnet-4-6", "llama3.1-70b", "mistral-large2"],
        index=0,
    )
    show_evidence = st.toggle("Show SQL Evidence", value=True)
    show_raw_data = st.toggle("Show Data Tables", value=True)

    st.divider()
    st.markdown("### :material/monitoring: Live Risk Signals")

    lev, kyc, late, conc, unrep = load_risk_signals()

    with st.container(horizontal=True):
        st.metric("Leverage", int(lev), delta=f"{int(lev)}" if lev > 0 else None, delta_color="inverse", border=True)
        st.metric("KYC Overdue", int(kyc), delta=f"{int(kyc)}" if kyc > 0 else None, delta_color="inverse", border=True)

    with st.container(horizontal=True):
        st.metric("Late Filings", int(late), delta=f"{int(late)}" if late > 0 else None, delta_color="inverse", border=True)
        st.metric("Unreported", int(unrep), delta=f"{int(unrep)}" if unrep > 0 else None, delta_color="inverse", border=True)

    st.divider()
    st.caption(f"Snapshot: 2026-06-30 | {datetime.now().strftime('%H:%M')}")

    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()


# ─── MAIN: CHAT INTERFACE ─────────────────────────────────────────────────────
st.title("Regulatory Compliance Copilot")
st.caption("Ask natural language questions about risk, fraud, and regulatory compliance. Get governed, evidence-backed, audit-ready answers.")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Pre-check Cortex AI availability once at startup
if "cortex_unavailable" not in st.session_state:
    try:
        conn.query("SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-70b', 'Say OK') AS R")
        st.session_state["cortex_unavailable"] = False
    except Exception as e:
        if "not available" in str(e).lower() or "0A000" in str(e):
            st.session_state["cortex_unavailable"] = True
        else:
            st.session_state["cortex_unavailable"] = True

# Suggestion chips
SUGGESTIONS = {
    ":blue[:material/warning:] Basel III leverage": "Show me all Basel III leverage ratio breaches across our funds. Which funds exceed safe leverage limits?",
    ":red[:material/gavel:] MiFID II gaps": "Are there any MiFID II transaction reporting gaps? Check for missing venue MIC codes, algo flag mismatches, and unreported trades.",
    ":orange[:material/person:] AML/KYC overdue": "Which client accounts have overdue KYC reviews? Show their risk ratings and days since last review.",
    ":green[:material/trending_up:] EMIR derivatives": "What is our OTC derivative exposure under EMIR? Are there positions eligible for central clearing that are not cleared?",
    ":violet[:material/description:] Late filings": "Show me all late or overdue regulatory report filings with their deadlines and submission status.",
    ":blue[:material/account_tree:] Counterparty risk": "What is our largest single-counterparty exposure? Are we within Basel III large exposure limits?",
}

if not st.session_state.messages:
    selected = st.pills("Try asking:", list(SUGGESTIONS.keys()), label_visibility="collapsed")
    if selected:
        st.session_state.messages.append({"role": "user", "content": SUGGESTIONS[selected]})
        st.rerun()

# Display chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar=":material/person:"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant", avatar=":material/shield:"):
            parsed = msg.get("parsed")
            if parsed and "raw" not in parsed:
                render_history_message(parsed)
            else:
                st.write(msg.get("content", ""))

# Chat input handler
if prompt := st.chat_input("Ask about risk, fraud, or regulatory compliance..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar=":material/person:"):
        st.write(prompt)

    with st.chat_message("assistant", avatar=":material/shield:"):
        # Show a visible progress indicator
        status_container = st.status("Analyzing regulatory data...", expanded=True)
        with status_container:
            st.write(":material/search: Matching question to regulatory framework...")
            response_text = call_copilot(prompt, model_choice)
            st.write(":material/check: Analysis complete. Rendering findings...")

        status_container.update(label="Analysis complete", state="complete", expanded=False)

        parsed = parse_response(response_text)
        if parsed:
            render_finding(parsed, model_choice, show_evidence, show_raw_data)
            st.session_state.messages.append({"role": "assistant", "content": response_text, "parsed": parsed})
        else:
            # If JSON parsing fails, try to show whatever we got
            st.warning("Could not parse structured response. Showing raw output:")
            st.code(response_text, language="json")
            st.session_state.messages.append({"role": "assistant", "content": response_text, "parsed": {"raw": response_text}})
