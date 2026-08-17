# Feature Enhancement: Insider & Congressional Trading Intelligence

## Objective

Add an **Ownership & Trading Intelligence** capability to the Financial Research Agent so that a user can query any public stock ticker and retrieve:

1. Corporate insider transactions from SEC Forms 3, 4, and 5.
2. Congressional trading activity from official Congressional disclosures.
3. Deterministic summaries and signals without sending full raw filings or full API payloads to the LLM.
4. A unified normalized data model stored in PostgreSQL.
5. Optional raw-file archival for provenance/debugging, while PostgreSQL remains the primary query layer.

The design should optimize for:

- Low LLM token usage.
- Fast ticker/date-range queries.
- Reproducible calculations.
- Source traceability.
- Incremental ingestion.
- Avoiding repeated API calls.
- Avoiding repeated transmission of large documents to the LLM.

---

# 1. Key Architectural Decision

## Recommendation

Use a **hybrid storage model**:

- **PostgreSQL = primary normalized/queryable store**
- **File-based storage = optional raw archive/cache**
- **LLM = receives only compact computed summaries and selected transactions**

Do **not** use a pure file-based architecture for this feature.

### Why PostgreSQL should be primary

The data is naturally relational and highly filterable:

- ticker
- transaction date
- filing date
- insider/politician
- transaction type
- transaction code
- issuer
- owner relationship
- chamber
- amount range
- direct/indirect ownership
- Form 4 accession number

The application will repeatedly need questions such as:

- Show all insider purchases of NVDA during the last 90 days.
- Calculate insider buy/sell ratio for MSFT.
- Find politicians purchasing AAPL during the last year.
- Count unique directors buying a stock.
- Identify cluster buying.
- Compare filing delay across congressional trades.
- Find the largest insider purchases over the past six months.

These are much easier and cheaper to answer with indexed SQL than by reading JSON/XML/CSV files into application memory for every request.

---

# 2. Source Strategy

## Corporate insiders

### Primary source
SEC EDGAR / SEC Insider Transactions Data Sets.

The SEC publishes structured ownership data from Forms:

- Form 3
- Form 3/A
- Form 4
- Form 4/A
- Form 5
- Form 5/A

The SEC also publishes quarterly flattened Insider Transactions Data Sets extracted from Ownership XML submissions.

Recommended usage:

### Historical backfill
Use SEC quarterly Insider Transactions Data Sets.

### Near-real-time updates
Use SEC EDGAR submissions / ownership XML filings.

This provides both:

- efficient historical loading
- recent Form 4 monitoring

---

## Congressional trading

### Primary practical source
official Congressional disclosures Congress Trades API.

Use Congress disclosures for normalized congressional disclosure data because congressional disclosures do not use the same standardized Form 4 ownership schema as SEC corporate insiders.

Congress disclosures can serve as the normalized source for:

- House trades
- Senate trades
- transaction date
- report/disclosure date
- ticker
- transaction type
- reported amount range
- politician identity

Where available, retain a link/reference to the original government disclosure for provenance.

---


## Cost-optimized congressional data source

Use the official congressional financial-disclosure systems as the default source:

- U.S. House Office of the Clerk Financial Disclosure portal
- U.S. Senate electronic Financial Disclosure (eFD) system

This keeps the core congressional-trading pipeline free.

Recommended provider priority:

```text
1. Official House Clerk + Senate eFD -> primary, authoritative, $0
2. Finnhub Congressional Trading API -> optional convenience/fallback
3. EODHD Congressional Trades API    -> optional paid fallback
4. Capitol Trades                    -> manual verification/reference only
```

### Provider architecture

```python
class CongressTradeProvider(Protocol):
    def fetch_trades(
        self,
        ticker: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CongressTradeRaw]:
        ...
```

Possible implementations:

```text
OfficialCongressProvider
FinnhubCongressProvider
EODHDCongressProvider
```

The application must not depend on a paid provider for startup or core functionality.

### Finnhub

Finnhub publicly documents a Congressional Trading API. Implement it only as an optional adapter because access limits and plan entitlements can change.

### EODHD

EODHD currently documents a normalized Congressional Trades API covering House and Senate records. Its response includes member, asset, transaction, disclosure timing, amount range, and original filing URL fields. Treat it as an optional fallback and verify plan entitlement before use.

### Capitol Trades

Capitol Trades is useful as a free research and manual verification interface. Do not make automated scraping of Capitol Trades part of the default implementation unless its terms explicitly permit it.

