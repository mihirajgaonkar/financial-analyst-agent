Build a production-oriented **Financial Research Agent** using Python, LangChain, LangGraph, FastAPI, PostgreSQL, and a React frontend.

The system should research public companies using primarily low-cost or free data sources, perform deterministic financial calculations, analyze SEC filings and macroeconomic data, use LLMs for reasoning and synthesis, and return traceable research reports with citations.

The architecture should be designed so it could later support production use, but keep the initial implementation inexpensive and understandable.

## Core design principle

Follow this rule throughout the project:

```text
LLM decides WHAT information or analysis is required.

Tools/APIs retrieve factual information.

Python performs deterministic financial calculations.

LLM interprets and synthesizes the results.
```

Never let the LLM invent financial figures or perform critical financial calculations when deterministic Python can do them.

---

# Target architecture

```text
React Frontend
      ↓
FastAPI
      ↓
Research API / Service Layer
      ↓
LangGraph
      ↓
Supervisor / Research Agent
      │
      ├── Market Data Tools
      │
      ├── SEC Filing Tools
      │
      ├── Macro Tools
      │
      ├── News/Search Tools
      │
      └── Financial Calculation Tools
      ↓
Analysis / Verification
      ↓
Structured Research Report
      ↓
PostgreSQL
```

Future architecture should allow specialized subagents:

```text
                 Supervisor Agent
                       │
       ┌───────────────┼───────────────┐
       ↓               ↓               ↓
   SEC Agent      Market Agent      Macro Agent
       │               │               │
       └───────────────┼───────────────┘
                       ↓
               Analysis / Report Agent
```

Do NOT begin with multiple agents unless needed.

Start with one supervisor agent plus well-designed tools.

---

# Data sources

Prefer low-cost/free sources initially.

Use:

```text
SEC EDGAR
→ filings
→ 10-K
→ 10-Q
→ 8-K
→ XBRL / Company Facts

FRED
→ interest rates
→ CPI
→ unemployment
→ GDP
→ economic indicators

Market data provider
→ stock prices
→ historical prices
→ company metadata
```

Use a low-cost/free market-data provider such as Alpha Vantage or another provider with an accessible developer tier.

Keep market-data integration behind an interface so the provider can later be replaced.

For news/search, make the provider optional.

Possible later integrations:

```text
Tavily
Finnhub
NewsAPI
SerpAPI
```

Do not make news search mandatory for the MVP.

---

# LLM providers

Support configurable providers.

At minimum:

```text
Groq
OpenAI
Ollama
```

Use environment configuration such as:

```env
LLM_PROVIDER=groq

GROQ_API_KEY=
GROQ_MODEL=

OPENAI_API_KEY=
OPENAI_MODEL=

OLLAMA_MODEL=
OLLAMA_BASE_URL=
```

Create a model factory:

```python
def get_llm():
    ...
```

The rest of the application should not care which provider is being used.

Use current LangChain provider integrations.

Check installed package versions and current official documentation before using LangChain/LangGraph APIs.

Avoid deprecated APIs.

---

# Project structure

Create something similar to:

```text
financial-research-agent/

├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── backend/
│   └── src/
│       └── financial_research/
│
│           ├── main.py
│           │
│           ├── config/
│           │   └── settings.py
│           │
│           ├── llm/
│           │   └── model.py
│           │
│           ├── schemas/
│           │   ├── company.py
│           │   ├── financials.py
│           │   ├── filings.py
│           │   └── reports.py
│           │
│           ├── services/
│           │   ├── sec.py
│           │   ├── fred.py
│           │   ├── market_data.py
│           │   └── news.py
│           │
│           ├── calculations/
│           │   ├── growth.py
│           │   ├── profitability.py
│           │   ├── valuation.py
│           │   └── dcf.py
│           │
│           ├── tools/
│           │   ├── sec_tools.py
│           │   ├── market_tools.py
│           │   ├── macro_tools.py
│           │   └── calculation_tools.py
│           │
│           ├── agents/
│           │   └── research_agent.py
│           │
│           ├── graph/
│           │   ├── state.py
│           │   └── research_graph.py
│           │
│           ├── middleware/
│           │   ├── logging.py
│           │   ├── validation.py
│           │   └── errors.py
│           │
│           ├── storage/
│           │   ├── database.py
│           │   └── repositories.py
│           │
│           └── api/
│               ├── routes/
│               │   ├── research.py
│               │   ├── companies.py
│               │   └── health.py
│               └── app.py
│
├── frontend/
│   └── React application
│
└── tests/
```

