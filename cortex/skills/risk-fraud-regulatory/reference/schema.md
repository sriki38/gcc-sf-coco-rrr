# REGULATORY_DW.REG_MODEL — Schema Reference

## Database & Schema
- **Database:** REGULATORY_DW
- **Schema:** REG_MODEL
- **Pattern:** Star schema (Kimball dimensional model) with SCD Type 2 dimensions

## Dimension Tables

### DIM_ACCOUNT
Institutional client accounts (pension funds, sovereign wealth, endowments, insurers, asset managers).

| Column | Type | Description |
|--------|------|-------------|
| ACCOUNT_KEY | INT (PK) | Surrogate key |
| ACCOUNT_ID | VARCHAR(50) | Business key |
| ACCOUNT_NAME | VARCHAR(200) | Client name |
| ACCOUNT_TYPE | VARCHAR(50) | PENSION_FUND, SOVEREIGN_WEALTH, ENDOWMENT, INSURANCE, ASSET_MANAGER |
| CLIENT_TYPE | VARCHAR(50) | INSTITUTIONAL |
| CLIENT_CLASSIFICATION | VARCHAR(50) | PROFESSIONAL, ELIGIBLE_COUNTERPARTY |
| LEI_CODE | VARCHAR(20) | Legal Entity Identifier |
| TAX_ID | VARCHAR(50) | Tax identification number |
| DOMICILE_GEOGRAPHY_KEY | INT (FK) | → DIM_GEOGRAPHY |
| REGISTRATION_GEOGRAPHY_KEY | INT (FK) | → DIM_GEOGRAPHY |
| PRIMARY_CURRENCY | VARCHAR(3) | Base currency |
| AUM_BAND | VARCHAR(50) | >10B, 5B-10B, 1B-5B, 500M-1B |
| RISK_PROFILE | VARCHAR(50) | CONSERVATIVE, MODERATE, AGGRESSIVE |
| KYC_STATUS | VARCHAR(30) | APPROVED, PENDING, EXPIRED |
| KYC_LAST_REVIEWED | DATE | Last KYC review date |
| AML_RISK_RATING | VARCHAR(20) | LOW, MEDIUM, HIGH |
| ONBOARDING_DATE | DATE | Client onboarding date |
| STATUS | VARCHAR(20) | ACTIVE, INACTIVE |
| RELATIONSHIP_MANAGER | VARCHAR(100) | RM name |
| EFFECTIVE_FROM / EFFECTIVE_TO / IS_CURRENT | SCD2 | Type 2 slowly changing dimension |

### DIM_SECURITY
Financial instruments across asset classes.

| Column | Type | Description |
|--------|------|-------------|
| SECURITY_KEY | INT (PK) | Surrogate key |
| SECURITY_ID | VARCHAR(50) | Internal ID |
| ISIN | VARCHAR(12) | International Securities Identification Number |
| CUSIP | VARCHAR(9) | US/Canada identifier |
| SEDOL | VARCHAR(7) | UK identifier |
| TICKER | VARCHAR(20) | Exchange ticker |
| SECURITY_NAME | VARCHAR(300) | Full name |
| SECURITY_TYPE | VARCHAR(50) | EQUITY, GOVERNMENT_BOND, CORPORATE_BOND, OPTION, IRS, FUTURE, FX_FORWARD, CONTINGENT_CONVERTIBLE |
| ASSET_CLASS | VARCHAR(50) | EQUITY, FIXED_INCOME, DERIVATIVE, CREDIT |
| SUB_ASSET_CLASS | VARCHAR(100) | US Large Cap, Sovereign, Interest Rate, etc. |
| ISSUER_NAME | VARCHAR(200) | Issuer entity name |
| ISSUER_LEI | VARCHAR(20) | Issuer LEI |
| ISSUER_GEOGRAPHY_KEY | INT (FK) | → DIM_GEOGRAPHY |
| ISSUE_CURRENCY | VARCHAR(3) | Currency of issuance |
| ISSUE_DATE / MATURITY_DATE | DATE | Lifecycle dates |
| COUPON_RATE | DECIMAL(10,6) | For fixed income |
| CREDIT_RATING | VARCHAR(10) | S&P/Moody's rating |
| IS_OTC | BOOLEAN | Over-the-counter flag |
| IS_DERIVATIVE | BOOLEAN | Derivative instrument flag |
| UNDERLYING_SECURITY_KEY | INT (FK) | Self-reference for derivatives |
| EXCHANGE_CODE | VARCHAR(20) | Listed exchange |
| TRADING_VENUE_MIC | VARCHAR(10) | MiFID II Market Identifier Code |
| LIQUIDITY_CLASSIFICATION | VARCHAR(20) | HIGHLY_LIQUID, LIQUID, LESS_LIQUID, ILLIQUID |
| ESG_RATING | VARCHAR(10) | ESG score |
| SFDR_CLASSIFICATION | VARCHAR(20) | ARTICLE_6, ARTICLE_8, ARTICLE_9 |

