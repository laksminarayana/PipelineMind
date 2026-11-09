import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity, AlertTriangle, Bot, Box, Check, ChevronRight, CircleHelp,
  Cloud, Code2, Database, GitBranch, HeartPulse, Layers3, LoaderCircle,
  LockKeyhole, Menu, Play, RefreshCw, Search, Send, Settings2, Shield,
  ShieldAlert, ShieldCheck, Sparkles, X
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis
} from 'recharts'
import { api } from './services/api'
import './styles.css'

const navigation = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'pipeline', label: 'CI/CD Pipeline', icon: GitBranch },
  { id: 'risk', label: 'AI Risk Analysis', icon: Shield },
  { id: 'assistant', label: 'AI Assistant', icon: Bot },
  { id: 'incidents', label: 'Incident History', icon: AlertTriangle },
  { id: 'memory', label: 'Hindsight Memory', icon: Database },
  { id: 'deployments', label: 'Deployments', icon: Layers3 },
  { id: 'monitoring', label: 'Monitoring', icon: HeartPulse },
  { id: 'settings', label: 'Settings', icon: Settings2 },
]

const demoSteps = [
  { step: 1, title: 'Learn from a failure', detail: 'Simulate a database configuration failure and retain its resolution.' },
  { step: 2, title: 'Recall the incident', detail: 'Repeat a similar change and review the memory-based warning.' },
  { step: 3, title: 'Deploy the fix', detail: 'Apply the learned correction and confirm a successful rollout.' },
]