Adjust the structure if necessary, but keep responsibilities separated.

---

# Dependency management

Use `uv`.

Before modifying the project, verify the environment.

Run:

```powershell
python --version
uv --version
where.exe python
where.exe uv
uv run python --version
```

If any command fails, report the environment problem before attempting implementation.

Do not repeatedly run commands that the execution environment cannot access.

Use:

```powershell
uv sync
uv run pytest -v
```

for testing.

---

# PHASE 1 — Foundation + Financial APIs

Implement only Phase 1 first.

## Project setup

Create:

```text
pyproject.toml
.env.example
.gitignore
README.md
backend package structure
tests directory
```

Add only required dependencies.

Likely backend dependencies include:

```text
langchain
langgraph
langchain-groq
langchain-openai
langchain-ollama
pydantic
pydantic-settings
httpx
fastapi
uvicorn
sqlalchemy
pytest
```

Do not add React dependencies yet.

---

## Pydantic schemas

Create schemas for:

```python
CompanyInfo

PriceData

FinancialStatementMetrics

SECFiling

MacroIndicator

FinancialMetric

ResearchSource

ResearchReport
```

Example concept:

```python
class ResearchSource(BaseModel):
    source_type: str
    title: str
    url: str | None
    retrieved_at: datetime
```

The final research report should distinguish:

```text
reported facts
calculated metrics
LLM interpretation
sources
```

---

## SEC integration

Create a service for SEC EDGAR.

Support:

```python
get_company_cik(ticker)

get_company_submissions(cik)

get_company_facts(cik)

get_recent_filings(cik)

get_latest_10k(cik)

get_latest_10q(cik)
```

Respect SEC requirements for identifying the application through an appropriate User-Agent.

Do not scrape HTML unnecessarily if SEC provides structured JSON.

Normalize SEC responses into Pydantic models.

---

## FRED integration

Create a FRED service.

Support a small initial set of indicators:

```text
Federal Funds Rate
10-Year Treasury Yield
CPI
Unemployment Rate
GDP
```

Expose a generic function such as:

```python
get_fred_series(series_id, ...)
```

and higher-level helpers if useful.

---

## Market data

Create an interface such as:

```python
class MarketDataProvider(Protocol):
    def get_quote(...)
    def get_price_history(...)
    def get_company_overview(...)
```

Implement one provider.

Keep provider-specific code isolated so another provider can later replace it.

---

## Deterministic calculations

Implement normal Python functions for:

```text
YoY revenue growth
CAGR
gross margin
operating margin
net margin
free cash flow
debt-to-equity
ROIC where data permits
P/E
price-to-sales
EV/EBITDA where data permits
```

These functions must NOT use the LLM.

Write tests for calculations.

---

## Phase 1 CLI

Add temporary CLI commands for testing:

```powershell
uv run python -m financial_research.main --company AAPL
```

and:

```powershell
uv run python -m financial_research.main --macro
```

The goal is to confirm that raw financial data can be retrieved before adding agents.

---

## Phase 1 tests

Mock external API calls.

Test:

```text
SEC parsing
ticker → CIK handling
company facts parsing
FRED parsing
market data parsing
calculation formulas
HTTP failures
invalid ticker handling
```

Run:

```powershell
uv run pytest -v
```

Stop after Phase 1.

Explain:

```text
Files created
Files modified
Dependencies added
Tests executed
How to run manually
```

Do NOT proceed automatically.

---

# PHASE 2 — LangChain Tools + Research Agent

Only implement after Phase 1 is validated.

Turn existing capabilities into tools.

Examples:

```python
get_company_profile()

get_stock_price()

get_price_history()

get_latest_10k()

get_latest_10q()

get_company_facts()

get_interest_rates()

get_macro_indicator()

calculate_revenue_growth()

calculate_cagr()

calculate_margins()

calculate_pe()

calculate_ev_ebitda()
```

Important:

Create core Python/service functionality first.

Then wrap it with LangChain tools.

Keep:

```text
Service
= performs functionality

Tool
= exposes functionality to the LLM
```

---

## Research agent

Create one tool-calling research agent.

System rules should include:

```text
Never invent financial data.

Use tools for factual financial information.

Use deterministic calculation tools for arithmetic.

Every important factual conclusion must be traceable to a source.

Always identify the time period associated with financial figures.

Distinguish facts from interpretation.

If information cannot be verified, say so.
```

