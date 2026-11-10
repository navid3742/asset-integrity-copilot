import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Bot,
  Box,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  ClipboardCheck,
  Cpu,
  Database,
  ExternalLink,
  FileCheck2,
  FileClock,
  FilePlus2,
  FileSearch,
  FileText,
  Fingerprint,
  Gauge,
  Layers3,
  LockKeyhole,
  LogOut,
  Menu,
  MessageSquareText,
  RefreshCw,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  TerminalSquare,
  TriangleAlert,
  Workflow,
  X,
  type LucideIcon,
} from 'lucide-react'
import { api, ApiError, clearPassword, savePassword } from './api'
import {
  Empty,
  Overlay,
  Pill,
  ProcessSchematic,
  SectionTitle,
  StatCard,
  StatusPill,
  TableShell,
  TextButton,
} from './components'
import type {
  ChatResult,
  AssetRecord,
  DocItem,
  Incident,
  Inspection,
  Maintenance,
  Message,
  Page,
  Report,
  Stats,
  Trace,
} from './types'

const menu: { id: Page; label: string; icon: LucideIcon }[] = [
  { id: 'overview', label: 'Overview', icon: Layers3 },
  { id: 'assistant', label: 'AI Assistant', icon: MessageSquareText },
  { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
  { id: 'assets', label: 'Equipment Assets', icon: Box },
  { id: 'reports', label: 'Integrity Reports', icon: ClipboardCheck },
  { id: 'activity', label: 'Agent Activity', icon: Activity },
]
const prompts = [
  {
    tag: 'PUMP',
    title: 'Investigate P-204',
    prompt:
      'Investigate pump P-204. Summarize vibration inspections, seal incident, open work orders and relevant SOPs.',
    icon: FileSearch,
  },
  {
    tag: 'VALVE',
    title: 'Investigate CV-310',
    prompt:
      'Review control valve CV-310: actuator position feedback, maintenance history, incident and valve SOP.',
    icon: ClipboardCheck,
  },
  {
    tag: 'VESSEL',
    title: 'Investigate PV-120',
    prompt:
      'Investigate pressure vessel PV-120 thickness inspections, corrosion indication, pending work and applicable SOPs.',
    icon: ShieldCheck,
  },
  {
    tag: 'SAFETY',
    title: 'Agent safety controls',
    prompt:
      'What actions are prohibited for the asset integrity AI agent and why is human review required?',
    icon: Layers3,
  },
]

function App() {
  const [page, setPage] = useState<Page>('overview')
  const [stats, setStats] = useState<Stats | null>(null)
  const [docs, setDocs] = useState<DocItem[]>([])
  const [assets, setAssets] = useState<AssetRecord[]>([])
  const [reports, setReports] = useState<Report[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [lastTraces, setLastTraces] = useState<Trace[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [passwordInput, setPasswordInput] = useState('')
  const [locked, setLocked] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedDoc, setSelectedDoc] = useState<DocItem | null>(null)
  const [selectedAsset, setSelectedAsset] = useState<AssetRecord | null>(null)
  const [selectedReport, setSelectedReport] = useState<Report | null>(null)
  const [assetDetails, setAssetDetails] = useState<{
    inspections: Inspection[]
    maintenance: Maintenance[]
    incidents: Incident[]
  } | null>(null)
  const [approveChecked, setApproveChecked] = useState(false)
  const [busy, setBusy] = useState(false)
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [docSearch, setDocSearch] = useState('')
  const chatEnd = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [s, d, c, r] = await Promise.all([
        api.status(),
        api.documents(),
        api.assets(),
        api.reports(),
      ])
      setStats(s)
      setDocs(d)
      setAssets(c)
      setReports(r)
      setLocked(false)
      setError('')
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setLocked(true)
        setError('')
        return
      }
      setError(e instanceof Error ? e.message : 'Unable to load data')
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    void refresh()
  }, [refresh])
  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  const navigate = (p: Page) => {
    setPage(p)
    setSidebarOpen(false)
    setError('')
  }
  const openDocument = async (id: string) => {
    try {
      setSelectedDoc(await api.document(id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Document unavailable')
    }
  }
  const openAsset = async (comp: AssetRecord) => {
    setSelectedAsset(comp)
    setAssetDetails(null)
    try {
      setAssetDetails(await api.history(comp.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Records unavailable')
    }
  }
  const sendQuestion = async (prompt?: string) => {
    const question = (prompt || query).trim()
    if (!question || busy) return
    setPage('assistant')
    setQuery('')
    setError('')
    setBusy(true)
    const current = [...messages, { role: 'user' as const, content: question, id: Date.now() }]
    setMessages(current)
    try {
      const response: ChatResult = await api.chat(question, messages)
      setLastTraces(response.traces)
      setMessages((items) => [
        ...items,
        {
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          traces: response.traces,
          mode: response.mode,
          id: Date.now() + 1,
        },
      ])
      void api
        .status()
        .then(setStats)
        .catch(() => {})
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Agent request failed')
    } finally {
      setBusy(false)
    }
  }
  const draftReport = async (id: string) => {
    try {
      const r = await api.draft(id)
      setReports((rs) => [r, ...rs])
      setSelectedAsset(null)
      setAssetDetails(null)
      setSelectedReport(r)
      setApproveChecked(false)
      void api.status().then(setStats)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not draft report')
    }
  }
  const approveReport = async (id: string) => {
    if (!approveChecked) return
    try {
      const r = await api.approve(id)
      setSelectedReport(r)
      setReports((rs) => rs.map((x) => (x.id === id ? r : x)))
      setApproveChecked(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Approval failed')
    }
  }
  const normalizedSearch = search.trim().toLowerCase()
  const filteredAssets = useMemo(
    () =>
      assets.filter((c) =>
        [c.id, c.name, c.category, c.status, c.unit, c.location].some((v) =>
          v.toLowerCase().includes(normalizedSearch),
        ),
      ),
    [assets, normalizedSearch],
  )
  const filteredDocs = useMemo(
    () =>
      docs.filter((d) =>
        [d.id, d.title, d.category, d.description].some((v) =>
          v.toLowerCase().includes(docSearch.toLowerCase()),
        ),
      ),
    [docs, docSearch],
  )
  const flaggedCount = assets.filter((c) => c.status !== 'Normal').length

  if (locked) {
    return (
      <div className="lock-screen">
        <div className="lock-card">
          <div className="eyebrow">SECURE DEMONSTRATION</div>
          <h1>Enter access code.</h1>
          <p>
            The live agent runs on a paid API, so access is password-protected. Enter the access
            code you were given.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              savePassword(passwordInput)
              setLoading(true)
              void refresh()
            }}
          >
            <input
              type="password"
              autoFocus
              value={passwordInput}
              onChange={(e) => setPasswordInput(e.target.value)}
              placeholder="Access code"
              required
            />
            <button className="btn-primary" type="submit">
              <LockKeyhole size={16} /> Unlock dashboard
            </button>
          </form>
          <div className="lock-note">
            <ShieldCheck size={15} /> Your password is stored only in this browser tab's session
            storage.
          </div>
        </div>
      </div>
    )
  }
  return (
    <div className="app-shell">
      {sidebarOpen && <div className="mobile-scrim" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand-block">
          <div className="brand-text">
            <div className="brand-name">
              ASSET <span>INTEGRITY</span>
            </div>
            <div className="brand-sub">EQUIPMENT RELIABILITY INTELLIGENCE</div>
          </div>
          <button className="close-side icon-btn" onClick={() => setSidebarOpen(false)}>
            <X size={18} />
          </button>
        </div>
        <div className="workspace-label">
          WORKSPACE <ChevronDown size={13} />
        </div>
        <div className="workspace">
          <div className="workspace-icon">
            <Cpu size={18} />
          </div>
          <div>
            <strong>Asset Integrity / Oil & Gas</strong>
            <small>Demo Environment</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="sidebar-group-label">PLATFORM</div>
        <nav>
          {menu.map((item) => (
            <button
              key={item.id}
              className={`nav-link ${page === item.id ? 'active' : ''}`}
              onClick={() => navigate(item.id)}
            >
              <item.icon size={17} />
              {item.label}
              {page === item.id && <span className="active-line" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-group-label secondary-nav-label">RESOURCES</div>
        <nav>
          <button
            className={`nav-link ${page === 'guide' ? 'active' : ''}`}
            onClick={() => navigate('guide')}
          >
            <BookOpen size={17} />
            User guide
          </button>
          <a
            className="nav-link"
            href="https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.119"
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink size={17} />
            OSHA mechanical integrity
          </a>
        </nav>
        <div className="sidebar-bottom">
          <div className="env-card">
            <div className="env-title">
              <span className="online-dot" />
              SYSTEM STATUS
            </div>
            <div className="env-mode">
              {stats?.mode === 'live' ? 'OpenAI Agents SDK active' : 'Offline preview active'}
            </div>
            <div className="env-foot">
              {stats?.mode === 'live'
                ? 'SDK managed tool calling'
                : 'Deterministic, no API charges'}
            </div>
          </div>
          <div className="sidebar-profile">
            <div className="profile-avatar">AI</div>
            <div>
              <strong>Portfolio workspace</strong>
              <small>Unofficial concept demo</small>
            </div>
            <Settings2 size={16} />
          </div>
        </div>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu icon-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              <Menu size={21} />
            </button>
            <span className="crumb">ASSET INTEGRITY COPILOT</span>
            <ChevronRight size={13} className="crumb-chevron" />
            <span className="crumb-active">
              {menu.find((m) => m.id === page)?.label || 'User guide'}
            </span>
          </div>
          <div className="topbar-right">
            <div className="status-top">
              <span className="online-dot" />
              {stats?.mode === 'live' ? 'OPENAI CONNECTED' : 'OFFLINE PREVIEW'}
            </div>
            <button className="icon-btn" title="Refresh data" onClick={() => void refresh()}>
              <RefreshCw size={16} />
            </button>
            <button
              className="icon-btn"
              title="Clear saved demo password"
              onClick={() => {
                clearPassword()
                window.location.reload()
              }}
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>
        <main className="content">
          {error && (
            <div role="alert" className="error-banner">
              <CircleAlert size={18} />
              <span>{error}</span>
              <button onClick={() => setError('')}>
                <X size={16} />
              </button>
            </div>
          )}
          {loading && (
            <div className="page-loader">
              <RefreshCw className="spin" />
              Loading workspace…
            </div>
          )}
          {!loading && page === 'overview' && (
            <>
              <div className="hero">
                <div className="hero-grain" />
                <ProcessSchematic />
                <div className="hero-content">
                  <div className="hero-topline">
                    <span className="pulse-ring" /> PUMPS, CONTROL VALVES AND PRESSURE VESSELS
                  </div>
                  <h1>
                    ENGINEERING
                    <br />
                    <em>INTELLIGENCE.</em>
                  </h1>
                  <p>
                    Connect inspection observations, maintenance work orders and asset integrity
                    SOPs across pumps, control valves and pressure vessels.
                  </p>
                  <button className="hero-cta" onClick={() => navigate('assistant')}>
                    LAUNCH AI ASSISTANT <ArrowUpRight size={19} />
                  </button>
                </div>
                <div className="hero-corner">
                  SYNTHETIC DATA
                  <br />
                  PORTFOLIO DEMO
                </div>
              </div>
              <div className="section-row">
                <div>
                  <span className="overline">OPERATIONS AT A GLANCE</span>
                  <h2>Platform overview</h2>
                </div>
                <div className="sync-label">
                  <span className="online-dot" /> Loaded fictional records
                </div>
              </div>
              <div className="metrics-grid">
                <StatCard
                  title="EQUIPMENT ASSETS"
                  value={stats?.counts.assets || 0}
                  icon={Box}
                  footer="Indexed in oil-and-gas DB"
                />
                <StatCard
                  title="INSPECTION RECORDS"
                  value={stats?.counts.inspections || 0}
                  icon={ClipboardCheck}
                  footer="Historian-style synthetic data"
                />
                <StatCard
                  title="MAINTENANCE WORK ORDERS"
                  value={stats?.counts.maintenance || 0}
                  icon={FileClock}
                  footer="Completed and open follow-ups"
                />
                <StatCard
                  title="FLAGGED ASSETS"
                  value={flaggedCount}
                  icon={TriangleAlert}
                  footer="Review or hold status"
                />
                <StatCard
                  title="KNOWLEDGE SOURCES"
                  value={docs.length}
                  icon={Database}
                  footer="Searchable synthetic documents"
                />
              </div>
              <div className="overview-columns">
                <div className="surface panel-quick">
                  <div className="panel-header">
                    <div>
                      <span className="overline">QUICK START</span>
                      <h3>What would you like to investigate?</h3>
                    </div>
                    <ArrowUpRight size={18} />
                  </div>
                  <div className="quick-grid">
                    {prompts.map((x) => (
                      <button
                        className="quick-card"
                        onClick={() => void sendQuestion(x.prompt)}
                        key={x.tag}
                      >
                        <span className="quick-icon">
                          <x.icon size={19} />
                        </span>
                        <span>
                          <small>{x.tag}</small>
                          <strong>{x.title}</strong>
                        </span>
                        <ArrowUpRight size={15} className="quick-arrow" />
                      </button>
                    ))}
                  </div>
                </div>
                <div className="surface panel-activity">
                  <div className="panel-header">
                    <div>
                      <span className="overline">PLATFORM CAPABILITIES</span>
                      <h3>Agent architecture</h3>
                    </div>
                    <Workflow size={19} />
                  </div>
                  <div className="architecture-mini">
                    <div>
                      <span className="flow-icon">
                        <MessageSquareText size={17} />
                      </span>
                      <div>
                        <strong>Natural language request</strong>
                        <small>Grounded user queries</small>
                      </div>
                    </div>
                    <span className="flow-connector" />
                    <div>
                      <span className="flow-icon">
                        <Cpu size={17} />
                      </span>
                      <div>
                        <strong>Bounded agent workflow</strong>
                        <small>Allowlisted tool decisions</small>
                      </div>
                    </div>
                    <span className="flow-connector" />
                    <div>
                      <span className="flow-icon">
                        <Database size={17} />
                      </span>
                      <div>
                        <strong>Knowledge + database</strong>
                        <small>Citations and provenance</small>
                      </div>
                    </div>
                    <span className="flow-connector" />
                    <div>
                      <span className="flow-icon">
                        <ShieldCheck size={17} />
                      </span>
                      <div>
                        <strong>Human-reviewed actions</strong>
                        <small>Draft first, approve later</small>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bottom-note">
                <ShieldCheck size={15} /> Independent portfolio project • Entirely fictional
                facility and records • No operating decisions or equipment controls.
              </div>
            </>
          )}
          {!loading && page === 'assistant' && (
            <div className="assistant-page">
              <div className="assistant-header">
                <div>
                  <div className="eyebrow">AI / AGENT WORKSPACE</div>
                  <h1>
                    Engineering assistant<span className="accent-dot">.</span>
                  </h1>
                  <p>
                    Ask about vibration, valve positioner checks, vessel thickness, work orders and
                    linked incidents.
                  </p>
                </div>
                <div className="agent-tag">
                  <span className="online-dot" />
                  {stats?.mode === 'live' ? 'AGENTS SDK LIVE' : 'OFFLINE RETRIEVAL'}
                </div>
              </div>
              <div className="chat-shell">
                <div className="chat-history">
                  {messages.length === 0 ? (
                    <div className="chat-welcome">
                      <div className="eyebrow">OIL & GAS / MECHANICAL INTEGRITY</div>
                      <h2>What can we help you find?</h2>
                      <p>
                        Investigate pumps, valves and pressure vessels using inspections,
                        maintenance work orders and synthetic SOPs.
                      </p>
                      <div className="prompt-grid">
                        {prompts.map((x) => (
                          <button key={x.tag} onClick={() => void sendQuestion(x.prompt)}>
                            <x.icon size={18} />
                            <div>
                              <small>{x.tag}</small>
                              <strong>{x.title}</strong>
                            </div>
                            <ArrowUpRight size={16} />
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    messages.map((m) => (
                      <div className={`chat-message ${m.role}`} key={m.id}>
                        <div className="chat-avatar">
                          {m.role === 'assistant' ? <Bot size={18} /> : <span>YOU</span>}
                        </div>
                        <div className="chat-message-body">
                          <div className="message-top">
                            <strong>
                              {m.role === 'assistant' ? 'Asset Integrity Copilot' : 'You'}
                            </strong>
                            <small>
                              {m.role === 'assistant'
                                ? m.mode === 'live'
                                  ? 'Agents SDK · Tools'
                                  : 'Offline · Deterministic'
                                : 'Workspace'}
                            </small>
                          </div>
                          {m.role === 'assistant' ? (
                            <div className="markdown">
                              <ReactMarkdown>{m.content}</ReactMarkdown>
                            </div>
                          ) : (
                            <div className="user-text">{m.content}</div>
                          )}
                          {m.sources && m.sources.length > 0 && (
                            <div className="message-sources">
                              <div className="mini-label">
                                <FileText size={13} /> RETRIEVED SOURCES
                              </div>
                              <div className="source-chips">
                                {m.sources.map((s) => (
                                  <button
                                    key={s.id}
                                    onClick={() => void openDocument(s.doc_id)}
                                    title={s.excerpt}
                                  >
                                    <FileText size={13} />
                                    {s.doc_id} <ArrowUpRight size={12} />
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                          {m.traces && m.traces.length > 0 && (
                            <details className="trace-details">
                              <summary>
                                <Workflow size={14} /> Agent tool trace{' '}
                                <span>{m.traces.length} steps</span>
                              </summary>
                              {m.traces.map((t, i) => (
                                <div key={i} className="trace-row">
                                  <CheckCheck size={13} /> <code>{t.tool}</code>
                                  <span>{t.status}</span>
                                </div>
                              ))}
                            </details>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                  {busy && (
                    <div className="chat-message assistant">
                      <div className="chat-avatar">
                        <Bot size={18} />
                      </div>
                      <div className="chat-message-body">
                        <div className="message-top">
                          <strong>Asset Integrity Copilot</strong>
                        </div>
                        <div className="typing">
                          <i />
                          <i />
                          <i /> Processing request and checking evidence…
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={chatEnd} />
                </div>
                <div className="chat-compose">
                  <div className="compose-box">
                    <textarea
                      ref={inputRef}
                      rows={2}
                      value={query}
                      disabled={busy}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault()
                          void sendQuestion()
                        }
                      }}
                      placeholder="Ask about an asset tag, a procedure or an incident…"
                    />
                    <div className="compose-actions">
                      <span>
                        <ShieldCheck size={14} /> Synthetic data only ·{' '}
                        {stats?.mode === 'live' ? 'Live AI' : 'Offline preview'}
                      </span>
                      <button
                        onClick={() => void sendQuestion()}
                        disabled={busy || !query.trim()}
                        aria-label="Send message"
                      >
                        <Send size={18} />
                      </button>
                    </div>
                  </div>
                  <div className="compose-foot">
                    <span>
                      Responses are informational; qualified engineers must verify oil-and-gas
                      decisions.
                    </span>
                    <span>ENTER to send · SHIFT+ENTER for newline</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          {!loading && page === 'knowledge' && (
            <>
              <SectionTitle
                eyebrow="ENGINEERING DOCUMENTATION"
                title="Knowledge base."
                subtitle="Search the synthetic procedures and governance documents powering the assistant."
                action={
                  <Pill tone="green">
                    <Database size={13} />
                    {docs.length} INDEXED SOURCES
                  </Pill>
                }
              />
              <div className="tool-strip">
                <div className="search-field">
                  <Search size={18} />
                  <input
                    value={docSearch}
                    onChange={(e) => setDocSearch(e.target.value)}
                    placeholder="Search documents by title, ID, or category…"
                  />
                </div>
                <span className="tool-count">{filteredDocs.length} DOCUMENTS</span>
              </div>
              <div className="document-grid">
                {filteredDocs.map((doc) => (
                  <button
                    key={doc.id}
                    className="doc-card"
                    onClick={() => void openDocument(doc.id)}
                  >
                    <div className="doc-top">
                      <span className="doc-icon">
                        <FileText size={23} />
                      </span>
                      <ArrowUpRight size={17} />
                    </div>
                    <div className="doc-id">{doc.id}</div>
                    <h3>{doc.title}</h3>
                    <p>{doc.description}</p>
                    <div className="doc-foot">
                      <span>{doc.category}</span>
                      <span>
                        OPEN <ArrowRight size={13} />
                      </span>
                    </div>
                  </button>
                ))}
              </div>
              {filteredDocs.length === 0 && (
                <Empty
                  icon={FileSearch}
                  title="No documents found"
                  description="Try a different document title or category."
                />
              )}
            </>
          )}
          {!loading && page === 'assets' && (
            <>
              <SectionTitle
                eyebrow="MECHANICAL INTEGRITY"
                title="Equipment asset registry."
                subtitle="Browse pumps, control valves and pressure vessels, with linked inspections and work orders."
                action={
                  <Pill tone="neutral">
                    <Box size={13} />
                    {assets.length} ASSETS
                  </Pill>
                }
              />
              <div className="tool-strip">
                <div className="search-field">
                  <Search size={18} />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search asset tag, type, unit or location…"
                  />
                </div>
                <div className="tool-count">{filteredAssets.length} MATCHES</div>
              </div>
              <div className="surface table-panel">
                <TableShell>
                  <thead>
                    <tr>
                      <th>ASSET TAG</th>
                      <th>EQUIPMENT</th>
                      <th>TYPE</th>
                      <th>PROCESS AREA</th>
                      <th>STATUS</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAssets.map((c) => (
                      <tr key={c.id} onClick={() => void openAsset(c)} className="clickable-row">
                        <td>
                          <span className="mono-id">{c.id}</span>
                        </td>
                        <td>{c.name}</td>
                        <td>{c.category}</td>
                        <td>
                          <span className="mono-muted">{c.unit}</span>
                        </td>
                        <td>
                          <StatusPill status={c.status} />
                        </td>
                        <td>
                          <ArrowUpRight size={15} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </TableShell>
                {filteredAssets.length === 0 && (
                  <Empty
                    icon={Search}
                    title="No matching assets"
                    description="Try P-204, CV-310 or PV-120."
                  />
                )}
              </div>
            </>
          )}

          {!loading && page === 'reports' && (
            <>
              <SectionTitle
                eyebrow="CONTROLLED INTEGRITY WORKFLOW"
                title="Integrity reports."
                subtitle="Drafts compile the synthetic records; only a person can approve a report."
                action={
                  <TextButton
                    onClick={() => {
                      navigate('assets')
                      setSearch('P-204')
                    }}
                  >
                    <FilePlus2 size={16} /> New report
                  </TextButton>
                }
              />
              <div className="warning-note">
                <ShieldCheck size={19} />
                <div>
                  <strong>Human-in-the-loop control</strong>
                  <span>
                    Reports are prepared from synthetic records and have no real-world engineering
                    significance. Approval is never available as an agent tool.
                  </span>
                </div>
              </div>
              <div className="surface table-panel">
                <TableShell>
                  <thead>
                    <tr>
                      <th>REPORT ID</th>
                      <th>ASSET</th>
                      <th>CREATED</th>
                      <th>APPROVAL STATUS</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((r) => (
                      <tr
                        key={r.id}
                        className="clickable-row"
                        onClick={() => {
                          setSelectedReport(r)
                          setApproveChecked(false)
                        }}
                      >
                        <td>
                          <span className="mono-id">{r.id}</span>
                        </td>
                        <td>{r.asset_id}</td>
                        <td>{new Date(r.created_at).toLocaleString()}</td>
                        <td>
                          <StatusPill status={r.status} />
                        </td>
                        <td>
                          <ArrowUpRight size={16} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </TableShell>
                {reports.length === 0 && (
                  <Empty
                    icon={FilePlus2}
                    title="No reports yet"
                    description="Open a asset and select Prepare integrity report to create a pending draft."
                  />
                )}
              </div>
            </>
          )}
          {!loading && page === 'activity' && (
            <>
              <SectionTitle
                eyebrow="AGENT OBSERVABILITY"
                title="Activity & controls."
                subtitle="Inspect executed tool calls, model mode, and estimated API usage."
                action={
                  <Pill tone={stats?.mode === 'live' ? 'green' : 'amber'}>
                    <span className="tiny-dot" />
                    {stats?.mode === 'live' ? 'LIVE' : 'OFFLINE'}
                  </Pill>
                }
              />
              <div className="metrics-grid three">
                <StatCard
                  title="MODEL API CALLS"
                  value={stats?.usage.api_calls || 0}
                  icon={Cpu}
                  footer="Since current server start"
                />
                <StatCard
                  title="ESTIMATED API COST"
                  value={`$${(stats?.usage.estimated_usd || 0).toFixed(5)}`}
                  icon={Gauge}
                  footer="Does not include embeddings"
                />
                <StatCard
                  title="SPENDING GUARDRAIL"
                  value={`$${(stats?.usage.limit_usd || 0).toFixed(2)}`}
                  icon={ShieldCheck}
                  footer="Estimated local cutoff only"
                />
              </div>
              <div className="overview-columns">
                <div className="surface pad-panel">
                  <div className="panel-header">
                    <div>
                      <span className="overline">MOST RECENT REQUEST</span>
                      <h3>Agent execution trace</h3>
                    </div>
                    <TerminalSquare size={19} />
                  </div>
                  {lastTraces.length === 0 ? (
                    <Empty
                      icon={Workflow}
                      title="No agent calls yet"
                      description="Ask a question in AI Assistant to see its tool trace."
                    />
                  ) : (
                    <div className="trace-list">
                      {lastTraces.map((t, i) => (
                        <div key={i}>
                          <span className="trace-num">{String(i + 1).padStart(2, '0')}</span>
                          <div>
                            <strong>{t.tool}</strong>
                            <small>{JSON.stringify(t.args).slice(0, 150)}</small>
                          </div>
                          <Pill tone={t.status === 'completed' ? 'green' : 'red'}>{t.status}</Pill>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="surface pad-panel">
                  <div className="panel-header">
                    <div>
                      <span className="overline">SAFETY ARCHITECTURE</span>
                      <h3>Built-in restrictions</h3>
                    </div>
                    <LockKeyhole size={18} />
                  </div>
                  <div className="safety-list">
                    <p>
                      <Check size={16} /> Allowlisted read-only agent tools
                    </p>
                    <p>
                      <Check size={16} /> Exact equipment-tag validation
                    </p>
                    <p>
                      <Check size={16} /> Explicit user-only report approval
                    </p>
                    <p>
                      <Check size={16} /> Bounded tool rounds and response size
                    </p>
                    <p>
                      <Check size={16} /> Optional demo access password
                    </p>
                    <p>
                      <Check size={16} /> API rate limiting and usage estimate
                    </p>
                  </div>
                  <p className="small-disclaimer">
                    Limitations: In-memory usage limits reset on restart; source-grounded factuality
                    and prompt-injection resistance are not guaranteed.
                  </p>
                </div>
              </div>
            </>
          )}
          {!loading && page === 'guide' && (
            <>
              <SectionTitle
                eyebrow="ENABLEMENT / RESOURCE CENTER"
                title="Operator quickstart."
                subtitle="A training playbook for reviewing equipment records with AI assistance."
              />
              <div className="guide-grid">
                <div className="surface pad-panel">
                  <div className="overline">01 / ASK WITH CONTEXT</div>
                  <h3>Be specific about the equipment tag.</h3>
                  <p>
                    Include an exact tag (P-204, CV-310 or PV-120), what history you need, and the
                    source IDs you want cited.
                  </p>
                  <div className="guide-example">
                    “Investigate P-204 and summarize the vibration, seal and maintenance history
                    with citations.”
                  </div>
                  <button className="link-btn" onClick={() => void sendQuestion(prompts[0].prompt)}>
                    Try this prompt <ArrowRight size={15} />
                  </button>
                </div>
                <div className="surface pad-panel">
                  <div className="overline">02 / VERIFY SOURCES</div>
                  <h3>Read the evidence.</h3>
                  <p>
                    Open linked documents and compare the answer against inspection records. The
                    model can make mistakes.
                  </p>
                  <button className="link-btn" onClick={() => navigate('knowledge')}>
                    Browse documents <ArrowRight size={15} />
                  </button>
                </div>
                <div className="surface pad-panel">
                  <div className="overline">03 / KEEP APPROVAL HUMAN</div>
                  <h3>Draft, review, approve.</h3>
                  <p>
                    For integrity reports, generate a pending draft, read it, and explicitly approve
                    or reject it.
                  </p>
                  <button className="link-btn" onClick={() => navigate('reports')}>
                    View reports <ArrowRight size={15} />
                  </button>
                </div>
                <div className="surface pad-panel">
                  <div className="overline">04 / KEEP DATA SAFE</div>
                  <h3>Use only example records.</h3>
                  <p>
                    Never upload plant documents, proprietary inspection reports or personal records
                    to this fictional portfolio demo.
                  </p>
                  <button className="link-btn" onClick={() => void openDocument('POL-AI-010')}>
                    Read AI policy <ArrowRight size={15} />
                  </button>
                </div>
              </div>
              <div className="bottom-note">
                <Fingerprint size={16} /> Interview note: illustrate agent tools and responsible
                adoption together—both are central to the role.
              </div>
            </>
          )}
          <footer className="content-footer">
            <span>ASSET INTEGRITY COPILOT / PORTFOLIO CONCEPT</span>
            <span>INSPIRED BY INDUSTRIAL DESIGN · NOT AN OPERATING OR SAFETY SYSTEM</span>
          </footer>
        </main>
      </div>
      {selectedDoc && (
        <Overlay
          title={selectedDoc.title}
          subtitle={`${selectedDoc.id} · ${selectedDoc.category}`}
          onClose={() => setSelectedDoc(null)}
        >
          <div className="doc-modal-top">
            <Pill tone="green">
              <FileCheck2 size={13} /> SYNTHETIC TRAINING SOURCE
            </Pill>
            <span>TEXT / MARKDOWN</span>
          </div>
          <div className="markdown doc-markdown">
            <ReactMarkdown>{selectedDoc.content || ''}</ReactMarkdown>
          </div>
          <div className="document-disclaimer">
            <CircleAlert size={16} /> These procedures are fictional educational examples, not
            validated industrial instructions.
          </div>
        </Overlay>
      )}
      {selectedAsset && (
        <Overlay
          title={selectedAsset.id}
          subtitle={`${selectedAsset.name} · ${selectedAsset.category}`}
          onClose={() => {
            setSelectedAsset(null)
            setAssetDetails(null)
          }}
        >
          <div className="comp-summary">
            <div>
              <span>ASSET STATUS</span>
              <StatusPill status={selectedAsset.status} />
            </div>
            <div>
              <span>UNIT / AREA</span>
              <strong>{selectedAsset.unit}</strong>
            </div>
            <div>
              <span>CRITICALITY</span>
              <strong>{selectedAsset.criticality}</strong>
            </div>
            <div>
              <span>DESIGN REF</span>
              <strong>{selectedAsset.design_reference}</strong>
            </div>
          </div>
          <p className="muted">{selectedAsset.description}</p>
          <div className="drawer-section">
            <div className="drawer-row">
              <h3>Inspection history</h3>
              <span>{assetDetails?.inspections.length || 0} RECORDS</span>
            </div>
            {!assetDetails ? (
              <div className="small-loader">Loading history…</div>
            ) : (
              assetDetails.inspections.map((i) => (
                <div key={i.id} className="inspection-card">
                  <div>
                    <strong>{i.id}</strong>
                    <StatusPill status={i.outcome} />
                  </div>
                  <p>
                    {i.inspection_type}: {i.notes}
                  </p>
                  <small>
                    {i.inspected_at} · {i.metric}: {i.reading} {i.unit} · {i.inspector}
                  </small>
                </div>
              ))
            )}
          </div>
          <div className="drawer-section">
            <div className="drawer-row">
              <h3>Maintenance work orders</h3>
              <span>{assetDetails?.maintenance.length || 0} RECORDS</span>
            </div>
            {assetDetails?.maintenance.map((w) => (
              <div key={w.id} className="inspection-card">
                <div>
                  <strong>{w.id}</strong>
                  <StatusPill status={w.status} />
                </div>
                <p>
                  {w.work_type}: {w.description}
                </p>
                <small>
                  {w.performed_at} · {w.next_step}
                </small>
              </div>
            ))}
          </div>
          <div className="drawer-section">
            <div className="drawer-row">
              <h3>Linked incidents</h3>
              <span>{assetDetails?.incidents.length || 0} ITEMS</span>
            </div>
            {assetDetails?.incidents.map((i) => (
              <div className="incident-card" key={i.id}>
                <div>
                  <TriangleAlert size={17} />
                  <strong>{i.id}</strong>
                  <StatusPill status={i.status} />
                </div>
                <p>{i.issue}</p>
                <small>{i.follow_up}</small>
              </div>
            ))}
            {assetDetails?.incidents.length === 0 && (
              <p className="muted">No incidents in the synthetic dataset.</p>
            )}
          </div>
          <TextButton disabled={!assetDetails} onClick={() => void draftReport(selectedAsset.id)}>
            <FilePlus2 size={17} /> Prepare integrity review
          </TextButton>
          <div className="drawer-action-hint">
            Creates a pending fictional report. Separate user approval cannot authorize plant work.
          </div>
        </Overlay>
      )}

      {selectedReport && (
        <Overlay
          title={selectedReport.id}
          subtitle={`Integrity review · ${selectedReport.asset_id}`}
          onClose={() => {
            setSelectedReport(null)
            setApproveChecked(false)
          }}
        >
          <div className="report-top">
            <span>REPORT STATUS</span>
            <StatusPill status={selectedReport.status} />
          </div>
          <div className="report-body">
            <div className="overline">REPORT CONTENT / GENERATED FROM STRUCTURED RECORDS</div>
            <pre>{selectedReport.summary}</pre>
          </div>
          <div className="document-disclaimer">
            <CircleAlert size={16} /> This fictional report is not an inspection certificate,
            engineering disposition, operational permit or fitness-for-service decision.
          </div>
          {selectedReport.status === 'pending' ? (
            <div className="approval-panel">
              <div className="eyebrow">REQUIRES HUMAN CONFIRMATION</div>
              <label className="check-line">
                <input
                  type="checkbox"
                  checked={approveChecked}
                  onChange={(e) => setApproveChecked(e.target.checked)}
                />
                <span>
                  I have reviewed the synthetic report and understand this is a demo-only approval
                  with no real-world operational consequence.
                </span>
              </label>
              <TextButton
                disabled={!approveChecked}
                onClick={() => void approveReport(selectedReport.id)}
              >
                <CheckCheck size={17} /> Approve demo report
              </TextButton>
            </div>
          ) : (
            <div className="approved-note">
              <CheckCheck size={18} /> Approved by a user action at{' '}
              {selectedReport.approved_at
                ? new Date(selectedReport.approved_at).toLocaleString()
                : 'unknown time'}
              .
            </div>
          )}
        </Overlay>
      )}
    </div>
  )
}
export default App