### Official-source ingestion responsibilities

The official provider should:

1. discover new PTR filings
2. avoid refetching already-ingested filings
3. extract transaction rows
4. normalize dates and transaction types
5. parse reported amount ranges
6. map asset descriptions to tickers where possible
7. preserve original filing URL and filing identifier
8. upsert normalized records into PostgreSQL
9. retain raw source files for reprocessing/debugging
10. never send raw filing history directly to the LLM


# 3. Analysis of SEC Output Format

## SEC quarterly Insider Transactions Data Set

The SEC publishes the data as quarterly ZIP archives containing up to eight tab-delimited UTF-8 files.

The documented logical tables are:

1. `SUBMISSION`
2. `REPORTINGOWNER`
3. `NONDERIV_TRANS`
4. `NONDERIV_HOLDING`
5. `DERIV_TRANS`
6. `DERIV_HOLDING`
7. `FOOTNOTES`
8. `OWNER_SIGNATURE`

These files are relational and are joined mainly by `ACCESSION_NUMBER`.

This is a strong indication that the data belongs in a relational database rather than a document database or a folder of JSON files.

---

## SEC SUBMISSION

Important fields include:

- `ACCESSION_NUMBER`
- `FILING_DATE`
- `PERIOD_OF_REPORT`
- `DATE_OF_ORIG_SUB`
- `DOCUMENT_TYPE`
- `ISSUERCIK`
- `ISSUERNAME`
- `ISSUERTRADINGSYMBOL`
- `REMARKS`

`ACCESSION_NUMBER` is the primary filing identifier.

---

## SEC REPORTINGOWNER

Important fields include:

- `ACCESSION_NUMBER`
- `RPTOWNERCIK`
- `RPTOWNERNAME`
- `RPTOWNER_RELATIONSHIP`
- `RPTOWNER_TITLE`
- owner address fields

The owner relationship can represent:

- OFFICER
- DIRECTOR
- TENPERCENTOWNER
- OTHER

One filing can contain multiple reporting owners, so this should remain a separate normalized entity.

---

## SEC NONDERIV_TRANS

This is one of the most important tables for open-market insider trading analysis.

Important fields include:

- `ACCESSION_NUMBER`
- `NONDERIV_TRANS_SK`
- `SECURITY_TITLE`
- `TRANS_DATE`
- `DEEMED_EXECUTION_DATE`
- `TRANS_FORM_TYPE`
- `TRANS_CODE`
- `EQUITY_SWAP_INVOLVED`
- `TRANS_TIMELINESS`
- `TRANS_SHARES`
- `TRANS_PRICEPERSHARE`
- `TRANS_ACQUIRED_DISP_CD`
- `SHRS_OWND_FOLWNG_TRANS`
- `DIRECT_INDIRECT_OWNERSHIP`
- `NATURE_OF_OWNERSHIP`

Important Form 4 transaction codes for analysis include:

- `P` = open-market/private purchase
- `S` = open-market/private sale
- `A` = grant/award
- `M` = option exercise/conversion
- `F` = payment of exercise price or tax liability using securities
- `G` = gift

The application should **not** treat all transaction codes as equivalent trading signals.

By default, investment-signal calculations should focus most heavily on:

- `P`
- `S`

Other codes should remain available but be categorized separately.

---

## SEC DERIV_TRANS

Derivative transactions should be stored separately from ordinary common-stock transactions.

Examples include:

- options
- warrants
- convertible instruments
- derivative exercises

Do not merge these blindly into ordinary insider purchase/sale calculations.

---

## SEC FOOTNOTES

Footnotes can contain materially important context such as:

- weighted-average execution prices
- execution-price ranges
- planned trading arrangements
- indirect ownership explanations
- transaction-specific qualifications

Store footnotes, but do not send them all to the LLM.

Retrieve them only when:

- the user asks for transaction detail
- the transaction appears unusual
- the verification layer requires additional context

---

# 4. Congress disclosures Congress Trades Output

Congress disclosures's current Congress Trades product returns normalized congressional-trading data rather than raw congressional disclosure documents.

Publicly exposed examples/documentation indicate fields such as:

- `Representative`
- `ReportDate`
- `TransactionDate`
- `Ticker`
- `Transaction`
- `Range`
- chamber/House information depending on endpoint/version

Because Congress disclosures's API may evolve, implementation must **not hard-code the upstream JSON directly into domain objects**.