### DIM_FUND
Investment fund vehicles.

| Column | Type | Description |
|--------|------|-------------|
| FUND_KEY | INT (PK) | Surrogate key |
| FUND_ID | VARCHAR(50) | Business key |
| FUND_NAME | VARCHAR(200) | Fund name |
| FUND_TYPE | VARCHAR(50) | HEDGE_FUND, UCITS, MUTUAL_FUND, AIF, PRIVATE_FUND, COLLECTIVE_INVESTMENT |
| FUND_STRUCTURE | VARCHAR(50) | LIMITED_PARTNERSHIP, SICAV, UNIT_TRUST, OPEN_END, CONTRACTUAL |
| INVESTMENT_STRATEGY | VARCHAR(100) | Long/Short Equity, Global Macro, etc. |
| ASSET_CLASS_FOCUS | VARCHAR(100) | EQUITY, FIXED_INCOME, MULTI_ASSET, REAL_ESTATE, CREDIT |
| BENCHMARK_INDEX | VARCHAR(200) | Performance benchmark |
| DOMICILE_GEOGRAPHY_KEY | INT (FK) | → DIM_GEOGRAPHY |
| PRIMARY_JURISDICTION_KEY | INT (FK) | → DIM_REGULATORY_JURISDICTION |
| BASE_CURRENCY | VARCHAR(3) | Fund base currency |
| INCEPTION_DATE | DATE | Fund launch date |
| NAV_FREQUENCY | VARCHAR(20) | DAILY, WEEKLY, MONTHLY, QUARTERLY |
| MANAGEMENT_FEE_BPS | DECIMAL(10,2) | Management fee in basis points |
| PERFORMANCE_FEE_PCT | DECIMAL(5,2) | Performance fee percentage |
| TOTAL_AUM | DECIMAL(20,2) | Assets under management |
| UCITS_COMPLIANT | BOOLEAN | UCITS compliance flag |
| AIFMD_REPORTING_REQUIRED | BOOLEAN | AIFMD reporting obligation |
| FORM_PF_REPORTING_REQUIRED | BOOLEAN | SEC Form PF obligation |
| LEVERAGE_RATIO | DECIMAL(10,4) | Gross leverage ratio |

### DIM_TRADE_MODEL
Execution strategies and trading models.

| Column | Type | Description |
|--------|------|-------------|
| TRADE_MODEL_KEY | INT (PK) | Surrogate key |
| TRADE_MODEL_ID | VARCHAR(50) | Business key |
| TRADE_MODEL_NAME | VARCHAR(200) | Model name |
| MODEL_CATEGORY | VARCHAR(50) | QUANTITATIVE, DISCRETIONARY, PASSIVE, ILLIQUID |
| STRATEGY_TYPE | VARCHAR(100) | Long/Short Equity, Global Macro, Relative Value, etc. |
| EXECUTION_METHOD | VARCHAR(50) | ALGORITHMIC, MANUAL, HYBRID, NEGOTIATED |
| ORDER_ROUTING_TYPE | VARCHAR(50) | SMART_ORDER_ROUTING, DIRECT_MARKET_ACCESS, COLOCATION, RFQ_PLATFORM, OFF_EXCHANGE |
| ALGO_INDICATOR | BOOLEAN | MiFID II algorithmic trading flag |
| HFT_INDICATOR | BOOLEAN | High-frequency trading flag |
| SHORT_SELLING_PERMITTED | BOOLEAN | Short selling allowed |
| PRE_TRADE_TRANSPARENCY | BOOLEAN | Pre-trade transparency required |
| POST_TRADE_TRANSPARENCY | BOOLEAN | Post-trade transparency required |
| MAX_POSITION_SIZE | DECIMAL(20,2) | Maximum allowed position |
| RISK_LIMIT_TYPE | VARCHAR(50) | GROSS_EXPOSURE, VAR_95, DURATION_LIMIT, etc. |
| RISK_LIMIT_VALUE | DECIMAL(20,4) | Risk limit threshold |
| APPROVED_JURISDICTIONS | VARCHAR(500) | Comma-separated jurisdiction codes |