function App() {
  const [page, setPage] = useState('overview')
  const [mobileNav, setMobileNav] = useState(false)
  const [metrics, setMetrics] = useState(null)
  const [deployments, setDeployments] = useState([])
  const [incidents, setIncidents] = useState([])
  const [memories, setMemories] = useState({ stats: {}, memories: [] })
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [toast, setToast] = useState('')
  const [pipeline, setPipeline] = useState(null)
  const [riskReport, setRiskReport] = useState(null)
  const [riskDiff, setRiskDiff] = useState('DB_HOST=postgres-cluster.internal:5432\\nDB_PASSWORD from environment')
  const [chat, setChat] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [memoryQuery, setMemoryQuery] = useState('')
  const [memoryResult, setMemoryResult] = useState(null)
  const [incidentQuery, setIncidentQuery] = useState('')
  const [settings, setSettings] = useState({
    groq_api_key: '', groq_model: 'openai/gpt-oss-120b',
    hindsight_api_url: 'http://localhost:8888', hindsight_api_key: '',
    hindsight_bank_id: 'pipelinemind-devops', simulation_mode: true,
  })

  const notify = useCallback((message) => {
    setToast(message)
    window.setTimeout(() => setToast(''), 3500)
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    const [metricData, deploymentData, incidentData, memoryData, healthData] = await Promise.allSettled([
      api.get('/metrics'), api.get('/deployments'), api.get('/incidents'),
      api.get('/memory'), api.get('/health'),
    ])
    if (metricData.status === 'fulfilled') setMetrics(metricData.value)
    if (deploymentData.status === 'fulfilled') setDeployments(deploymentData.value)
    if (incidentData.status === 'fulfilled') setIncidents(incidentData.value)
    if (memoryData.status === 'fulfilled') setMemories(memoryData.value)
    if (healthData.status === 'fulfilled') setHealth(healthData.value)
    setLoading(false)
  }, [])

  useEffect(() => {
    refresh()
    api.get('/settings').then(setSettings).catch(() => {})
  }, [refresh])

  const openPage = (id) => {
    setPage(id)
    setMobileNav(false)
  }

  const runDemo = async (step) => {
    setBusy(`demo-${step}`)
    try {
      const result = await api.post('/demo/run-step', { step })
      notify(result.message || `Demo step ${step} completed`)
      await refresh()
    } catch (error) {
      notify(error.message)
    } finally {
      setBusy('')
    }
  }

  const runPipeline = async (shouldFail = false) => {
    setBusy('pipeline')
    try {
      const result = await api.post('/pipeline/run', {
        trigger_type: 'dashboard',
        strategy: 'rolling',
        ...(shouldFail ? {
          fail_at_stage: 'health_verification',
          failure_error: 'Postgres connection timed out: DB_SECRET is not mounted',
        } : {}),
      })
      setPipeline(result)
      notify(result.status === 'failed' ? 'Pipeline failed; an incident was recorded.' : 'Pipeline completed successfully.')
      await refresh()
    } catch (error) {
      notify(error.message)
    } finally {
      setBusy('')
    }
  }

  const analyzeRisk = async (event) => {
    event?.preventDefault()
    setBusy('risk')
    try {
      setRiskReport(await api.post('/analyze', {
        db_config_diff: riskDiff,
        deployment_strategy: 'rolling',
      }))
    } catch (error) {
      notify(error.message)
    } finally {
      setBusy('')
    }
  }

  const sendChat = async (event) => {
    event.preventDefault()
    const message = chatInput.trim()
    if (!message || busy === 'chat') return
    setChatInput('')
    setChat((previous) => [...previous, { role: 'user', content: message }])
    setBusy('chat')
    try {
      const result = await api.post('/agent/chat', { message })
      setChat((previous) => [...previous, { role: 'assistant', content: result.response, provider: result.provider, memories: result.memories_used || [] }])
    } catch (error) {
      setChat((previous) => [...previous, { role: 'assistant', content: error.message }])
    } finally {
      setBusy('')
    }
  }

  const searchMemory = async (event) => {
    event.preventDefault()
    if (!memoryQuery.trim()) return
    setBusy('memory')
    try {
      setMemoryResult(await api.post('/memory/recall', { query: memoryQuery, limit: 5 }))
    } catch (error) {
      notify(error.message)
    } finally {
      setBusy('')
    }
  }

  const searchIncidents = async (event) => {
    event.preventDefault()
    try {
      setIncidents(await api.get(`/incidents?limit=100${incidentQuery ? `&search=${encodeURIComponent(incidentQuery)}` : ''}`))
    } catch (error) {
      notify(error.message)
    }
  }

  const pageTitle = navigation.find((item) => item.id === page)?.label || 'Overview'
  const visibleIncidents = incidents

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Layers3 size={20} /></div>
          <div><strong>PipelineMind</strong><span>AI DevOps platform</span></div>
          <button className="icon-button mobile-close" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <div className="workspace-select"><div className="workspace-avatar">P</div><div><strong>Platform Engineering</strong><span>production</span></div><ChevronRight size={15} /></div>
        <div className="nav-label">WORKSPACE</div>
        <nav className="main-nav">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => openPage(id)}>
              <Icon size={17} /><span>{label}</span>
              {id === 'incidents' && incidents.length > 0 && <span className="nav-badge">{incidents.length}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="memory-status"><span className={`status-dot ${health?.hindsight_memory?.is_connected_to_cloud ? 'green' : 'amber'}`} /><div><strong>Memory bank</strong><span>{health?.hindsight_memory?.is_connected_to_cloud ? 'Hindsight connected' : health?.hindsight_memory?.is_configured ? 'Configured, not verified' : 'Local demo mode'}</span></div></div>
          <div className="user-profile"><div className="user-avatar">JD</div><div><strong>Jordan Davis</strong><span>DevOps engineer</span></div><Settings2 size={16} /></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="breadcrumb">Workspace <ChevronRight size={14} /> <span>{pageTitle}</span></div>
          <div className="topbar-actions"><div className="system-status"><span className={`status-dot ${health?.status === 'healthy' ? 'green' : 'amber'}`} />{health?.status === 'healthy' ? 'All systems operational' : 'API unavailable'}</div><button className="icon-button" title="Refresh dashboard" onClick={refresh}><RefreshCw size={17} /></button><div className="user-avatar top-avatar">JD</div></div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div><div className="eyebrow"><span className="live-dot" /> LIVE WORKSPACE</div><h1>{pageTitle}</h1><p>{pageDescription(page)}</p></div>
            <div className="heading-actions"><span className={`mode-chip ${health?.hindsight_memory?.is_connected_to_cloud ? 'connected' : ''}`}><Database size={14} />{health?.hindsight_memory?.is_connected_to_cloud ? 'Hindsight Cloud' : health?.hindsight_memory?.is_configured ? 'Hindsight Configured' : 'Hindsight Local Demo'}</span>{page === 'overview' && <button className="button button-primary" onClick={() => runPipeline()} disabled={!!busy}><Play size={15} fill="currentColor" />{busy === 'pipeline' ? 'Running…' : 'Run pipeline'}</button>}</div>
          </div>

          {page === 'overview' && <Overview metrics={metrics} deployments={deployments} incidents={incidents} loading={loading} pipeline={pipeline} onNavigate={openPage} onRunDemo={runDemo} busy={busy} />}
          {page === 'pipeline' && <PipelineView pipeline={pipeline} busy={busy} onRun={runPipeline} onDemo={runDemo} />}
          {page === 'risk' && <RiskView diff={riskDiff} setDiff={setRiskDiff} report={riskReport} busy={busy} onAnalyze={analyzeRisk} />}
          {page === 'assistant' && <AssistantView chat={chat} input={chatInput} setInput={setChatInput} busy={busy} onSend={sendChat} />}
          {page === 'incidents' && <IncidentsView incidents={visibleIncidents} query={incidentQuery} setQuery={setIncidentQuery} onSearch={searchIncidents} onRefresh={refresh} />}
          {page === 'memory' && <MemoryView data={memories} result={memoryResult} query={memoryQuery} setQuery={setMemoryQuery} onSearch={searchMemory} busy={busy} />}
          {page === 'deployments' && <DeploymentsView deployments={deployments} busy={busy} onRollback={async (id) => {
            setBusy(`rollback-${id}`)
            try { await api.post('/rollback', { deployment_id: id }); notify('Rollback simulation completed.'); await refresh() }
            catch (error) { notify(error.message) }
            finally { setBusy('') }
          }} />}
          {page === 'monitoring' && <MonitoringView metrics={metrics} loading={loading} />}
          {page === 'settings' && <SettingsView settings={settings} setSettings={setSettings} busy={busy} onSave={async (event) => {
            event.preventDefault()
            setBusy('settings')
            try { await api.post('/settings', settings); setSettings(await api.get('/settings')); notify('Settings saved.') }
            catch (error) { notify(error.message) }
            finally { setBusy('') }
          }} />}
        </div>
        <footer className="footer"><span>PipelineMind AI <span className="footer-sep">/</span> v1.0.0</span><span><span className="status-dot green" /> API {health?.status === 'healthy' ? 'connected' : 'unavailable'} <span className="footer-sep">·</span> Data refreshes on demand</span></footer>
      </main>
      {mobileNav && <button className="mobile-backdrop" onClick={() => setMobileNav(false)} aria-label="Close navigation" />}
      {toast && <div className="toast"><Check size={17} />{toast}</div>}
    </div>
  )
}

