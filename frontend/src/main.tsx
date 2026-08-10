import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, BarChart3, Building2, FileText, Play, RefreshCcw, Search, ShieldCheck } from "lucide-react";
import "./styles.css";

type Metric = {
  name: string;
  value: number;
  unit?: string | null;
  period?: string | null;
  source?: string | null;
};

type Source = {
  source_type: string;
  title: string;
  url?: string | null;
  retrieved_at: string;
};

type Report = {
  ticker: string;
  company_name: string;
  executive_summary?: string | null;
  calculated_metrics: Metric[];
  key_financials: Metric[];
  growth_analysis?: string | null;
  profitability_analysis?: string | null;
  valuation_analysis?: string | null;
  risks: string[];
  llm_interpretation?: string | null;
  sources: Source[];
};

type Job = {
  job_id: string;
  ticker: string;
  question: string;
  status: string;
  report?: Report | null;
  error?: string | null;
};

const tabs = ["Overview", "Fundamentals", "Valuation", "Filings", "Macro", "Sources"] as const;

function App() {
  const [ticker, setTicker] = useState("MSFT");
  const [question, setQuestion] = useState("Analyze Microsoft's fundamentals and valuation.");
  const [job, setJob] = useState<Job | null>(null);
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>("Overview");
  const [events, setEvents] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const metrics = useMemo(() => job?.report?.key_financials?.length ? job.report.key_financials : job?.report?.calculated_metrics ?? [], [job]);

  async function runResearch() {
    setLoading(true);
    setEvents(["research_started"]);
    setJob(null);
    try {
      const response = await fetch("/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, question })
      });
      const created: Job = await response.json();
      setJob(created);
      setEvents((current) => [...current, "job_created"]);
      await pollJob(created.job_id);
    } catch (error) {
      setEvents((current) => [...current, "failed"]);
    } finally {
      setLoading(false);
    }
  }

  async function pollJob(jobId: string) {
    for (let attempt = 0; attempt < 30; attempt += 1) {
      const response = await fetch(`/research/${jobId}`);
      const current: Job = await response.json();
      setJob(current);
      setEvents((existing) => [...new Set([...existing, current.status])]);
      if (current.status === "complete" || current.status === "failed") return;
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div className="brand">
          <Building2 size={22} />
          <div>
            <h1>Financial Research Agent</h1>
            <p>Traceable company research workspace</p>
          </div>
        </div>
        <div className="runbar">
          <label>
            <span>Ticker</span>
            <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} />
          </label>
          <button onClick={runResearch} disabled={loading}>
            {loading ? <RefreshCcw size={18} className="spin" /> : <Play size={18} />}
            <span>{loading ? "Running" : "Run Research"}</span>
          </button>
        </div>
      </section>

      <section className="workspace">
        <aside className="panel sidebar">
          <label className="question">
            <span>Research Agent</span>
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
          </label>
          <div className="progress">
            {["research_started", "job_created", "running", "complete"].map((event) => (
              <div className={events.includes(event) ? "step active" : "step"} key={event}>
                <ShieldCheck size={16} />
                <span>{event.replaceAll("_", " ")}</span>
              </div>
            ))}
          </div>
        </aside>

        <section className="content">
          <div className="metrics">
            {(metrics.length ? metrics : sampleMetrics).slice(0, 4).map((metric) => (
              <article className="metric" key={metric.name}>
                <span>{metric.name.replaceAll("_", " ")}</span>
                <strong>{formatMetric(metric)}</strong>
                <small>{metric.period ?? metric.source ?? "Awaiting verified data"}</small>
              </article>
            ))}
          </div>

          <nav className="tabs">
            {tabs.map((tab) => (
              <button className={activeTab === tab ? "selected" : ""} onClick={() => setActiveTab(tab)} key={tab}>
                {tabIcon(tab)}
                <span>{tab}</span>
              </button>
            ))}
          </nav>

          <article className="report">
            {renderTab(activeTab, job)}
          </article>
        </section>
      </section>
    </main>
  );
}

const sampleMetrics: Metric[] = [
  { name: "Price", value: 0, source: "Awaiting market data" },
  { name: "Revenue Growth", value: 0, source: "Awaiting calculations" },
  { name: "Operating Margin", value: 0, source: "Awaiting calculations" },
  { name: "P/E", value: 0, source: "Awaiting market data" }
];

function formatMetric(metric: Metric) {
  const value = metric.unit === "%" || metric.name.toLowerCase().includes("margin") || metric.name.toLowerCase().includes("growth")
    ? `${(metric.value * 100).toFixed(1)}%`
    : metric.value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return `${value}${metric.unit && metric.unit !== "%" ? ` ${metric.unit}` : ""}`;
}

function tabIcon(tab: string) {
  const props = { size: 16 };
  if (tab === "Overview") return <Activity {...props} />;
  if (tab === "Fundamentals") return <BarChart3 {...props} />;
  if (tab === "Sources" || tab === "Filings") return <FileText {...props} />;
  return <Search {...props} />;
}

function renderTab(tab: string, job: Job | null) {
  const report = job?.report;
  if (!report) {
    return <p className="empty">Run research to populate verified facts, calculated metrics, interpretation, and citations.</p>;
  }
  if (tab === "Sources") {
    return <SourceList sources={report.sources} />;
  }
  if (tab === "Fundamentals") {
    return <TextBlock title="Fundamentals" text={report.growth_analysis || report.profitability_analysis || report.executive_summary} />;
  }
  if (tab === "Valuation") {
    return <TextBlock title="Valuation" text={report.valuation_analysis || report.executive_summary} />;
  }
  if (tab === "Filings") {
    return <SourceList sources={report.sources.filter((source) => source.source_type.toLowerCase().includes("sec"))} />;
  }
  if (tab === "Macro") {
    return <TextBlock title="Macro" text="Macro context is available through FRED-backed tools when requested by the research question." />;
  }
  return <TextBlock title={`${report.ticker} Research`} text={report.executive_summary || report.llm_interpretation || "No summary returned."} />;
}

function TextBlock({ title, text }: { title: string; text?: string | null }) {
  return (
    <>
      <h2>{title}</h2>
      <p>{text || "No verified analysis returned for this section."}</p>
    </>
  );
}

function SourceList({ sources }: { sources: Source[] }) {
  if (!sources.length) return <p className="empty">No citations returned yet.</p>;
  return (
    <ul className="sources">
      {sources.map((source) => (
        <li key={`${source.title}-${source.url}`}>
          <span>{source.source_type}</span>
          {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> : <strong>{source.title}</strong>}
        </li>
      ))}
    </ul>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