### DIM_COUNTERPARTY
Brokers, banks, CCPs, and market makers.

| Column | Type | Description |
|--------|------|-------------|
| COUNTERPARTY_KEY | INT (PK) | Surrogate key |
| COUNTERPARTY_ID | VARCHAR(50) | Business key |
| COUNTERPARTY_NAME | VARCHAR(200) | Entity name |
| COUNTERPARTY_TYPE | VARCHAR(50) | INVESTMENT_BANK, COMMERCIAL_BANK, CCP, MARKET_MAKER |
| LEI_CODE | VARCHAR(20) | Legal Entity Identifier |
| BIC_CODE | VARCHAR(11) | SWIFT/BIC code |
| DOMICILE_GEOGRAPHY_KEY | INT (FK) | → DIM_GEOGRAPHY |
| CREDIT_RATING | VARCHAR(10) | Credit rating |
| NETTING_AGREEMENT | BOOLEAN | ISDA netting in place |
| CSA_IN_PLACE | BOOLEAN | Credit Support Annex signed |
| INITIAL_MARGIN_REQUIRED | BOOLEAN | IM posting required |
| CENTRAL_CLEARING_ELIGIBLE | BOOLEAN | Eligible for CCP clearing |
| CCP_MEMBER | BOOLEAN | Is a CCP member |
| SANCTIONS_SCREENED_DATE | DATE | Last sanctions screen |
| SANCTIONS_STATUS | VARCHAR(30) | CLEAR, FLAGGED, BLOCKED |

### DIM_REGULATORY_JURISDICTION
Regulatory bodies and reporting requirements.

| Column | Type | Description |
|--------|------|-------------|
| JURISDICTION_KEY | INT (PK) | Surrogate key |
| JURISDICTION_CODE | VARCHAR(20) | SEC, FCA, ESMA, MAS, SFC, JFSA, ASIC, CSSF, FINMA, CIMA |
| JURISDICTION_NAME | VARCHAR(200) | Full regulator name |
| REGULATORY_BODY | VARCHAR(200) | Regulator short name |
| GEOGRAPHY_KEY | INT (FK) | → DIM_GEOGRAPHY |
| REGULATION_FRAMEWORK | VARCHAR(100) | Dodd-Frank, MiFID II, AIFMD, SFA, etc. |
| REPORTING_FREQUENCY | VARCHAR(50) | DAILY, MONTHLY, QUARTERLY, SEMI-ANNUAL, ANNUAL |
| REPORTING_DEADLINE_DAYS | INT | Days after period end |

### DIM_GEOGRAPHY
Country and regional reference data.

| Column | Type | Description |
|--------|------|-------------|
| GEOGRAPHY_KEY | INT (PK) | Surrogate key |
| COUNTRY_CODE | VARCHAR(3) | ISO 3166 alpha-3 |
| COUNTRY_NAME | VARCHAR(100) | Country name |
| REGION | VARCHAR(50) | North America, Europe, Asia Pacific, Caribbean |
| SUB_REGION | VARCHAR(100) | Sub-region |
| REGULATORY_ZONE | VARCHAR(50) | Regulatory zone mapping |
| CURRENCY_CODE | VARCHAR(3) | Local currency |
| IS_EU_MEMBER | BOOLEAN | EU membership |
| IS_OECD_MEMBER | BOOLEAN | OECD membership |

### DIM_DATE
Calendar dimension (2024–2026).

| Column | Type | Description |
|--------|------|-------------|
| DATE_KEY | INT (PK) | YYYYMMDD integer |
| CALENDAR_DATE | DATE | Date value |
| DAY_OF_WEEK / DAY_NAME / DAY_OF_MONTH | INT/VARCHAR | Day attributes |
| MONTH_NUM / MONTH_NAME / QUARTER_NUM / YEAR_NUM | INT/VARCHAR | Period attributes |
| IS_BUSINESS_DAY | BOOLEAN | Weekday flag |
| IS_MONTH_END / IS_QUARTER_END / IS_YEAR_END | BOOLEAN | Period-end flags |
| REGULATORY_REPORTING_PERIOD | VARCHAR(20) | e.g., "2026-Q2" |

## Fact Tables

### FACT_TRANSACTION
Trade-level data with MiFID II compliance fields.