function pageDescription(page) {
  return {
    overview: 'Your deployment intelligence, at a glance.',
    pipeline: 'Run and inspect your simulated delivery workflows.',
    risk: 'Understand change risk before it reaches production.',
    assistant: 'Ask questions grounded in your deployment history.',
    incidents: 'Investigate failures and record verified resolutions.',
    memory: 'Explore the operational knowledge your agent has retained.',
    deployments: 'Review releases and manage safe rollback simulations.',
    monitoring: 'Service health and infrastructure telemetry.',
    settings: 'Configure model providers and memory integrations.',
  }[page]
}

function Overview({ metrics, deployments, incidents, loading, pipeline, onNavigate, onRunDemo, busy }) {
  const chartData = metrics?.latency_trend || []
  const statCards = [
    { title: 'Total deployments', value: metrics?.total_deployments ?? '—', foot: 'All environments', icon: Layers3, color: 'blue' },
    { title: 'Successful deployments', value: metrics?.successful_deployments ?? '—', foot: `${metrics?.deployment_success_percentage ?? 0}% success rate`, icon: Check, color: 'green' },
    { title: 'Failed deployments', value: metrics?.failed_deployments ?? '—', foot: 'Needs investigation', icon: ShieldAlert, color: 'red' },
    { title: 'Recorded incidents', value: metrics?.recorded_incidents ?? '—', foot: `${metrics?.hindsight_memory_records ?? 0} memories retained`, icon: Database, color: 'purple' },
  ]
  return <>
    <section className="stat-grid">
      {statCards.map(({ title, value, foot, icon: Icon, color }) => <article className="stat-card" key={title}><div className={`stat-icon ${color}`}><Icon size={18} /></div><div className="stat-title">{title}</div><div className="stat-value">{loading ? <span className="skeleton short" /> : value}</div><div className="stat-foot">{foot}</div></article>)}
    </section>
    <section className="overview-grid">
      <article className="panel chart-panel"><PanelHeading title="Deployment health" subtitle="Simulated API latency · last 60 minutes" action={<span className="legend"><i /> Latency</span>} />
        <div className="chart-container">{chartData.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{ top: 10, right: 12, left: -20, bottom: 0 }}><defs><linearGradient id="latency-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#6d7cff" stopOpacity={0.28} /><stop offset="95%" stopColor="#6d7cff" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#202a3a" vertical={false} /><XAxis dataKey="time" tick={{ fill: '#77849a', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: '#77849a', fontSize: 11 }} axisLine={false} tickLine={false} unit=" ms" /><Tooltip contentStyle={{ background: '#101827', border: '1px solid #293549', borderRadius: 9, color: '#e5eaf2' }} /><Area type="monotone" dataKey="latency" stroke="#7180ff" strokeWidth={2} fill="url(#latency-fill)" /></AreaChart></ResponsiveContainer> : <EmptyState text="Monitoring data is not available yet." />}</div>
        <div className="chart-caption"><span><span className="status-dot green" />Current simulated latency <strong>{metrics?.api_latency_ms ?? '—'} ms</strong></span><span>Simulated HTTP error rate <strong>{metrics?.http_error_rate_pct ?? '—'}%</strong></span></div>
      </article>
      <article className="panel health-panel"><PanelHeading title="Service health" subtitle="Application and simulated pod status" action={<span className="health-badge"><span className={`status-dot ${metrics?.application_health ? 'green' : 'amber'}`} />{metrics?.application_health || 'Unknown'}</span>} />
        <div className="health-hero"><div className="health-ring"><HeartPulse size={25} /></div><div><strong>{metrics?.application_health || 'Unknown'}</strong><span>Monitored service status from the API</span></div></div>
        <div className="service-list">{(metrics?.active_pods || []).slice(0, 4).map((pod) => <div className="service-row" key={pod.name}><span className="service-name"><span className="status-dot green" />{pod.name}</span><span className="service-state">{pod.ready} ready</span></div>)}</div>
        <button className="text-button" onClick={() => onNavigate('monitoring')}>View monitoring <ChevronRight size={15} /></button>
      </article>
    </section>
    <section className="lower-grid">
      <article className="panel"><PanelHeading title="Recent deployments" subtitle="Latest delivery activity" action={<button className="text-button" onClick={() => onNavigate('deployments')}>View all <ChevronRight size={14} /></button>} />
        {deployments.length ? <div className="table-wrap"><table><thead><tr><th>Deployment</th><th>Environment</th><th>Status</th><th>Risk</th><th>When</th></tr></thead><tbody>{deployments.slice(0, 5).map((dep) => <tr key={dep.id}><td><div className="table-primary">{dep.service_name}</div><div className="table-secondary mono">{dep.commit_sha}</div></td><td><span className="environment-tag">{dep.environment}</span></td><td><StatusBadge value={dep.status} /></td><td><RiskBadge value={dep.risk_level || 'Low'} /></td><td className="table-secondary">{relativeTime(dep.created_at)}</td></tr>)}</tbody></table></div> : <EmptyState text={loading ? 'Loading deployments…' : 'No deployment records found.'} />}
      </article>
      <article className="panel"><PanelHeading title="AI memory learning" subtitle="Before-and-after demonstration" action={<span className="demo-label"><Sparkles size={13} /> DEMO</span>} />
        <div className="demo-steps">{demoSteps.map(({ step, title, detail }) => <div className="demo-step" key={step}><div className="step-number">{`0${step}`}</div><div className="step-copy"><strong>{title}</strong><span>{detail}</span></div><button className="step-run" disabled={!!busy} onClick={() => onRunDemo(step)}>{busy === `demo-${step}` ? <LoaderCircle size={15} className="spin" /> : <Play size={14} />}</button></div>)}</div>
        <div className="demo-note"><CircleHelp size={14} /> Runs against local demonstration data; no production systems are changed.</div>
      </article>
    </section>
    {pipeline && <div className="panel latest-run"><PanelHeading title="Latest pipeline run" subtitle={`Run ${pipeline.run_id || ''}`} action={<StatusBadge value={pipeline.status} />} /><PipelineStages stages={pipeline.stages || []} /></div>}
    <div className="demo-callout"><div className="callout-icon"><Sparkles size={19} /></div><div><strong>See the agent learn from experience</strong><span>Run the 3-step demonstration to record an incident, recall a similar failure, and verify the recommended fix.</span></div><button className="button button-secondary" onClick={() => onNavigate('pipeline')}>Explore demo <ChevronRight size={15} /></button></div>
  </>
}

