---
name: risk-fraud-regulatory
description: "Full-lifecycle regulatory compliance skill for the REGULATORY_DW data warehouse. Covers querying, reporting (Basel III, MiFID II, AIFMD, EMIR, UCITS, AML/KYC), data lineage, audit trails, gap analysis, breach detection, and remediation guidance. Use when: user mentions regulatory reports, compliance checks, Basel, MiFID, AIFMD, EMIR, UCITS, AML, KYC, reporting gaps, breaches, Form PF, FR Y-15, sanctions screening, counterparty risk, or references the REGULATORY_DW database. Triggers: regulatory report, compliance, Basel, MiFID, AIFMD, EMIR, UCITS, AML, KYC, reporting gap, breach, Form PF, FR Y-15, sanctions, counterparty risk, REGULATORY_DW, REG_MODEL, risk-fraud-regulatory."
---

# Risk, Fraud & Regulatory Compliance

Full-lifecycle regulatory compliance assistant for the **REGULATORY_DW.REG_MODEL** data warehouse supporting a multi-geographical investment management firm.

## REQUIRED: Read reference before any action

Before writing SQL or answering questions, **read** `reference/schema.md` from this skill directory to understand the full dimensional model (tables, columns, relationships).

## Capabilities

| Capability | Description |
|-----------|-------------|
| **Query & Report** | Generate SQL for any regulatory extract (Basel III, MiFID II, AIFMD, EMIR, UCITS, AML/KYC, Form PF, FR Y-15) |
| **Gap Analysis** | Identify transactions/positions that cannot be reported or breach regulatory limits |
| **Audit Trail** | Trace data lineage across dimensions, validate SCD Type 2 history, verify reporting completeness |
| **Remediation** | Recommend fixes for compliance gaps (missing MIC codes, algo flag mismatches, concentration breaches, KYC overdue) |
| **Risk Scoring** | Compute counterparty exposure, leverage ratios, VaR aggregation, concentration risk |

## Workflow

### Step 1: Classify the Request

Determine which regulatory regime(s) and capability the user needs:

| Regime | Key Tables | Common Asks |
|--------|-----------|-------------|
| **Basel III** | FACT_POSITION, DIM_FUND, DIM_SECURITY | Capital adequacy, RWA, leverage ratio, VaR, FR Y-15 |
| **MiFID II** | FACT_TRANSACTION, DIM_TRADE_MODEL | Best execution, transaction reporting, venue analysis, algo flagging |
| **AIFMD** | DIM_FUND, FACT_REGULATORY_REPORT | Annex IV reporting, leverage, AUM, fund classification |
| **EMIR** | FACT_POSITION, DIM_SECURITY, DIM_COUNTERPARTY | OTC derivatives, central clearing, margin, CSA coverage |
| **UCITS** | DIM_FUND, FACT_POSITION | Concentration limits, leverage caps, eligible assets |
| **AML/KYC** | DIM_ACCOUNT, DIM_GEOGRAPHY | Client risk ratings, KYC review status, sanctions screening |
| **Form PF** | DIM_FUND, FACT_REGULATORY_REPORT | Quarterly filing for large hedge fund advisers |
| **FR Y-15** | FACT_POSITION, DIM_FUND, DIM_COUNTERPARTY | Systemic risk indicators (size, interconnectedness, complexity) |

### Step 2: Build the Query

**Rules:**
1. Always use fully-qualified table names: `REGULATORY_DW.REG_MODEL.<TABLE>`
2. Use parameterized dates where applicable (prefer `AS_OF_DATE` for positions, `TRADE_TIMESTAMP` range for transactions)
3. Join through foreign keys (e.g., `FUND_KEY`, `SECURITY_KEY`, `COUNTERPARTY_KEY`, `JURISDICTION_KEY`, `GEOGRAPHY_KEY`)
4. For SCD Type 2 dimensions, filter `IS_CURRENT = TRUE` unless historical analysis is requested
5. Use `DIM_DATE` for period-based aggregations and regulatory calendar lookups

**⚠️ STOP**: If the request is ambiguous (multiple regimes could apply, or scope is unclear), ask the user to clarify which regime, time period, and fund scope before writing SQL.

### Step 3: Gap Analysis (if applicable)

When checking for compliance gaps, evaluate:

**Transaction-level gaps (MiFID II / EMIR):**
- Missing jurisdiction mapping (`JURISDICTION_KEY IS NULL`)
- Missing venue MIC code (non-OTC trades without `EXECUTION_VENUE_MIC`)
- Algo flag mismatch (model is algorithmic but trade not flagged)
- Short sale model violations
- Unreported trades (`REPORTING_STATUS != 'REPORTED'`)
- Best execution failures
- Missing ISIN on non-derivative securities

**Position-level gaps (Basel / UCITS / EMIR):**
- No jurisdiction mapped
- Concentration breaches (`CONCENTRATION_BREACH = TRUE`)
- OTC derivatives eligible for clearing but not cleared
- Missing counterparty on derivative positions
- UCITS leverage exceeding limits
- Liquidity classification issues
- Missing CSA on bilateral OTC positions

### Step 4: Remediation Guidance

For each gap type, provide:
1. **Root cause** — why the gap exists
2. **Regulatory risk** — which regulation is violated and potential penalty
3. **Fix** — specific data or process change needed
4. **SQL** — query to identify all affected records

### Step 5: Reporting Extracts

When generating regulatory filing extracts:

| Filing | Key Fields | Format |
|--------|-----------|--------|
| **FR Y-15 Schedule A** | Total exposure, AUM, derivative FV, gross leverage, collateral | Line items with MDRM codes |
| **AIFMD Annex IV** | Fund AUM, leverage (gross/net/commitment), liquidity profile | Per-fund quarterly |
| **MiFID II RTS 25** | Transaction ID, venue MIC, timestamp, instrument ISIN, buyer/seller LEI | T+1 daily |
| **EMIR Trade Report** | UTI, counterparty LEI, notional, maturity, clearing status | Per-trade |
| **Form PF** | AUM, NAV, leverage, borrowings, investor concentration | Quarterly for large advisers |

## Stopping Points

- ✋ **After Step 1**: If request is ambiguous, ask which regime and scope
- ✋ **Before executing destructive changes**: If remediation involves UPDATE/DELETE, confirm with user
- ✋ **After gap analysis**: Present summary before detailed remediation

## Key Regulatory Thresholds

| Regulation | Threshold | Check |
|-----------|-----------|-------|
| UCITS | Single position ≤ 10% of NAV | `WEIGHT_IN_FUND_PCT > 10` |
| UCITS | Total derivative exposure ≤ 100% of NAV | Sum derivative MV vs fund AUM |
| MiFID II | Transaction reported within T+1 | `REPORTING_TIMESTAMP - EXECUTION_TIMESTAMP > 86400s` |
| Basel III | Leverage ratio ≥ 3% | Fund leverage ratio check |
| EMIR | Mandatory clearing for eligible OTC | `IS_OTC AND CENTRAL_CLEARING_ELIGIBLE AND NOT centrally_cleared` |
| AML/KYC | Review within 12 months | `DATEDIFF('day', KYC_LAST_REVIEWED, CURRENT_DATE()) > 365` |

## Output

- SQL queries (validated, ready to execute)
- Summary tables with compliance status
- Gap counts with severity classification
- Remediation recommendations with priority
- Filing extracts formatted per regulatory specification
