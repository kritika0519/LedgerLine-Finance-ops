import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity, AlertTriangle, ArrowDown, ArrowUp, BadgeDollarSign, ChevronLeft,
  ChevronRight, CircleCheck, Clock3, ExternalLink, Filter, LayoutDashboard,
  Menu, RefreshCw, Search, ShieldAlert, SlidersHorizontal, X,
} from "lucide-react";
import { api } from "./api";
import { chartEntries, deriveDashboardData, formatMoney, formatNumber, formatPercent } from "./utils";
import "./styles.css";

const RISK_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const STATUS_OPTIONS = ["MATCHED", "DATE_MISMATCH", "DUPLICATE_PAYMENT", "AMOUNT_MISMATCH", "LEDGER_EXCEPTION", "PAYMENT_FAILED", "PAYMENT_REFUNDED"];

function App() {
  const [summary, setSummary] = useState(null);
  const [records, setRecords] = useState([]);
  const [table, setTable] = useState({ items: [], total: 0, pages: 0, page: 1, page_size: 10 });
  const [filters, setFilters] = useState({ final_status: "", exception_type: "", risk_level: "", page: 1, page_size: 10, sort_by: "risk_score", descending: "true" });
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [error, setError] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  const [investigation, setInvestigation] = useState(null);
  const [investigating, setInvestigating] = useState(false);

  const loadDashboard = async () => {
    setLoading(true); setError("");
    try {
      const [summaryData, allData] = await Promise.all([
        api.summary(),
        api.transactions({ page_size: 500, sort_by: "risk_score", descending: "true" }),
      ]);
      setSummary(summaryData); setRecords(allData.items);
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  };

  const loadTable = async (nextFilters = filters) => {
    setTableLoading(true); setError("");
    try { setTable(await api.transactions(nextFilters)); }
    catch (err) { setError(err.message); }
    finally { setTableLoading(false); }
  };

  useEffect(() => { loadDashboard(); }, []);
  useEffect(() => { if (!loading) loadTable(); }, [filters, loading]);

  const derived = useMemo(() => deriveDashboardData(records), [records]);
  const exceptionEntries = chartEntries(summary?.exception_distribution);
  const riskEntries = RISK_ORDER.map((key) => [key, summary?.risk_distribution?.[key] || 0]);
  const settlementEntries = chartEntries(derived.settlement).slice(0, 8);

  const updateFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value, page: 1 }));
  const resetFilters = () => setFilters({ final_status: "", exception_type: "", risk_level: "", page: 1, page_size: 10, sort_by: "risk_score", descending: "true" });
  const openSearch = async (event) => {
    event.preventDefault(); if (!search.trim()) return;
    try { setSelected(await api.transaction(search.trim())); setError(""); }
    catch (err) { setSelected(null); setError(err.message); }
  };
  const sortTable = () => setFilters((current) => ({ ...current, descending: current.descending === "true" ? "false" : "true", page: 1 }));

  const openInvestigation = async () => {
    setInvestigating(true); setInvestigation(null); setError("");
    try { setInvestigation(await api.investigate(selected.transaction_id)); }
    catch (err) { setError(err.message); }
    finally { setInvestigating(false); }
  };

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? "is-open" : ""}`}>
      <div className="brand"><span className="brand-mark"><Activity size={17} /></span><span>LEDGERLINE</span></div>
      <div className="workspace-label">OPERATIONS CONSOLE</div>
      <nav><a className="nav-item active" href="#overview" onClick={() => setMobileNav(false)}><LayoutDashboard size={17} />Overview</a><a className="nav-item" href="#explorer" onClick={() => setMobileNav(false)}><SlidersHorizontal size={17} />Transaction explorer</a><a className="nav-item" href="#exceptions" onClick={() => setMobileNav(false)}><ShieldAlert size={17} />Exception queue</a></nav>
      <div className="sidebar-footer"><div className="service-dot"><span />LIVE SERVICE</div><small>Decision support layer<br />v1.0.0</small></div>
    </aside>
    {mobileNav && <button className="scrim" onClick={() => setMobileNav(false)} aria-label="Close navigation" />}
    <main className="main-content">
      <header className="topbar"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20} /></button><div className="breadcrumb">FINANCE OPS <span>/</span> RECONCILIATION</div><div className="topbar-actions"><span className="last-sync"><span className="pulse" />Reconciliation API connected</span><button className="icon-button" onClick={loadDashboard} aria-label="Refresh dashboard" title="Refresh dashboard"><RefreshCw size={17} /></button></div></header>
      {error && <div className="alert error"><AlertTriangle size={17} />{error}<button onClick={() => setError("")} aria-label="Dismiss error"><X size={16} /></button></div>}
      <section className="page-heading" id="overview"><div><p className="eyebrow">CONTROL ROOM <span>•</span> DAILY RECONCILIATION</p><h1>Finance Operations<br /><em>Control Center</em></h1><p className="subtitle">Reconcile source systems, prioritize exceptions, and give every investigation a clear operational next step.</p></div><div className="heading-status"><CircleCheck size={16} /> Reconciliation pipeline healthy</div></section>
      {loading ? <LoadingState /> : !summary ? <ErrorState message={error || "Operations data could not be loaded."} onRetry={loadDashboard} /> : <>
        <section className="kpi-grid">
          <Kpi label="Total transactions" value={formatNumber(summary.total_transactions)} icon={<Activity />} detail="Across all source systems" tone="blue" />
          <Kpi label="Matched" value={formatNumber(summary.matched_transactions)} icon={<CircleCheck />} detail={`${formatPercent(summary.matched_transactions / summary.total_transactions)} of portfolio`} tone="green" />
          <Kpi label="Exceptions" value={formatNumber(summary.exception_count)} icon={<AlertTriangle />} detail={`${formatPercent(summary.exception_rate)} require review`} tone="amber" />
          <Kpi label="High-risk cases" value={formatNumber((summary.risk_distribution.HIGH || 0) + (summary.risk_distribution.CRITICAL || 0))} icon={<ShieldAlert />} detail="High + critical priority" tone="red" />
          <Kpi label="Amount mismatch cases" value={formatNumber(summary.exception_distribution.AMOUNT_MISMATCH || 0)} icon={<BadgeDollarSign />} detail={`Total observed variance: ${formatMoney(derived.amountMismatchTotal)}`} tone="violet" />
        </section>
        <section className="analytics-grid">
          <ChartCard title="Exception breakdown" caption="Final status classification"><HorizontalBars entries={exceptionEntries} /></ChartCard>
          <ChartCard title="Risk distribution" caption="Unified operational priority"><RiskBars entries={riskEntries} /></ChartCard>
          <ChartCard title="Settlement delay" caption="Date mismatch transactions"><HorizontalBars entries={settlementEntries} suffix="" empty="No settlement delays" /></ChartCard>
          <ChartCard title="Reconciliation health" caption="Matched versus exception"><Donut matched={summary.matched_transactions} exceptions={summary.exception_count} /></ChartCard>
        </section>
        <section className="priority-strip"><div className="section-heading"><div><p className="eyebrow">NEXT BEST ACTIONS</p><h2>Priority action queue</h2></div><span className="queue-count"><span />Sorted by unified risk score</span></div><PriorityActionQueue records={records.filter((record) => record.is_exception).slice(0, 4)} onSelect={setSelected} /></section>
        <section className="section-block" id="explorer"><div className="section-heading"><div><p className="eyebrow">WORK QUEUE</p><h2>Transaction explorer</h2></div><form className="search-box" onSubmit={openSearch}><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search transaction ID" aria-label="Search transaction ID" /></form></div><div className="filters"><Filter size={16} /><Select label="Final status" value={filters.final_status} onChange={(value) => updateFilter("final_status", value)} options={STATUS_OPTIONS} /><Select label="Exception type" value={filters.exception_type} onChange={(value) => updateFilter("exception_type", value)} options={STATUS_OPTIONS.filter((x) => x !== "MATCHED")} /><Select label="Risk level" value={filters.risk_level} onChange={(value) => updateFilter("risk_level", value)} options={RISK_ORDER} /><button className="clear-button" onClick={resetFilters}>Clear filters</button></div><TransactionTable table={table} loading={tableLoading} onSelect={setSelected} onSort={sortTable} onPage={(page) => setFilters((current) => ({ ...current, page }))} /></section>
        <section className="section-block exception-section" id="exceptions"><div className="section-heading"><div><p className="eyebrow">PRIORITY REVIEW</p><h2>Exception queue</h2></div><span className="queue-count"><span />{formatNumber(summary.exception_count)} cases require attention</span></div><ExceptionQueue records={records.filter((record) => record.is_exception).slice(0, 6)} onSelect={setSelected} /></section>
      </>}
      <footer>LEDGERLINE OPERATIONS <span>•</span> Data served by reconciliation API</footer>
    </main>
    {selected && <DetailPanel record={selected} onClose={() => { setSelected(null); setInvestigation(null); }} investigation={investigation} investigating={investigating} onInvestigate={openInvestigation} />}
  </div>;
}

function Kpi({ label, value, detail, icon, tone }) { return <div className="kpi-card"><div className={`kpi-icon ${tone}`}>{icon}</div><div className="kpi-copy"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div></div>; }
function ChartCard({ title, caption, children }) { return <div className="chart-card"><div className="chart-heading"><div><h3>{title}</h3><p>{caption}</p></div><span className="chart-menu">•••</span></div>{children}</div>; }
function HorizontalBars({ entries, empty = "No data", suffix = "" }) { const max = Math.max(...entries.map(([, value]) => value), 1); return entries.length ? <div className="bar-list">{entries.map(([label, value]) => <div className="bar-row" key={label}><div className="bar-label"><span title={label}>{label.replaceAll("_", " ")}</span><b>{formatNumber(value)}{suffix}</b></div><div className="bar-track"><i style={{ width: `${(value / max) * 100}%` }} /></div></div>)}</div> : <div className="empty-chart">{empty}</div>; }
function RiskBars({ entries }) { const max = Math.max(...entries.map(([, value]) => value), 1); return <div className="risk-list">{entries.map(([label, value]) => <div className="risk-row" key={label}><span className={`risk-dot ${label.toLowerCase()}`} /><span>{label}</span><div className="risk-track"><i className={label.toLowerCase()} style={{ width: `${(value / max) * 100}%` }} /></div><b>{formatNumber(value)}</b></div>)}</div>; }
function Donut({ matched, exceptions }) { const total = matched + exceptions; const angle = total ? (matched / total) * 360 : 0; return <div className="donut-wrap"><div className="donut" style={{ background: `conic-gradient(#167c72 0deg ${angle}deg, #f1b24a ${angle}deg 360deg)` }}><div><strong>{formatPercent(total ? matched / total : 0)}</strong><span>matched</span></div></div><div className="legend"><span><i className="green" />Matched <b>{formatNumber(matched)}</b></span><span><i className="amber" />Exceptions <b>{formatNumber(exceptions)}</b></span></div></div>; }
function Select({ label, value, onChange, options }) { return <label className="filter-select"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}><option value="">All</option>{options.map((option) => <option key={option} value={option}>{option.replaceAll("_", " ")}</option>)}</select></label>; }
function TransactionTable({ table, loading, onSelect, onSort, onPage }) { return <div className="table-wrap">{loading && <div className="table-overlay"><RefreshCw className="spin" size={20} />Updating queue</div>}<table><thead><tr><th>Transaction</th><th>Final status</th><th>Exception</th><th>Risk</th><th>Score <button className="sort-button" onClick={onSort}><ArrowDown size={13} /></button></th><th>Action</th></tr></thead><tbody>{table.items.length ? table.items.map((record) => <tr key={record.transaction_id} onClick={() => onSelect(record)}><td><strong>{record.transaction_id}</strong><small>{record.payment_id || "No payment assigned"}</small></td><td><StatusPill status={record.final_status} /></td><td>{record.exception_type?.replaceAll("_", " ") || "—"}</td><td><RiskPill level={record.risk_level} /></td><td><strong className="score">{Number(record.risk_score || 0).toFixed(1)}</strong></td><td><button className="row-action" onClick={(event) => { event.stopPropagation(); onSelect(record); }} aria-label={`View ${record.transaction_id}`}><ExternalLink size={15} /></button></td></tr>) : <tr><td colSpan="6"><div className="empty-table">No transactions match these filters.</div></td></tr>}</tbody></table><Pagination table={table} onPage={onPage} /></div>; }
function Pagination({ table, onPage }) { if (!table.total) return null; return <div className="pagination"><span>Showing {((table.page - 1) * table.page_size) + 1}–{Math.min(table.page * table.page_size, table.total)} of {formatNumber(table.total)}</span><div><button disabled={table.page <= 1} onClick={() => onPage(table.page - 1)} aria-label="Previous page"><ChevronLeft size={16} /></button><b>{table.page} / {table.pages}</b><button disabled={table.page >= table.pages} onClick={() => onPage(table.page + 1)} aria-label="Next page"><ChevronRight size={16} /></button></div></div>; }
function StatusPill({ status }) { return <span className={`status-pill ${status === "MATCHED" ? "matched" : "exception"}`}><i />{status?.replaceAll("_", " ")}</span>; }
function RiskPill({ level }) { return <span className={`risk-pill ${String(level).toLowerCase()}`}>{level || "—"}</span>; }
function ExceptionQueue({ records, onSelect }) { return <div className="queue-grid">{records.length ? records.map((record) => <button className="queue-item" key={record.transaction_id} onClick={() => onSelect(record)}><div className="queue-top"><span className="queue-id">{record.transaction_id}</span><RiskPill level={record.risk_level} /></div><strong>{record.exception_type?.replaceAll("_", " ")}</strong><div className="queue-bottom"><span>{record.recommended_action?.replaceAll("_", " ")}</span><b>{Number(record.risk_score || 0).toFixed(1)} score</b></div></button>) : <div className="empty-panel">No exceptions in the current dataset.</div>}</div>; }
function PriorityActionQueue({ records, onSelect }) { return <div className="priority-list">{records.length ? records.map((record, index) => <button className="priority-item" key={record.transaction_id} onClick={() => onSelect(record)}><span className="priority-index">0{index + 1}</span><div className="priority-main"><strong>{record.transaction_id}</strong><span>{record.exception_type?.replaceAll("_", " ") || "Exception"}</span></div><RiskPill level={record.risk_level} /><span className="priority-score">{Number(record.risk_score || 0).toFixed(1)}</span><span className="priority-action">{record.recommended_action?.replaceAll("_", " ") || "Manual review"}</span><ExternalLink size={15} /></button>) : <div className="empty-panel">No priority actions in the current dataset.</div>}</div>; }
function DetailPanel({ record, onClose, investigation, investigating, onInvestigate }) { const contextFields = [["Final status", record.final_status], ["Payment status", record.payment_status], ["Ledger status", record.ledger_status], ["Recommended action", record.recommended_action?.replaceAll("_", " ")]]; const varianceFields = [["Payment ID", record.payment_id], ["Amount difference", formatMoney(record.amount_difference)], ["Date difference", `${record.date_difference || 0} days`], ["Reconciliation reason", record.reason]]; return <><button className="detail-scrim" onClick={onClose} aria-label="Close transaction details" /><aside className="detail-panel"><div className="detail-header"><div><p className="eyebrow">TRANSACTION DETAIL</p><h2>{record.transaction_id}</h2><span>{record.payment_id || "No payment assignment"}</span></div><button className="icon-button" onClick={onClose} aria-label="Close details"><X size={19} /></button></div><div className="detail-priority"><div><span>Risk priority</span><strong>{Number(record.risk_score || 0).toFixed(1)}</strong></div><RiskPill level={record.risk_level} /></div><div className="detail-section system-section"><div className="section-kicker"><span className="section-marker system" />SYSTEM DECISION</div><h3>Decision context</h3>{contextFields.map(([label, value]) => <div className="detail-row" key={label}><span>{label}</span><b>{value || "—"}</b></div>)}</div><div className="detail-section"><div className="section-kicker"><span className="section-marker variance" />VARIANCE REVIEW</div><h3>Variance</h3>{varianceFields.map(([label, value]) => <div className="detail-row" key={label}><span>{label}</span><b>{value || "—"}</b></div>)}</div><div className="detail-section"><div className="section-kicker"><span className="section-marker ml" />ML RISK SIGNAL</div><h3>Risk intelligence</h3><div className="ml-signal"><span>Probability</span><b>{formatPercent(record.ml_risk_probability)}</b><span>Prediction</span><RiskPill level={record.ml_prediction ? "HIGH" : "LOW"} /><span>Risk level</span><RiskPill level={record.risk_level} /></div><div className="factor-box"><ShieldAlert size={16} /><p>{record.top_risk_factors || record.ml_reason || "No major risk factors detected."}</p></div><p className="model-note">Prioritizes transactions for operational attention; it does not determine reconciliation truth.</p></div><div className="detail-section ai-section"><div className="ai-heading"><div><div className="section-kicker"><span className="section-marker ai" />AI INVESTIGATION</div><h3>Evidence-grounded review</h3><p>Gemini explains the supplied evidence. The system decision remains authoritative.</p></div><span className="ai-spark">✦</span></div><button className="investigate-button" onClick={onInvestigate} disabled={investigating}>{investigating ? <><RefreshCw className="spin" size={15} /> Investigating</> : <><ShieldAlert size={15} /> Investigate exception</>}</button>{investigation && <div className="investigation-result"><div className="provider-label">{investigation.provider === "deterministic_fallback" ? "DETERMINISTIC FALLBACK" : "GEMINI GENERATED"}</div><p className="provenance">{investigation.provider === "deterministic_fallback" ? "AI provider unavailable; showing a local evidence-based explanation." : "AI provider: Gemini"}</p><h4>{investigation.summary}</h4><p className="investigation-reason">{investigation.reason}</p><div className="confidence-line"><span>Confidence: <b>{investigation.confidence}</b></span><small>{investigation.confidence_basis}</small></div><h5>Evidence supplied</h5><div className="evidence-list">{investigation.evidence.map((item) => <div key={`${item.source}-${item.field}`}><span>{item.source} / {item.field}</span><b>{String(item.value)}</b></div>)}</div><div className="recommendation"><span>Existing recommended action</span><strong>{investigation.recommended_action.replaceAll("_", " ")}</strong><p>{investigation.recommendation_explanation}</p></div><h5>Analyst notes</h5><ul>{investigation.analyst_notes.map((note) => <li key={note}>{note}</li>)}</ul><p className="ai-disclaimer">AI assists investigation; reconciliation status remains system-authoritative.</p></div>}</div></aside></>; }
function LoadingState() { return <div className="loading-state"><RefreshCw className="spin" size={22} /><span>Loading operations data</span></div>; }
function ErrorState({ message, onRetry }) { return <div className="loading-state error-state"><AlertTriangle size={24} /><strong>Unable to load operations data</strong><span>{message}</span><button className="retry-button" onClick={onRetry}><RefreshCw size={15} /> Try again</button></div>; }

createRoot(document.getElementById("root")).render(<App />);