function PipelineView({ pipeline, busy, onRun, onDemo }) {
  return <div className="content-stack">
    <div className="panel pipeline-intro"><div className="intro-icon"><GitBranch size={21} /></div><div><h2>Delivery pipeline</h2><p>Ten simulated stages from source checkout through health verification. Run a success path or inject a controlled failure to exercise incident learning.</p></div><div className="pipeline-actions"><button className="button button-secondary" disabled={!!busy} onClick={() => onRun(true)}><AlertTriangle size={15} />Simulate failure</button><button className="button button-primary" disabled={!!busy} onClick={() => onRun(false)}><Play size={15} />{busy === 'pipeline' ? 'Running…' : 'Run pipeline'}</button></div></div>
    <article className="panel"><PanelHeading title={pipeline ? 'Latest run' : 'Pipeline stages'} subtitle={pipeline ? `Run ${pipeline.run_id} · ${pipeline.deployment_id}` : 'Stages are updated after a pipeline run'} action={pipeline && <StatusBadge value={pipeline.status} />} />{pipeline ? <PipelineStages stages={pipeline.stages || []} /> : <div className="empty-panel"><GitBranch size={25} /><strong>No pipeline run yet</strong><span>Start a run to see stage-level status and logs.</span></div>}</article>
    <article className="panel demo-panel"><PanelHeading title="Before-and-after learning demo" subtitle="The core memory-learning workflow" /><div className="demo-steps horizontal">{demoSteps.map(({ step, title, detail }) => <div className="demo-step" key={step}><div className="step-number">{`0${step}`}</div><div className="step-copy"><strong>{title}</strong><span>{detail}</span></div><button className="button button-small button-secondary" disabled={!!busy} onClick={() => onDemo(step)}>{busy === `demo-${step}` ? <LoaderCircle size={14} className="spin" /> : <Play size={13} />}Run step</button></div>)}</div><div className="demo-note"><LockKeyhole size={14} /> Demonstration workflows are simulated. They do not execute Kubernetes operations or modify production systems.</div></article>
  </div>
}