| Column | Type | Description |
|--------|------|-------------|
| TRANSACTION_KEY | INT (PK) | Surrogate key |
| TRANSACTION_ID | VARCHAR(50) | Business transaction ID |
| TRADE_DATE_KEY | INT (FK) | → DIM_DATE |
| SETTLEMENT_DATE_KEY | INT (FK) | → DIM_DATE |
| ACCOUNT_KEY | INT (FK) | → DIM_ACCOUNT |
| FUND_KEY | INT (FK) | → DIM_FUND |
| SECURITY_KEY | INT (FK) | → DIM_SECURITY |
| COUNTERPARTY_KEY | INT (FK) | → DIM_COUNTERPARTY |
| TRADE_MODEL_KEY | INT (FK) | → DIM_TRADE_MODEL |
| JURISDICTION_KEY | INT (FK) | → DIM_REGULATORY_JURISDICTION |
| EXECUTION_GEOGRAPHY_KEY | INT (FK) | → DIM_GEOGRAPHY |
| TRANSACTION_TYPE | VARCHAR(20) | BUY, SELL |
| BUY_SELL_INDICATOR | VARCHAR(4) | BUY, SELL |
| ORDER_TYPE | VARCHAR(30) | LIMIT, MARKET, RFQ, AUCTION |
| EXECUTION_VENUE | VARCHAR(100) | Venue name |
| EXECUTION_VENUE_MIC | VARCHAR(10) | MiFID II MIC code |
| QUANTITY | DECIMAL(20,6) | Trade quantity |
| PRICE | DECIMAL(20,8) | Execution price |
| TRADE_CURRENCY | VARCHAR(3) | Trade currency |
| GROSS_AMOUNT / NET_AMOUNT | DECIMAL(20,4) | Trade amounts |
| COMMISSION / FEES / TAX_AMOUNT | DECIMAL(20,4) | Cost components |
| SETTLEMENT_CURRENCY / SETTLEMENT_AMOUNT | VARCHAR(3) / DECIMAL | Settlement details |
| FX_RATE | DECIMAL(15,8) | FX conversion rate |
| IS_SHORT_SALE | BOOLEAN | Short selling flag |
| IS_CROSS_BORDER | BOOLEAN | Cross-border transaction |
| IS_PRINCIPAL_TRADE / IS_AGENCY_TRADE | BOOLEAN | Trading capacity |
| ALGO_EXECUTION_FLAG | BOOLEAN | Algorithmic execution |
| BEST_EXECUTION_FLAG | BOOLEAN | Best execution achieved |
| REPORTING_STATUS | VARCHAR(30) | PENDING, REPORTED, FAILED |
| TRADE_TIMESTAMP / EXECUTION_TIMESTAMP / REPORTING_TIMESTAMP | TIMESTAMP_NTZ | Lifecycle timestamps |

### FACT_POSITION
Point-in-time holdings with risk metrics.

| Column | Type | Description |
|--------|------|-------------|
| POSITION_KEY | INT (PK) | Surrogate key |
| POSITION_DATE_KEY | INT (FK) | → DIM_DATE |
| ACCOUNT_KEY | INT (FK) | → DIM_ACCOUNT |
| FUND_KEY | INT (FK) | → DIM_FUND |
| SECURITY_KEY | INT (FK) | → DIM_SECURITY |
| COUNTERPARTY_KEY | INT (FK) | → DIM_COUNTERPARTY |
| JURISDICTION_KEY | INT (FK) | → DIM_REGULATORY_JURISDICTION |
| GEOGRAPHY_KEY | INT (FK) | → DIM_GEOGRAPHY |
| QUANTITY | DECIMAL(20,6) | Position quantity |
| MARKET_VALUE_LOCAL / MARKET_VALUE_BASE | DECIMAL(20,4) | Market values |
| COST_BASIS_LOCAL / COST_BASIS_BASE | DECIMAL(20,4) | Cost basis |
| UNREALIZED_PNL | DECIMAL(20,4) | Unrealized P&L |
| REALIZED_PNL_YTD | DECIMAL(20,4) | YTD realized P&L |
| ACCRUED_INCOME | DECIMAL(20,4) | Accrued interest/dividends |
| LOCAL_CURRENCY / BASE_CURRENCY | VARCHAR(3) | Currencies |
| FX_RATE | DECIMAL(15,8) | FX rate |
| WEIGHT_IN_FUND_PCT | DECIMAL(10,6) | Position weight in fund |
| DURATION / MODIFIED_DURATION / CONVEXITY | DECIMAL | Fixed income risk |
| DELTA / GAMMA / VEGA | DECIMAL | Greeks for derivatives |
| VAR_95 / VAR_99 | DECIMAL(20,4) | Value at Risk |
| CONCENTRATION_LIMIT_PCT | DECIMAL(10,4) | Concentration limit |
| CONCENTRATION_BREACH | BOOLEAN | Limit breach flag |
| LEVERAGE_CONTRIBUTION | DECIMAL(10,4) | Leverage contribution |
| COLLATERAL_PLEDGED | DECIMAL(20,4) | Collateral posted |
| MARGIN_REQUIREMENT | DECIMAL(20,4) | Margin required |
| LIQUIDITY_DAYS | INT | Days to liquidate |
| POSITION_TYPE | VARCHAR(20) | LONG, SHORT |
| AS_OF_DATE | DATE | Position snapshot date |