Create a provider-specific Pydantic response model and map it into an internal canonical model.

Example provider model:

```python
class Congress disclosuresCongressTradeRaw(BaseModel):
    representative: str | None = None
    report_date: date | None = None
    transaction_date: date | None = None
    ticker: str | None = None
    transaction: str | None = None
    range: str | None = None
    chamber: str | None = None
```

The actual aliases should match the live API response observed during implementation.

Example:

```python
representative: str | None = Field(
    default=None,
    validation_alias=AliasChoices("Representative", "representative")
)
```

This protects the application if upstream naming changes between API versions.

---

# 5. Canonical Internal Data Model

Do not make the rest of the application depend directly on SEC or Congress disclosures schemas.

Normalize both sources into application-owned schemas.

---

## `security`

```text
id
ticker
issuer_name
issuer_cik
exchange
created_at
updated_at
```

Unique indexes:

```text
ticker
issuer_cik
```

---

## `person`

Represents both insiders and politicians.

```text
id
person_type
name
source_person_id
created_at
updated_at
```

Possible `person_type`:

```text
corporate_insider
politician
```

Avoid trying to deduplicate SEC insiders and politicians automatically based only on name.

---

## `insider_filing`

```text
id
accession_number
issuer_id
document_type
filing_date
period_of_report
original_submission_date
sec_url
remarks
raw_source_path
ingested_at
```

Constraints:

```text
UNIQUE(accession_number)
```

---

## `insider_reporting_owner`

```text
id
filing_id
person_id
reporting_owner_cik
relationship
title
is_director
is_officer
is_ten_percent_owner
is_other
```

---

## `insider_transaction`

```text
id
filing_id
issuer_id
person_id
source_transaction_id
security_title
transaction_date
deemed_execution_date
transaction_code
acquired_disposed
shares
price_per_share
transaction_value
shares_owned_after
direct_indirect_ownership
nature_of_ownership
is_derivative
equity_swap_involved
transaction_timeliness
created_at
```

Recommended indexes:

```text
(ticker/issuer_id, transaction_date)
(person_id, transaction_date)
transaction_code
filing_id
```

A generated/calculated `transaction_value` can be:

```text
shares * price_per_share
```

when both values exist.

Never overwrite the underlying filed values.

---

## `congress_trade`

```text
id
provider
provider_trade_id
person_id
ticker
issuer_id
chamber
party
state
owner
transaction_date
report_date
transaction_type
amount_range
amount_min
amount_max
amount_midpoint
source_url
raw_source_path
ingested_at
```

Recommended indexes:

```text
(ticker, transaction_date)
(person_id, transaction_date)
(chamber, transaction_date)
transaction_type
report_date
```

If Congress disclosures does not provide a durable transaction ID, derive a deterministic hash from stable fields.

Example:

```text
SHA256(
    normalized_person_name
    + ticker
    + transaction_date
    + transaction_type
    + amount_range
    + report_date
)
```

Use this only for ingestion deduplication.

---

# 6. Congressional Amount Ranges

Congressional disclosures commonly report ranges rather than exact values.

Example:

```text
$1,001 - $15,000
$15,001 - $50,000
$50,001 - $100,000
```

Store:

```text
amount_range
amount_min
amount_max
amount_midpoint
```

Example:

```text
amount_range    = "$15,001 - $50,000"
amount_min      = 15001
amount_max      = 50000
amount_midpoint = 32500.5
```

Do not represent midpoint as the actual transaction value.

All UI and LLM output must distinguish:

```text
reported range
```

from:

```text
estimated midpoint
```

---

# 7. Raw File Storage

PostgreSQL should be the primary operational store, but retaining raw provider data is useful.

Recommended directory:

```text
data/
    raw/
        sec/
            ownership/
                2026/
                    08/
        quiver/
            congress/
                2026/
                    08/
```

Possible formats:

```text
SEC individual filings   -> XML
SEC bulk archives        -> original ZIP / TSV
Congress disclosures responses         -> JSON
```

Raw files are useful for:

- debugging parsers
- auditability
- reprocessing
- verifying source changes
- avoiding unnecessary API refetches

Raw files should **not** be the query interface used by LangChain tools.

---

# 8. Why Pure File Storage Is Not Recommended

A file-only solution might initially look simpler:

```text
NVDA.json
AAPL.json
MSFT.json
```

but becomes problematic quickly.

Example user query:

```text
Which stocks had at least three insiders buying during
the last 30 days and were also bought by members of Congress?
```

With files, the application would need to:

1. enumerate files
2. deserialize many files
3. normalize records
4. filter dates
5. aggregate transactions
6. join insider and politician activity
7. possibly pass large results downstream

PostgreSQL can answer the same question directly.

Example conceptual SQL:

```sql
SELECT
    s.ticker,
    COUNT(DISTINCT it.person_id) AS insider_buyers,
    COUNT(DISTINCT ct.person_id) AS politician_buyers
FROM securities s
JOIN insider_transactions it
    ON it.issuer_id = s.id
JOIN congress_trades ct
    ON ct.ticker = s.ticker
WHERE it.transaction_code = 'P'
  AND ct.transaction_type = 'Purchase'
  AND it.transaction_date >= CURRENT_DATE - INTERVAL '30 days'
  AND ct.transaction_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY s.ticker
HAVING COUNT(DISTINCT it.person_id) >= 3;
```

This is the main reason PostgreSQL is the recommended primary storage layer.

---

# 9. LLM Cost Optimization

The LLM should **never receive the complete SEC filing history or complete congressional-trade history for a ticker by default**.

The system should use deterministic retrieval and aggregation before invoking the model.

Recommended pipeline:

```text
User
  |
  v
LangGraph
  |
  v
Tool / Service Layer
  |
  v
PostgreSQL
  |
  v
Deterministic Calculations
  |
  v
Compact Typed Result
  |
  v
LLM
```

NOT:

```text
User
  |
  v
Download SEC files
  |
  v
Load entire files
  |
  v
Pass entire dataset to LLM
  |
  v
Ask model to calculate
```

---

# 10. Tool Design

Add deterministic LangChain tools.

---

## `get_insider_transactions`

Inputs:

```python
ticker: str
start_date: date | None
end_date: date | None
transaction_codes: list[str] | None
limit: int = 50
```

Returns only relevant normalized rows.

Example:

```json
{
  "ticker": "NVDA",
  "period": {
    "start": "2026-05-01",
    "end": "2026-08-01"
  },
  "transactions": [
    {
      "name": "Example Insider",
      "role": "Director",
      "date": "2026-07-20",
      "code": "P",
      "shares": 10000,
      "price": 150.25,
      "value": 1502500
    }
  ]
}
```

---

## `get_congressional_transactions`

Inputs:

```python
ticker: str
start_date: date | None
end_date: date | None
chamber: str | None
transaction_type: str | None
limit: int = 50
```

Returns compact normalized rows.

---

## `get_ownership_activity`

This should be the primary tool used by the research agent.

Inputs:

```python
ticker: str
lookback_days: int = 90
```

Return a precomputed summary such as:

```json
{
  "ticker": "NVDA",
  "lookback_days": 90,

  "insiders": {
    "purchase_count": 4,
    "sale_count": 19,
    "unique_buyers": 3,
    "unique_sellers": 8,
    "purchase_value": 6200000,
    "sale_value": 41000000,
    "net_open_market_value": -34800000,
    "cluster_buying": true
  },

  "congress": {
    "purchase_count": 7,
    "sale_count": 2,
    "unique_buyers": 5,
    "unique_sellers": 2,
    "reported_purchase_min": 86007,
    "reported_purchase_max": 310000
  },

  "recent_notable_transactions": [
    ...
  ]
}
```

This compact object is what the LLM should normally see.

---

# 11. Deterministic Metrics

Calculations should occur in Python/SQL, not in the LLM.

---

## Insider Purchase Count

Count:

```text
transaction_code = P
```

---

## Insider Sale Count

Count:

```text
transaction_code = S
```

---

## Gross Insider Purchase Value

```text
SUM(shares * price)
WHERE transaction_code = 'P'
```

---

## Gross Insider Sale Value

```text
SUM(shares * price)
WHERE transaction_code = 'S'
```

---

## Net Open-Market Insider Activity

```text
purchase_value - sale_value
```

This metric should exclude grants, gifts, tax withholding, and option exercises unless specifically requested.

---

## Insider Buy/Sell Ratio

Possible implementation:

```text
purchase_value / sale_value
```

Handle zero-sale cases explicitly.

Also calculate a transaction-count ratio separately.

---

## Unique Insider Buyers

```text
COUNT(DISTINCT person_id)
WHERE transaction_code = 'P'
```

---

## Cluster Buying

Initial deterministic definition:

```text
cluster_buying = TRUE
when >= 3 distinct corporate insiders
record code P transactions
within a rolling 30-day period
```

Make thresholds configurable.

Suggested settings:

```text
INSIDER_CLUSTER_MIN_BUYERS=3
INSIDER_CLUSTER_WINDOW_DAYS=30
```

---

## Congressional Disclosure Delay

```text
report_date - transaction_date
```

Return:

```text
days_to_disclose
```

Do not use the LLM to calculate date differences.

---

# 12. Signal Layer

Do not create a black-box LLM investment score.

Use transparent deterministic indicators.

Possible signals:

```text
insider_purchase_strength
insider_sale_strength
insider_buy_sell_ratio
unique_insider_buyers
cluster_buying
congress_purchase_count
congress_sale_count
congress_buy_sell_ratio
congress_unique_buyers
median_disclosure_delay
```

Optional higher-level composite score can be introduced later, but every component must remain inspectable.

---

# 13. Example Summary Sent to the LLM

Instead of supplying 500 transactions:

```json
{
  "ticker": "NVDA",
  "period_days": 90,
  "insider_summary": {
    "open_market_buys": 4,
    "open_market_sells": 19,
    "unique_buyers": 3,
    "purchase_value": 6200000,
    "sale_value": 41000000,
    "cluster_buying": true
  },
  "congress_summary": {
    "purchases": 7,
    "sales": 2,
    "unique_purchasers": 5,
    "purchase_amount_min": 86007,
    "purchase_amount_max": 310000
  },
  "notable_transactions": [
    {
      "category": "insider",
      "person": "Example Director",
      "transaction": "Purchase",
      "date": "2026-07-20",
      "value": 1502500
    },
    {
      "category": "congress",
      "person": "Example Representative",
      "transaction": "Purchase",
      "date": "2026-07-25",
      "range": "$15,001-$50,000"
    }
  ]
}
```

This drastically reduces context size.

---

# 14. Retrieval Strategy

Implement a query-first approach.

Example user question:

```text
Has there been meaningful insider activity in NVDA?
```

Agent flow:

```text
1. Normalize ticker -> NVDA
2. Call get_ownership_activity(NVDA, 90)
3. PostgreSQL performs filtering/aggregation
4. Service returns compact JSON
5. LLM interprets the compact data
6. User receives explanation + source references
```

Only if the user asks:

```text
Show me the exact filing behind the director's transaction.
```

should the application retrieve:

```text
specific SEC filing
specific filing footnote
specific Congress disclosures/source disclosure
```

---

# 15. API-Level Caching

Provider calls should not run every time a user opens a ticker.

Use source-specific ingestion schedules.

---

## SEC

### Historical
Backfill quarterly datasets once.

### Incremental
Poll recent EDGAR Form 4 submissions periodically.

Suggested:

```text
every 15-60 minutes
```

subject to SEC access policies and application requirements.

Always use an appropriate SEC User-Agent.

---

## Congress disclosures

Poll according to:

- subscription limits
- provider rate limits
- acceptable freshness

Possible starting point:

```text
every 1-6 hours
```

for congressional transactions.

Store fetched records locally in PostgreSQL.

The research agent should query PostgreSQL rather than Congress disclosures directly for ordinary user requests.

---

# 16. Sync Metadata

Create a provider synchronization table.

## `data_source_sync`

```text
id
provider
dataset
last_success_at
last_attempt_at
last_cursor
last_record_date
status
records_inserted
records_updated
error_message
```

Examples:

```text
sec / form4_recent
sec / insider_bulk_2026_q2
quiver / congress_trades
```

This allows incremental ingestion instead of repeatedly downloading full datasets.

---

# 17. Optional Raw Payload Table

Do not put every large SEC XML document directly into normal transaction tables.

If database-level raw payload retention is desired:

```text
raw_provider_payload
--------------------
id
provider
resource_type
source_id
retrieved_at
content_hash
storage_path
```

Store the actual large payload on disk/object storage and the path/hash in PostgreSQL.

For a local portfolio project:

```text
filesystem + PostgreSQL metadata
```

is sufficient.

At larger scale:

```text
S3-compatible object storage + PostgreSQL metadata
```

would be preferable.

---

# 18. Proposed Backend Structure

Extend the current backend approximately as follows:

```text
backend/src/financial_research/

    ownership/
        __init__.py

        schemas/
            insider.py
            congress.py
            ownership_summary.py

        providers/
            sec_ownership.py
            quiver.py

        repositories/
            insider_repository.py
            congress_repository.py
            sync_repository.py

        services/
            insider_ingestion.py
            congress_ingestion.py
            ownership_analysis.py
            ownership_sync.py

        calculations/
            insider_metrics.py
            congress_metrics.py
            ownership_signals.py

        tools/
            insider_tools.py
            congress_tools.py
            ownership_tools.py
```

Use existing project conventions where appropriate instead of forcing this exact directory layout.

---

# 19. Suggested SQLAlchemy Models

Add models approximately corresponding to:

```text
Security
Person
InsiderFiling
InsiderReportingOwner
InsiderTransaction
InsiderFootnote
CongressTrade
DataSourceSync
RawProviderPayload
```

If equivalent company/security/person models already exist, reuse them instead of creating duplicates.

---

# 20. Pydantic Schemas

Create separate schemas for:

### Provider schemas

```text
SECSubmissionRaw
SECReportingOwnerRaw
SECNonDerivativeTransactionRaw
SECDerivativeTransactionRaw

Congress disclosuresCongressTradeRaw
```

### Canonical application schemas

```text
InsiderTransaction
CongressionalTransaction
InsiderActivitySummary
CongressActivitySummary
OwnershipActivitySummary
```

Provider schemas must never leak into the agent-facing interface.

---

# 21. API Endpoints

Suggested FastAPI routes:

```text
GET /companies/{ticker}/insiders
GET /companies/{ticker}/congress
GET /companies/{ticker}/ownership-activity
```

Example:

```text
GET /companies/NVDA/ownership-activity?lookback_days=90
```

Possible response:

```json
{
  "ticker": "NVDA",
  "lookback_days": 90,
  "insider_activity": {...},
  "congress_activity": {...},
  "notable_transactions": [...],
  "data_freshness": {
    "sec_last_updated": "...",
    "quiver_last_updated": "..."
  }
}
```

---

# 22. Frontend Enhancement

Add a new tab:

```text
Ownership & Trading
```

Suggested sections:

```text
Ownership & Trading

Corporate Insider Activity
------------------------------------------------
Open-market purchases
Open-market sales
Purchase value
Sale value
Unique buyers
Cluster buying

Recent Insider Transactions
------------------------------------------------
Date | Insider | Role | Type | Shares | Price | Value


Congressional Activity
------------------------------------------------
Purchases
Sales
Unique buyers
Reported purchase range

Recent Congressional Transactions
------------------------------------------------
Date | Politician | Chamber | Type | Reported Range | Filed


Signals
------------------------------------------------
Cluster Buying
Insider Buy/Sell Ratio
Congress Buy/Sell Ratio
Disclosure Delay
```

---

# 23. Source Traceability

Every displayed transaction must be traceable.

SEC transaction:

```text
source = SEC
accession_number
filing_url
```

Congress transaction:

```text
source = Congress disclosures
source_url / provider identifier
original disclosure URL when available
```

The final research report should cite the underlying source rather than asking the model to invent attribution.

---

# 24. Deduplication

SEC:

Primary filing identifier:

```text
ACCESSION_NUMBER
```

Transaction uniqueness:

```text
ACCESSION_NUMBER + NONDERIV_TRANS_SK
```

or:

```text
ACCESSION_NUMBER + DERIV_TRANS_SK
```

Congress:

Prefer provider trade ID if supplied.

Otherwise derive deterministic ingestion key from:

```text
politician
ticker
transaction_date
transaction_type
amount_range
report_date
owner
```

Do not use random UUIDs alone for source-level deduplication.

---

# 25. Amendments

SEC includes:

```text
4/A
3/A
5/A
```

Do not silently treat amendments as independent economic transactions.

Store:

```text
document_type
original_submission_date
amendment relationship where resolvable
```

The analysis layer should prevent double counting the original transaction and an amended version.

Implement amendment handling as part of normalization before computing signals.

---

# 26. Data Freshness

Include freshness metadata with every summary.

Example:

```json
{
  "data_freshness": {
    "sec": "2026-08-16T13:45:00Z",
    "quiver": "2026-08-16T12:00:00Z"
  }
}
```

This is especially important for trading-related data.

---

# 27. LLM Guardrails

The LLM should be responsible for:

- narrative explanation
- highlighting unusual activity
- comparing insider and politician behavior
- explaining limitations

The LLM should not be responsible for:

- totaling transaction values
- calculating ratios
- filtering transaction codes
- deduplicating amendments
- parsing SEC XML
- parsing congressional ranges
- calculating date differences
- deciding whether a transaction qualifies as an open-market purchase

These should be deterministic code.

---

# 28. Recommended Implementation Phases

## Phase 1 — Database Models

Implement:

```text
Security
Person
InsiderFiling
InsiderReportingOwner
InsiderTransaction
CongressTrade
DataSourceSync
```

Add migrations.

Add indexes.

Add repository tests.

---

## Phase 2 — SEC Historical Loader

Download and parse SEC quarterly Insider Transactions Data Sets.

Initially support:

```text
SUBMISSION
REPORTINGOWNER
NONDERIV_TRANS
```

Then add:

```text
DERIV_TRANS
FOOTNOTES
```

Implement idempotent upserts.

---

## Phase 3 — SEC Recent Form 4 Loader

Add incremental recent Form 4 ingestion from EDGAR.

Parse Ownership XML.

Normalize into the same canonical database tables used by bulk data.

---

## Phase 4 — Congress disclosures Congress Provider

Add:

```text
FINNHUB_API_KEY
FINNHUB_BASE_URL
```

Implement Congress disclosures client.

Normalize response.

Persist transactions.

Implement retry/backoff for:

```text
429
5xx
network timeout
```

---

## Phase 5 — Deterministic Analytics

Implement:

```text
insider purchase count
insider sale count
purchase value
sale value
net value
unique buyers
unique sellers
cluster buying

congress purchase count
congress sale count
unique purchasers
reported min/max value
disclosure delay
```

Unit test all calculations.

---

## Phase 6 — LangChain Tools

Implement:

```text
get_insider_transactions
get_congressional_transactions
get_ownership_activity
```

Prefer `get_ownership_activity` for normal agent workflows.

---

## Phase 7 — FastAPI

Expose:

```text
/companies/{ticker}/insiders
/companies/{ticker}/congress
/companies/{ticker}/ownership-activity
```

---

## Phase 8 — Frontend

Add:

```text
Ownership & Trading
```

Render summary cards and transaction tables.

Do not rely on an LLM-generated Markdown blob for this tab.

The frontend should receive structured JSON and render components directly.

---

## Phase 9 — Agent Integration

Allow the research agent to call:

```text
get_ownership_activity
```

when queries involve:

```text
insiders
Form 4
executive buying
executive selling
Congress trading
politicians
ownership activity
```

The final synthesis node should receive only the compact tool response.

---

# 29. Tests

Add tests covering:

### SEC parsing

- valid Form 4
- Form 4/A
- multiple reporting owners
- missing price
- derivative transaction
- direct ownership
- indirect ownership
- footnotes

### Congress disclosures

- valid response
- missing ticker
- missing amount range
- purchase
- sale
- API rate limit
- provider timeout

### Deduplication

- duplicate Form 4
- amended Form 4
- duplicate congressional trade

### Calculations

- insider buy/sell value
- zero sales
- zero buys
- cluster buying
- congressional range parsing
- disclosure delay

### API

- ticker with activity
- ticker with no activity
- invalid ticker
- stale provider data

---

# 30. Environment Variables

Add:

```text
FINNHUB_API_KEY=
FINNHUB_BASE_URL=
SEC_USER_AGENT=

OWNERSHIP_SEC_SYNC_ENABLED=true
OWNERSHIP_CONGRESS_SYNC_ENABLED=true

INSIDER_CLUSTER_MIN_BUYERS=3
INSIDER_CLUSTER_WINDOW_DAYS=30
```

Avoid exposing API keys to the frontend.

---

# 31. Recommended Storage Architecture

Final recommended architecture:

```text
                    DATA SOURCES

         SEC EDGAR                 Congress disclosures
        Forms 3/4/5            Congress Trades
             |                       |
             v                       v
      SEC Provider              Congress disclosures Provider
             |                       |
             +-----------+-----------+
                         |
                         v
                  Normalization
                         |
                         v
                  PostgreSQL
            canonical transactions
                         |
             +-----------+-----------+
             |                       |
             v                       v
       SQL Aggregation        Raw Archive
       Python Metrics         XML / JSON / ZIP
             |
             v
       Compact Tool Result
             |
             v
         LangGraph Agent
             |
             v
             LLM
```

---

# 32. Storage Recommendation Summary

## PostgreSQL

Use PostgreSQL for:

- normalized filings
- normalized transactions
- people
- issuers
- transaction indexes
- aggregation
- filtering
- deduplication
- sync metadata
- application queries

### Rating for this project

```text
★★★★★ Recommended
```

---

## File-based storage

Use files only for:

- original SEC XML
- SEC bulk ZIP archives
- original Congress disclosures JSON payloads
- debug/reprocessing snapshots

### Rating as primary database

```text
★★☆☆☆ Not recommended
```

### Rating as archive/cache

```text
★★★★★ Recommended
```

---

## Vector database

Do not use embeddings/vector search for the transaction records themselves.

These queries are structured:

```text
ticker = NVDA
date >= ...
transaction_code = P
```

A relational database is substantially more appropriate.

A vector store may optionally be used later for:

- long SEC filing footnotes
- filing remarks
- qualitative disclosure text

but it is unnecessary for core insider/congress trading retrieval.

---

# 33. Critical Cost Principle

The core principle for this enhancement is:

```text
DATA IS STORED ONCE
       ↓
FILTERED WITH SQL
       ↓
CALCULATED WITH CODE
       ↓
SUMMARIZED STRUCTURALLY
       ↓
ONLY THEN SENT TO THE LLM
```

The LLM should see tens of fields, not thousands of source rows.

This keeps token consumption predictable and allows the same locally stored transaction data to support repeated analysis without repeatedly downloading or transmitting source documents.

---

# 34. Codex Implementation Instruction

Implement this feature incrementally and preserve the existing application architecture.

Before writing code:

1. Inspect existing SQLAlchemy company/security models and reuse them where possible.
2. Inspect existing repository conventions.
3. Inspect existing LangChain tool patterns.
4. Inspect the current LangGraph state and final synthesis behavior.
5. Inspect existing FastAPI route structure.
6. Inspect frontend tab/component structure.
7. Produce an implementation plan before modifying files.

Important requirements:

- PostgreSQL is the primary normalized store.
- Raw SEC/Congress disclosures files are optional archival data.
- Never send complete historical source data to the LLM.
- Perform calculations deterministically.
- Tool outputs must be compact and typed.
- Handle SEC amendments so transactions are not double-counted.
- Preserve source URLs/accession numbers.
- Add provider retry/backoff.
- Add tests before considering the feature complete.
- Prefer structured frontend rendering over raw Markdown for the new tab.
- Do not break existing research workflows or tests.

---

# 35. Reference Sources

SEC Insider Transactions Data Sets:
https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets

SEC Insider Transactions Data Set documentation:
https://www.sec.gov/files/insider_transactions_readme.pdf

SEC EDGAR APIs:
https://www.sec.gov/search-filings/edgar-application-programming-interfaces

Congress disclosures Congress Trades:
https://disclosures-clerk.house.gov/

U.S. Senate Financial Disclosure:
https://www.ethics.senate.gov/public/index.cfm/financialdisclosure

Finnhub Congressional Trading API:
https://finnhub.io/docs/api/congressional-trading

EODHD Congressional Trades API:
https://eodhd.com/financial-apis/congressional-trades-api

Congress disclosures Insider Trades:
https://api.quiverquant.com/datasets/insider-trades

House/Senate disclosure ingestion:
https://api.quiverquant.com/docs/

---

# Final Recommendation

For this Financial Research Agent:

```text
SEC                  -> authoritative corporate-insider source
Congress disclosures               -> normalized congressional-trading source
PostgreSQL           -> primary analytical/query store
Filesystem           -> raw payload/archive/cache
Python/SQL           -> calculations and summarization
LangChain/LangGraph  -> orchestration
LLM                  -> final explanation only
```

This architecture provides the lowest long-term token usage, avoids repeated source downloads, supports fast historical analysis, and gives the agent access to compact structured facts rather than large raw documents.


# Cost Recommendation

Default recurring provider cost for congressional trades should be **$0**:

```text
SEC EDGAR                 -> corporate insider source, free
House Clerk disclosures   -> House PTR source, free
Senate eFD                -> Senate PTR source, free
PostgreSQL                -> primary normalized store
Finnhub                   -> optional fallback; verify current plan entitlement
EODHD                     -> optional paid fallback
Capitol Trades            -> manual verification/reference
```

The agent should query PostgreSQL, not the upstream provider, during normal conversations. This preserves the low-token architecture: ingest once, normalize once, calculate with SQL/Python, and send only compact summaries to the LLM.