function PipelineStages({ stages }) {
  return <div className="stage-list">{stages.map((stage, index) => <div className="stage-row" key={stage.id || stage.name}><div className={`stage-indicator ${stage.status || 'pending'}`}>{stage.status === 'success' ? <Check size={13} /> : stage.status === 'failed' ? <X size={13} /> : String(index + 1).padStart(2, '0')}</div><div className="stage-details"><div className="stage-title"><strong>{stage.name}</strong><StatusBadge value={stage.status || 'pending'} /></div><span>{stage.error_message || stage.details || (stage.logs || []).join(' · ') || 'Waiting to run'}</span></div><span className="stage-time">{stage.duration_seconds ? `${stage.duration_seconds.toFixed(1)}s` : '—'}</span></div>)}</div>
}

function RiskView({ diff, setDiff, report, busy, onAnalyze }) {
  return <div className="content-stack">
    <div className="risk-top-grid"><article className="panel"><PanelHeading title="Change input" subtitle="Paste infrastructure or dependency changes for analysis" /><form onSubmit={onAnalyze}><label className="field-label" htmlFor="diff-input">Configuration diff</label><textarea id="diff-input" className="code-input" value={diff} onChange={(event) => setDiff(event.target.value)} placeholder="+ DB_HOST=postgres.internal" rows={8} /><p className="field-help">The analyzer uses transparent rules and related incident memories. Scores are heuristic indicators, not calibrated failure probabilities.</p><button className="button button-primary" disabled={!!busy}><Sparkles size={15} />{busy === 'risk' ? 'Analyzing…' : 'Analyze deployment risk'}</button></form></article>
      <article className="panel risk-guide"><PanelHeading title="Analysis signals" subtitle="What PipelineMind checks" /><div className="signal-list"><Signal icon={Box} text="Container and Dockerfile configuration" /><Signal icon={Cloud} text="Kubernetes security and availability settings" /><Signal icon={Code2} text="Dependency and database changes" /><Signal icon={Database} text="Related incidents from Hindsight memory" /><Signal icon={ShieldCheck} text="Preventive actions and deployment decision" /></div></article></div>
    {report && <article className="panel report-panel"><PanelHeading title="Risk assessment" subtitle={`Analyzed ${relativeTime(report.analyzed_at)}`} action={<RiskBadge value={report.risk_category} />} /><div className="risk-summary"><div className={`risk-score ${riskClass(report.risk_category)}`}><strong>{report.risk_score}</strong><span>/100</span><small>HEURISTIC SCORE</small></div><div><span className="eyebrow">DEPLOYMENT DECISION</span><h2>{report.deployment_decision?.replaceAll('_', ' ')}</h2><p>{report.llm_explanation}</p></div></div><div className="report-columns"><div><h3>Risk factors</h3>{(report.reasons || []).map((reason) => <div className="report-line" key={reason}><AlertTriangle size={15} />{reason}</div>)}</div><div><h3>Preventive actions</h3>{(report.recommended_preventive_actions || []).map((action) => <div className="report-line positive" key={action}><ShieldCheck size={15} />{action}</div>)}</div></div>{report.related_incidents?.length > 0 && <div className="related-memory"><Database size={15} /> {report.related_incidents.length} related historical incident(s) informed this result.</div>}</article>}
  </div>
}

function Signal({ icon: Icon, text }) { return <div className="signal-row"><span><Icon size={16} /></span>{text}<Check size={14} className="signal-check" /></div> }