### FACT_REGULATORY_REPORT
Regulatory filing tracker.

| Column | Type | Description |
|--------|------|-------------|
| REPORT_KEY | INT (PK) | Surrogate key |
| REPORT_ID | VARCHAR(50) | Report identifier |
| JURISDICTION_KEY | INT (FK) | → DIM_REGULATORY_JURISDICTION |
| FUND_KEY | INT (FK) | → DIM_FUND |
| ACCOUNT_KEY | INT (FK) | → DIM_ACCOUNT |
| REPORT_TYPE | VARCHAR(100) | FORM_PF, AIFMD_ANNEX_IV, MIFID_TRANSACTION_REPORT, UCITS_REPORTING, etc. |
| REPORTING_PERIOD_START / REPORTING_PERIOD_END | DATE | Filing period |
| SUBMISSION_DEADLINE | DATE | Due date |
| ACTUAL_SUBMISSION_DATE | DATE | When filed (NULL if not yet) |
| REPORT_STATUS | VARCHAR(30) | NOT_STARTED, IN_PROGRESS, SUBMITTED, LATE, AMENDED |
| TOTAL_AUM_REPORTED / TOTAL_NAV_REPORTED | DECIMAL(20,2) | Reported figures |
| GROSS_LEVERAGE_REPORTED / NET_LEVERAGE_REPORTED | DECIMAL(10,4) | Leverage |
| TOTAL_TRANSACTIONS_REPORTED | INT | Transaction count |
| BREACHES_REPORTED | INT | Number of breaches |
| LATE_REPORTS_COUNT | INT | Late filings |
| AMENDMENT_COUNT | INT | Amendments filed |
| VALIDATION_ERRORS | INT | Filing validation errors |

## Join Patterns

```
FACT_TRANSACTION
  → DIM_ACCOUNT (ACCOUNT_KEY)
  → DIM_FUND (FUND_KEY)
  → DIM_SECURITY (SECURITY_KEY)
  → DIM_COUNTERPARTY (COUNTERPARTY_KEY)
  → DIM_TRADE_MODEL (TRADE_MODEL_KEY)
  → DIM_REGULATORY_JURISDICTION (JURISDICTION_KEY)
  → DIM_GEOGRAPHY (EXECUTION_GEOGRAPHY_KEY)
  → DIM_DATE (TRADE_DATE_KEY, SETTLEMENT_DATE_KEY)

FACT_POSITION
  → DIM_ACCOUNT (ACCOUNT_KEY)
  → DIM_FUND (FUND_KEY)
  → DIM_SECURITY (SECURITY_KEY)
  → DIM_COUNTERPARTY (COUNTERPARTY_KEY)
  → DIM_REGULATORY_JURISDICTION (JURISDICTION_KEY)
  → DIM_GEOGRAPHY (GEOGRAPHY_KEY)
  → DIM_DATE (POSITION_DATE_KEY)

FACT_REGULATORY_REPORT
  → DIM_REGULATORY_JURISDICTION (JURISDICTION_KEY)
  → DIM_FUND (FUND_KEY)
  → DIM_ACCOUNT (ACCOUNT_KEY)
```

## Sample Data Coverage

- **12 institutional accounts** across US, UK, EU, Singapore, Japan, Australia
- **15 securities** spanning equities, bonds, derivatives, FX
- **10 funds** (hedge, UCITS, mutual, AIF, private)
- **8 trade models** (algo, discretionary, passive, illiquid)
- **10 counterparties** (investment banks, CCPs, market makers)
- **12 regulatory jurisdictions** (SEC, FCA, ESMA, MAS, SFC, JFSA, ASIC, CSSF, FINMA, CIMA)
- **12 geographies** (USA, UK, Germany, France, Switzerland, Singapore, Hong Kong, Japan, Australia, Luxembourg, Ireland, Cayman Islands)
- **20 transactions** with full MiFID II fields
- **19 positions** as of 2026-06-30 with risk metrics
- **10 regulatory reports** across multiple filing types