Example query:

```text
Analyze Microsoft’s revenue growth and operating margins over recent periods.
```

Expected conceptual execution:

```text
Agent
 ↓
get_company_facts()
 ↓
calculate_revenue_growth()
 ↓
calculate_margins()
 ↓
LLM interpretation
```

The LLM should not manually calculate financial ratios.

---

## Structured output

Create a Pydantic result such as:

```python
class ResearchReport(BaseModel):
    ticker: str
    company_name: str

    executive_summary: str

    key_financials: list[FinancialMetric]

    growth_analysis: str

    profitability_analysis: str

    valuation_analysis: str | None

    risks: list[str]

    sources: list[ResearchSource]

    generated_at: datetime
```

Use LangChain structured output where appropriate.

---

# PHASE 3 — LangGraph + Specialized Research Workflow

Create LangGraph orchestration.

Initial graph:

```text
START
 ↓
Understand Question
 ↓
Research Agent
 ↓
Tool requested?
 ├── YES → Tools → Research Agent
 └── NO
 ↓
Verification
 ↓
Report
 ↓
END
```

State should track:

```text
messages
ticker
research_question
sources
calculated_metrics
final_report
```

Use reducers appropriately.

Add bounded loops.

---

## Verification node

This is important for financial research.

Before final output, run a verification step.

Verify:

```text
numbers cited by the LLM exist in tool results
time periods match
sources exist
calculated metrics match deterministic outputs
```

The verifier should flag unsupported claims.

Do not let an LLM silently overwrite deterministic numbers.

---

## Optional specialized subagents

Only introduce subagents after the single-agent implementation works.

Possible agents:

```text
SEC Agent
Market Agent
Macro Agent
News Agent
Valuation Agent
```

Supervisor:

```text
                 Supervisor
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
      SEC         Market        Macro
        ↓            ↓            ↓
        └────────────┼────────────┘
                     ↓
                  Report
```

Use subagents only where specialization clearly improves the architecture.

Do not create agents merely for architectural complexity.

---

# PHASE 4 — Storage + RAG over Financial Filings

Add PostgreSQL.

Store:

```text
companies
research jobs
reports
financial metrics
source metadata
```

Avoid storing API keys.

---

## Filing RAG

Add RAG over SEC filings.

Pipeline:

```text
10-K / 10-Q
     ↓
parse sections
     ↓
section-aware chunks
     ↓
embeddings
     ↓
vector store
     ↓
retrieval
```

Metadata should include:

```text
ticker
CIK
filing type
filing date
fiscal period
section
source URL
```

Support questions such as:

```text
What risks did management identify?

What changed between the last two 10-Q filings?

What did management say about AI spending?
```

Prefer section-aware retrieval instead of arbitrary chunks.

---

# PHASE 5 — FastAPI + React + Production Features

Only implement after backend agent behavior is stable.

## FastAPI

Create endpoints such as:

```text
GET /health

POST /research

GET /research/{job_id}

GET /companies/{ticker}

POST /chat

GET /threads/{thread_id}
```

Example:

```json
POST /research

{
  "ticker": "MSFT",
  "question": "Analyze Microsoft's fundamentals and valuation."
}
```

Return structured JSON.

---

## Streaming

If practical, stream research progress using SSE.

Example events:

```text
research_started

fetching_sec_data

fetching_market_data

calculating_metrics

generating_analysis

verification_complete

finished
```

Do not expose hidden chain-of-thought.

Only expose high-level execution status.

---

## React frontend

Use React with Vite unless Next.js provides a specific benefit.

Build an analyst-style interface.

Suggested layout:

```text
------------------------------------------------
Ticker: MSFT        [Run Research]
------------------------------------------------

Price
Market Cap
Revenue Growth
Operating Margin
P/E

------------------------------------------------

Tabs:

Overview
Fundamentals
Valuation
Filings
Macro
Sources

------------------------------------------------

Research Agent

Question:
[ Analyze Microsoft's valuation ]

Response:
...

Sources:
SEC 10-K
SEC Company Facts
FRED
Market Data
------------------------------------------------
```

Features:

```text
ticker input
research question
loading state
streaming progress
research report
financial metric cards
source citations
filing links
thread/session support
```

---

# Production-oriented features

Add where appropriate:

```text
request IDs
structured logging
timeouts
bounded retries
rate limiting
API caching
input validation
provider error normalization
LLM fallback strategy
database persistence
source timestamps
as-of dates
audit logging
```

Do not implement excessive infrastructure.

---

# Caching

Financial APIs should not be repeatedly called unnecessarily.

Implement caching for:

```text
company metadata
SEC filings
company facts
macro data
historical prices
```

Include timestamps.

Example:

```text
AAPL company facts
retrieved_at = ...
expires_at = ...
```

---

# Financial safety / trust requirements

Every report should distinguish:

```text
Reported Fact
Calculated Metric
Model Interpretation
```

Example:

```text
Reported:
FY2025 revenue = $X

Calculated:
YoY revenue growth = Y%

Interpretation:
Growth accelerated relative to the previous year.
```

Never present model-generated numbers as reported facts.

Include:

```text
Data as of:
Market price as of:
Latest filing:
Sources:
```

Do not position the system as providing guaranteed investment advice.

---

# Observability

Integrate LangSmith optionally.

Trace:

```text
agent execution
model calls
tool calls
latency
errors
token usage
```

Add metadata:

```text
ticker
research job id
thread id
model
provider
```

Never attach secrets.

---

# Human-in-the-loop

Add optional approval before producing a final investment-oriented conclusion.

Conceptually:

```text
Research complete
      ↓
Draft analysis
      ↓
Human review / approval
      ↓
Final report
```

Use LangGraph interrupt/resume rather than implementing fake HITL inside the LLM prompt.

---

# Testing strategy

Use:

```text
unit tests
integration-style tests with mocks
optional live smoke tests
```

Normal pytest must never depend on paid APIs.

Mock:

```text
LLM
market provider
FRED
SEC responses where practical
search/news APIs
```

Test:

```text
agent tool selection
financial calculations
graph routing
verification logic
state/checkpointing
API endpoints
source attribution
provider failures
invalid tickers
```

---

# Important Codex execution instructions

At the beginning of EVERY phase:

1. Inspect the existing repository.
2. Run:

```powershell
python --version
uv --version
uv run python --version
```

3. Run the existing tests:

```powershell
uv run pytest -v
```

4. If Codex cannot execute `python`, `uv`, or the project's environment but my VS Code terminal can, report the environment mismatch once.

Do NOT repeatedly attempt failing environment commands.

Do NOT claim tests passed unless they actually ran.

After implementation:

```powershell
uv sync
uv run pytest -v
```

Inspect all changed files.

Fix obvious failures before stopping.

---

# Coding rules

Use:

```text
type hints
Pydantic
httpx
async only where beneficial
dependency injection where useful
small modules
clear interfaces
application-level exceptions
```

Avoid:

```text
giant files
hard-coded API keys
provider-specific logic scattered everywhere
LLM-generated arithmetic
deprecated LangChain APIs
unnecessary abstractions
premature multi-agent architecture
```

Keep external API calls in service modules.

Keep calculations separate from agents.

Keep agent prompts separate from tools.

Keep API routes separate from business logic.

---

# README

Build the README progressively.

Final README should explain:

```text
Architecture
Setup
Environment variables
Data sources
SEC integration
FRED integration
Market data
Financial calculations
LangChain tools
Research agent
LangGraph
Subagents
Verification
RAG
PostgreSQL
FastAPI
React
LangSmith
Human-in-the-loop
Testing
Example queries
Known limitations
```

Include Mermaid diagrams.

---

# Example final capabilities

The finished system should support queries such as:

```text
Analyze NVDA.

Compare AMD vs NVDA fundamentals.

What changed between Microsoft's latest 10-Q and previous 10-Q?

Analyze Apple's revenue growth and margins.

What are the major risks in Tesla's latest 10-K?

Build a bull/base/bear valuation scenario.

How do current interest rates affect this company's valuation?

Summarize the latest filing and identify material changes.
```

---

# Start now

Begin with **PHASE 1 ONLY**.

Do not implement agents, LangGraph, React, FastAPI endpoints, RAG, or subagents yet.

For Phase 1:

1. verify environment
2. create project structure
3. create configuration
4. create Pydantic schemas
5. implement SEC service
6. implement FRED service
7. implement market-data interface/provider
8. implement deterministic financial calculations
9. add tests
10. update README
11. run tests

Then stop and provide:

```text
Files created
Files modified
Dependencies added
Tests passed/failed
Manual commands
Any environment issues
```

Wait for my instruction before proceeding to Phase 2.