function AssistantView({ chat, input, setInput, busy, onSend }) {
  const suggestions = ['Why did my last deployment fail?', 'Have we seen a database timeout before?', 'Should I deploy this version?']
  return <div className="assistant-layout"><section className="panel chat-panel"><div className="chat-header"><div className="assistant-avatar"><Bot size={20} /></div><div><strong>PipelineMind Assistant</strong><span><span className="status-dot green" /> Ready · Uses deployment memory</span></div><span className="mode-chip">AI ASSISTANT</span></div>
    <div className="chat-messages">{chat.length === 0 ? <div className="chat-welcome"><div className="welcome-spark"><Sparkles size={22} /></div><h2>Your DevOps co-pilot</h2><p>Ask about deployments, incidents, or operational patterns. Replies can include relevant memories from your Hindsight bank.</p><div className="suggestion-list">{suggestions.map((text) => <button key={text} onClick={() => setInput(text)}>{text}<ChevronRight size={14} /></button>)}</div></div> : chat.map((item, index) => <div className={`chat-message ${item.role}`} key={`${index}-${item.content.slice(0, 12)}`}><div className="message-avatar">{item.role === 'assistant' ? <Bot size={15} /> : 'JD'}</div><div className="message-content"><div>{item.content}</div>{item.provider && <span className="message-meta">{item.provider}{item.memories?.length ? ` · ${item.memories.length} memories recalled` : ''}</span>}</div></div>)}{busy === 'chat' && <div className="chat-message assistant"><div className="message-avatar"><Bot size={15} /></div><div className="thinking"><i /><i /><i /></div></div>}</div>
    <form className="chat-compose" onSubmit={onSend}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask about incidents, deployments, or infrastructure…" /><button className="button button-primary" disabled={!input.trim() || busy === 'chat'} aria-label="Send message"><Send size={16} /></button></form><div className="chat-disclaimer">AI-generated guidance can be inaccurate. Verify recommendations before applying changes.</div></section>
    <aside className="panel assistant-context"><PanelHeading title="Context sources" subtitle="Available to your assistant" /><div className="context-card"><Database size={17} /><div><strong>Hindsight memory</strong><span>{healthLabel(chat)} · {chat.reduce((count, item) => count + (item.memories?.length || 0), 0)} memories used this chat</span></div></div><div className="context-card"><Layers3 size={17} /><div><strong>Deployment history</strong><span>Recent runs and their outcomes</span></div></div><div className="context-card"><AlertTriangle size={17} /><div><strong>Incident records</strong><span>Known root causes and resolutions</span></div></div><div className="context-note"><Shield size={15} />The assistant provides recommendations only. It cannot run commands or modify infrastructure.</div></aside>
  </div>
}

function healthLabel(chat) { return chat.length ? 'Ready' : 'Connected' }

function IncidentsView({ incidents, query, setQuery, onSearch, onRefresh }) {
  return <div className="content-stack"><article className="panel"><PanelHeading title="Incident records" subtitle={`${incidents.length} incident(s) · Search by error, root cause, or stage`} action={<form className="search-form" onSubmit={onSearch}><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search incidents…" /><button type="submit">Search</button></form>} />{incidents.length ? <div className="incident-list">{incidents.map((incident) => <div className="incident-card" key={incident.incident_id}><div className="incident-top"><div className="incident-id"><span className="incident-icon"><AlertTriangle size={16} /></span><div><strong>{incident.incident_id}</strong><span>{incident.pipeline_stage} · {relativeTime(incident.timestamp)}</span></div></div><StatusBadge value={incident.fix_succeeded ? 'resolved' : 'open'} /></div><div className="incident-fields"><div><span>ERROR</span><p>{incident.error_message}</p></div><div><span>ROOT CAUSE</span><p>{incident.root_cause || 'Not recorded'}</p></div><div><span>CORRECTIVE ACTION</span><p>{incident.corrective_action || 'Not recorded'}</p></div></div><div className="incident-foot"><span><GitBranch size={13} /> Deployment {incident.deployment_id}</span><span><Database size={13} /> {incident.memory_bank_id || 'pipelinemind-devops'}</span></div></div>)}</div> : <EmptyState text="No matching incidents. Run the failure demo to create a sample incident." action={<button className="text-button" onClick={onRefresh}>Refresh incidents <RefreshCw size={14} /></button>} />}</article></div>
}

function MemoryView({ data, result, query, setQuery, onSearch, busy }) {
  const stats = data.stats || {}
  return <div className="content-stack"><section className="stat-grid memory-stats"><StatMini label="MEMORY RECORDS" value={stats.total_memories ?? data.memories?.length ?? 0} icon={Database} /><StatMini label="BANK ID" value={stats.bank_id || 'pipelinemind-devops'} icon={Layers3} /><StatMini label="PROVIDER MODE" value={stats.status?.label || 'Local demo'} icon={Cloud} /></section>
    <article className="panel"><PanelHeading title="Recall operational memory" subtitle="Search for incidents and deployment learnings" /><form className="memory-search" onSubmit={onSearch}><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. postgres connection timeout" /><button className="button button-primary" disabled={!query.trim() || busy === 'memory'}>{busy === 'memory' ? 'Searching…' : 'Recall'}</button></form>{result && <div className="recall-result"><div className="recall-title"><Sparkles size={16} /> {result.results_count} matching memories for “{result.query}”</div>{result.memories?.map((memory, index) => <MemoryCard memory={memory} key={memory.id || index} />)}{!result.memories?.length && <EmptyState text="No related memories found." />}</div>}</article>
    <article className="panel"><PanelHeading title="Retained memories" subtitle="Persistent incident history available to the assistant" />{data.memories?.length ? <div className="memory-list">{data.memories.map((memory, index) => <MemoryCard memory={memory} key={memory.id || index} />)}</div> : <EmptyState text="No memories retained yet. Complete a demonstration step to teach the agent." />}</article>
  </div>
}

function MemoryCard({ memory }) { return <div className="memory-card"><div className="memory-card-top"><span><Database size={14} />{memory.bank_id || 'pipelinemind-devops'}</span>{memory.similarity_score != null && <span className="similarity">{Math.round(memory.similarity_score * 100)}% match</span>}<time>{relativeTime(memory.created_at)}</time></div><p>{memory.content}</p>{memory.metadata?.corrective_action && <div className="memory-fix"><Check size={14} /> Verified fix: {memory.metadata.corrective_action}</div>}</div> }

function DeploymentsView({ deployments, busy, onRollback }) {
  return <article className="panel"><PanelHeading title="Deployment history" subtitle={`${deployments.length} recorded deployment(s)`} />{deployments.length ? <div className="table-wrap"><table className="wide-table"><thead><tr><th>Service / commit</th><th>Environment</th><th>Strategy</th><th>Status</th><th>Risk</th><th>Created</th><th>Action</th></tr></thead><tbody>{deployments.map((dep) => <tr key={dep.id}><td><div className="table-primary">{dep.service_name}</div><div className="table-secondary mono">{dep.id} · {dep.commit_sha}</div></td><td><span className="environment-tag">{dep.environment}</span></td><td className="capitalize">{dep.strategy}</td><td><StatusBadge value={dep.status} /></td><td><RiskBadge value={dep.risk_level || 'Low'} /></td><td className="table-secondary">{relativeTime(dep.created_at)}</td><td><button className="table-action" disabled={!!busy || dep.status !== 'SUCCESS'} onClick={() => onRollback(dep.id)}>{busy === `rollback-${dep.id}` ? <LoaderCircle size={14} className="spin" /> : <RefreshCw size={14} />}Rollback</button></td></tr>)}</tbody></table></div> : <EmptyState text="No deployments recorded." />}</article>
}

function MonitoringView({ metrics, loading }) {
  const indicators = [
    { label: 'CPU usage', value: metrics?.cpu_usage_pct, unit: '%', color: 'blue' },
    { label: 'Memory usage', value: metrics?.memory_usage_pct, unit: '%', color: 'purple' },
    { label: 'API latency', value: metrics?.api_latency_ms, unit: ' ms', color: 'cyan' },
    { label: 'HTTP error rate', value: metrics?.http_error_rate_pct, unit: '%', color: 'red' },
  ]
  return <div className="content-stack"><div className="monitoring-banner"><Activity size={16} /><span>Metrics source: <strong>{metrics?.telemetry_source || 'Simulated demo telemetry'}</strong></span><span className="simulated-tag">DEMO DATA</span></div><section className="monitor-grid">{indicators.map((item) => <article className="panel monitor-card" key={item.label}><span className="monitor-label">{item.label}</span><strong className={item.color}>{loading ? '—' : `${item.value ?? '—'}${item.unit}`}</strong><div className="monitor-track"><i className={item.color} style={{ width: `${Math.min(100, Number(item.value) || 0)}%` }} /></div><span className="monitor-foot"><span className="status-dot green" />Within expected range</span></article>)}</section><article className="panel"><PanelHeading title="Pod status" subtitle="Sampled service availability" action={<span className="simulated-tag">SIMULATED</span>} /><div className="table-wrap"><table><thead><tr><th>Pod</th><th>Status</th><th>Ready</th><th>Restarts</th><th>CPU</th><th>Memory</th></tr></thead><tbody>{(metrics?.active_pods || []).map((pod) => <tr key={pod.name}><td className="table-primary mono">{pod.name}</td><td><StatusBadge value={pod.status} /></td><td>{pod.ready}</td><td>{pod.restarts}</td><td>{pod.cpu}</td><td>{pod.mem}</td></tr>)}</tbody></table></div></article><div className="info-note"><CircleHelp size={15} />The application currently provides simulated monitoring values. Connect a Prometheus target to use live infrastructure metrics.</div></div>
}

function SettingsView({ settings, setSettings, busy, onSave }) {
  const update = (key, value) => setSettings((current) => ({ ...current, [key]: value }))
  return <div className="settings-layout"><form className="panel settings-form" onSubmit={onSave}><PanelHeading title="AI provider" subtitle="Configure Groq or use local simulation" /><label className="toggle-row"><div><strong>Simulation mode</strong><span>Use local responses without calling an external LLM provider.</span></div><input type="checkbox" checked={!!settings.simulation_mode} onChange={(event) => update('simulation_mode', event.target.checked)} /><span className="toggle-control" /></label><div className="form-grid"><label><span className="field-label">Groq API key</span><input type="password" autoComplete="new-password" value={settings.groq_api_key || ''} onChange={(event) => update('groq_api_key', event.target.value)} placeholder="Enter key (stored in local app database)" /></label><label><span className="field-label">Groq model</span><input value={settings.groq_model || ''} onChange={(event) => update('groq_model', event.target.value)} placeholder="openai/gpt-oss-120b" /></label></div><div className="settings-divider" /><PanelHeading title="Hindsight memory" subtitle="Official server integration or local demo engine" /><div className="form-grid"><label><span className="field-label">Hindsight API URL</span><input value={settings.hindsight_api_url || ''} onChange={(event) => update('hindsight_api_url', event.target.value)} placeholder="http://localhost:8888" /></label><label><span className="field-label">Memory bank ID</span><input value={settings.hindsight_bank_id || ''} onChange={(event) => update('hindsight_bank_id', event.target.value)} placeholder="pipelinemind-devops" /></label><label className="full-field"><span className="field-label">Hindsight API key</span><input type="password" autoComplete="new-password" value={settings.hindsight_api_key || ''} onChange={(event) => update('hindsight_api_key', event.target.value)} placeholder="Enter key if using a secured Hindsight server" /></label></div><div className="settings-note"><Shield size={15} />Credentials are stored in the local SQLite settings table. Do not use production secrets in a shared demo environment.</div><button className="button button-primary" disabled={busy === 'settings'}>{busy === 'settings' ? 'Saving…' : 'Save settings'}<ChevronRight size={15} /></button></form><aside className="panel settings-status"><PanelHeading title="Integration status" subtitle="Current connection mode" /><div className="integration-card"><span className={`integration-icon ${settings.simulation_mode ? 'amber' : 'green'}`}><Bot size={18} /></span><div><strong>Groq AI</strong><span>{settings.simulation_mode ? 'Local simulation enabled' : settings.groq_api_key ? 'Configured' : 'API key required'}</span></div><span className={`status-dot ${settings.simulation_mode || settings.groq_api_key ? 'green' : 'amber'}`} /></div>    <div className="integration-card"><span className={`integration-icon ${settings.hindsight_status?.is_connected_to_cloud ? 'green' : 'amber'}`}><Database size={18} /></span><div><strong>Hindsight</strong><span>{settings.hindsight_status?.is_connected_to_cloud ? 'Official server connected' : settings.hindsight_status?.is_configured ? 'Configured; connection unverified' : 'Local SQLite demo engine'}</span></div><span className={`status-dot ${settings.hindsight_status?.is_connected_to_cloud ? 'green' : 'amber'}`} /></div><div className="settings-status-note"><LockKeyhole size={15} />No deployment action is automatically executed by changing these settings.</div></aside></div>
}

function StatMini({ label, value, icon: Icon }) { return <article className="panel mini-stat"><span className="mini-stat-icon"><Icon size={16} /></span><span className="mini-stat-label">{label}</span><strong>{value}</strong></article> }
function PanelHeading({ title, subtitle, action }) { return <div className="panel-heading"><div><h2>{title}</h2>{subtitle && <span>{subtitle}</span>}</div>{action}</div> }
function StatusBadge({ value }) { const normalized = String(value || 'pending').toLowerCase(); return <span className={`status-badge ${normalized.replaceAll('_', '-')}`}><i />{normalized.replaceAll('_', ' ')}</span> }
function RiskBadge({ value }) { return <span className={`risk-badge ${riskClass(value)}`}>{value || 'Low'}</span> }
function riskClass(value) { const normalized = String(value || '').toLowerCase(); return normalized.includes('high') || normalized.includes('reject') ? 'high' : normalized.includes('medium') || normalized.includes('review') ? 'medium' : 'low' }
function EmptyState({ text, action }) { return <div className="empty-state"><span>{text}</span>{action}</div> }
function relativeTime(value) { if (!value) return '—'; const date = new Date(value); if (Number.isNaN(date.getTime())) return value; const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000)); if (seconds < 60) return 'just now'; if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`; if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`; return date.toLocaleDateString() }

createRoot(document.getElementById('root')).render(<App />)
