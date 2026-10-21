import { useState, useEffect } from 'react'
import {
  TrendingUp, TrendingDown, CheckCircle2, XCircle,
  LayoutDashboard, Activity, Target, Cpu, BarChart2,
  Bell, User, AlertCircle, Plus, X, Loader2, Trash2,
  BookOpen, History, Rss, Settings2, Database, ExternalLink
} from 'lucide-react'

// ─── Design tokens (from reference) ──────────────────────────────────────────

const C = {
  primary:        '#d0bcff',
  secondary:      '#4cd7f6',
  tertiary:       '#fbabff',
  error:          '#ffb4ab',
  surface:        '#131314',
  surfaceLow:     '#0e0e0f',
  surfaceHigh:    '#2a2a2b',
  onSurface:      '#e5e2e3',
  onSurfaceVar:   '#cbc3d7',
  outline:        '#958ea0',
  outlineVar:     '#494454',
}

// UP → cyan (secondary), DOWN → pink border + red text
const DIR = {
  up:       { label: 'UP',       border: C.secondary, text: C.secondary, glow: 'neon-glow-cyan',   confColor: C.secondary, subColor: C.secondary },
  down:     { label: 'DOWN',     border: C.tertiary,  text: C.error,     glow: 'neon-glow-pink',   confColor: C.tertiary,  subColor: C.tertiary  },
  neutral:  { label: 'NEUTRAL',  border: C.outline,   text: C.outline,   glow: '',                 confColor: C.outline,   subColor: C.outline   },
  shortage: { label: 'SHORTAGE', border: C.primary,   text: C.primary,   glow: 'neon-glow-purple', confColor: C.primary,   subColor: C.primary   },
  surplus:  { label: 'SURPLUS',  border: C.outline,   text: C.outline,   glow: '',                 confColor: C.outline,   subColor: C.outline   },
}

const CONF = {
  high:   { label: 'High',   segs: 3 },
  medium: { label: 'Medium', segs: 2 },
  low:    { label: 'Low',    segs: 1 },
}

function subjectIcon(subject, dir) {
  const s = (subject || '').toLowerCase()
  const color = dir?.text || C.secondary
  if (s.includes('tesla') || s.includes('stock'))
    return <TrendingUp size={20} style={{ color }} />
  if (s.includes('gold') || s.includes('silver'))
    return <Activity size={20} style={{ color }} />
  if (s.includes('gpu') || s.includes('chip') || s.includes('price'))
    return <Cpu size={20} style={{ color }} />
  return <BarChart2 size={20} style={{ color }} />
}

// ─── Reasoning formatter ──────────────────────────────────────────────────────

function ReasoningBox({ text, dir }) {
  if (!text) return null
  const sentences = text.match(/[^.!?]+[.!?]*/g) || [text]
  const clean = sentences.map(s => s.trim()).filter(Boolean)

  return (
    <div style={{ background: 'rgba(0,0,0,0.4)', borderRadius: 8, padding: 16, marginBottom: 16 }}>
      <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {clean.map((sentence, i) => (
          <li key={i} style={{ display: 'flex', gap: 10, fontSize: 14, lineHeight: '22px',
            color: i === clean.length - 1 && clean.length > 1 ? C.onSurfaceVar : C.onSurface }}>
            <span style={{ color: dir.text, flexShrink: 0, marginTop: 1 }}>•</span>
            <span>{sentence}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function signalMeta(signal) {
  const s = (signal || '').toLowerCase()
  if (s.includes('risk') || s.includes('concern') || s.includes('supply') || s.includes('shortage'))
    return { label: 'Risk Alert',   dot: C.error,     shadow: `0 0 8px ${C.error}` }
  if (s.includes('ai') || s.includes('tech') || s.includes('gpu') || s.includes('chip'))
    return { label: 'AI Momentum',  dot: C.primary,   shadow: `0 0 8px ${C.primary}` }
  if (s.includes('market') || s.includes('analyst') || s.includes('price') || s.includes('rally'))
    return { label: 'Market Flash', dot: C.secondary, shadow: `0 0 8px ${C.secondary}` }
  return { label: 'Signal',         dot: C.outlineVar, shadow: 'none' }
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

function useClock() {
  const [t, setT] = useState(new Date())
  useEffect(() => { const i = setInterval(() => setT(new Date()), 1000); return () => clearInterval(i) }, [])
  return t.toLocaleTimeString()
}

function currencySymbol(ticker) {
  if (!ticker) return '$'
  if (ticker.endsWith('.NS') || ticker.endsWith('.BO')) return '₹'
  if (ticker.endsWith('.L'))  return '£'
  if (ticker.endsWith('.PA') || ticker.endsWith('.DE') || ticker.endsWith('.AS')) return '€'
  return '$'
}

// ─── Category colors ─────────────────────────────────────────────────────────

const CAT = {
  stock:               { label: 'Stock',       color: C.primary },
  crypto:              { label: 'Crypto',      color: '#f7931a' },
  commodity:           { label: 'Commodity',   color: '#fbbf24' },
  etf:                 { label: 'ETF',         color: C.secondary },
  consumer_electronics:{ label: 'Electronics', color: C.tertiary },
  general:             { label: 'General',     color: C.outline },
}

// ─── Sparkline ────────────────────────────────────────────────────────────────

function Sparkline({ ticker, color }) {
  const [prices, setPrices] = useState([])
  useEffect(() => {
    if (!ticker) return
    fetch(`/api/sparkline/${ticker}`).then(r => r.json()).then(d => setPrices(d.prices || [])).catch(() => {})
  }, [ticker])
  if (prices.length < 2) return null

  const W = 72, H = 24
  const min = Math.min(...prices), max = Math.max(...prices)
  const range = max - min || 1
  const pts = prices.map((p, i) => {
    const x = (i / (prices.length - 1)) * W
    const y = H - ((p - min) / range) * H
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width={W} height={H} style={{ overflow: 'visible', flexShrink: 0 }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" opacity="0.7" />
    </svg>
  )
}

// ─── Live Price ───────────────────────────────────────────────────────────────

function LivePrice({ ticker, baseline, compact = false }) {
  const [price, setPrice] = useState(null)
  useEffect(() => {
    if (!ticker) return
    fetch(`/api/price/${ticker}`).then(r => r.json()).then(d => setPrice(d.price)).catch(() => {})
  }, [ticker])
  if (!ticker || !price) return null

  const change = baseline ? ((price - baseline) / baseline * 100) : null
  const up = change >= 0
  const sym = currencySymbol(ticker)

  if (compact) return (
    <div className="flex items-center gap-2">
      <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: C.secondary, flexShrink: 0 }} />
      <span style={{ fontSize: 12, color: C.secondary }}>{sym}{price}</span>
      {change !== null && (
        <span style={{ fontSize: 11, color: up ? '#4ade80' : C.error }}>
          {up ? '▲' : '▼'} {Math.abs(change).toFixed(1)}%
        </span>
      )}
    </div>
  )

  return (
    <div className="flex items-center gap-1.5" style={{ fontSize: 13, color: C.secondary }}>
      <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: C.secondary }} />
      Live {sym}{price}
      {change !== null && (
        <span style={{ fontSize: 12, color: up ? '#4ade80' : C.error, marginLeft: 4 }}>
          ({up ? '+' : ''}{change.toFixed(1)}%)
        </span>
      )}
    </div>
  )
}

// ─── Confidence Bar ───────────────────────────────────────────────────────────

function ConfBar({ confidence, direction }) {
  const conf = CONF[confidence] || CONF.low
  const dir  = DIR[direction]   || DIR.neutral
  return (
    <div className="flex items-center gap-3">
      <span style={{ fontSize: 12, color: C.outline }}>Confidence: {conf.label}</span>
      <div className="flex gap-1">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} style={{
            height: 4, width: 24, borderRadius: 9999,
            background: i < conf.segs ? dir.confColor : 'rgba(149,142,160,0.2)'
          }} />
        ))}
      </div>
    </div>
  )
}

// ─── Confidence Stat Card ─────────────────────────────────────────────────────

function ConfidenceStatCard({ predictions }) {
  const scored = predictions.filter(p => p.outcome === 'correct' || p.outcome === 'incorrect')

  const calc = (level) => {
    const group = scored.filter(p => p.confidence === level)
    if (!group.length) return null
    const correct = group.filter(p => p.outcome === 'correct').length
    return Math.round(correct / group.length * 100)
  }

  const rows = [
    { label: 'High',   acc: calc('high'),   color: C.primary },
    { label: 'Medium', acc: calc('medium'),  color: C.secondary },
    { label: 'Low',    acc: calc('low'),     color: C.outline },
  ]

  const hasAny = rows.some(r => r.acc !== null)

  return (
    <div className="glass-card rounded-xl relative overflow-hidden" style={{ padding: 24 }}>
      <div className="flex justify-between items-start" style={{ marginBottom: 16 }}>
        <Target size={24} style={{ color: C.outline }} />
        <span style={{ fontSize: 12, color: C.secondary, background: `${C.secondary}1a`, padding: '2px 8px', borderRadius: 4 }}>Confidence</span>
      </div>
      {!hasAny ? (
        <div className="flex items-center gap-1.5" style={{ height: 56 }}>
          {[0,1,2].map(i => (
            <div key={i} className="animate-bounce" style={{
              width: 8, height: 8, borderRadius: '50%',
              background: 'rgba(149,142,160,0.3)', animationDelay: `${i * 75}ms`
            }} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2" style={{ marginBottom: 4 }}>
          {rows.map(r => (
            <div key={r.label} className="flex items-center justify-between">
              <span style={{ fontSize: 12, color: C.outline }}>{r.label}</span>
              {r.acc === null
                ? <span style={{ fontSize: 12, color: C.outlineVar }}>—</span>
                : <div className="flex items-center gap-2">
                    <div style={{ width: 48, height: 3, borderRadius: 9999, background: 'rgba(149,142,160,0.15)' }}>
                      <div style={{ width: `${r.acc}%`, height: '100%', borderRadius: 9999, background: r.color }} />
                    </div>
                    <span style={{ fontSize: 13, fontWeight: 600, color: r.color }}>{r.acc}%</span>
                  </div>
              }
            </div>
          ))}
        </div>
      )}
      <div style={{ fontSize: 14, letterSpacing: '0.02em', fontWeight: 500, color: C.outline }}>Accuracy by Confidence</div>
    </div>
  )
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, iconColor, glowClass, badge, value, label, calculating, accent }) {
  return (
    <div className="glass-card rounded-xl p-8 relative overflow-hidden group" style={{ padding: 24 }}>
      {accent && (
        <div style={{
          position: 'absolute', right: -16, top: -16, width: 96, height: 96,
          background: `${accent}1a`, borderRadius: '50%', filter: 'blur(32px)',
          transition: 'transform 0.3s', pointerEvents: 'none'
        }} />
      )}
      <div className="flex justify-between items-start" style={{ marginBottom: 16 }}>
        <Icon size={24} className={glowClass} style={{ color: iconColor }} />
        {badge && <span style={{ fontSize: 12, color: C.secondary, background: `${C.secondary}1a`, padding: '2px 8px', borderRadius: 4 }}>{badge}</span>}
      </div>
      {calculating
        ? <div className="flex items-center gap-1.5" style={{ height: 56 }}>
            {[0, 1, 2].map(i => (
              <div key={i} className="animate-bounce" style={{
                width: 8, height: 8, borderRadius: '50%',
                background: 'rgba(149,142,160,0.3)',
                animationDelay: `${i * 75}ms`
              }} />
            ))}
          </div>
        : <div style={{ fontSize: 48, fontWeight: 700, letterSpacing: '-0.02em', lineHeight: '56px', color: C.onSurface, marginBottom: 4 }}>
            {value ?? '—'}
          </div>
      }
      <div style={{ fontSize: 14, letterSpacing: '0.02em', fontWeight: 500, color: C.outline }}>{label}</div>
    </div>
  )
}

// ─── Prediction Card ──────────────────────────────────────────────────────────

function PredictionCard({ p, expanded, onToggle, onScore, onDiscard, wide, index }) {
  const dir  = DIR[p.direction]  || DIR.neutral
  const cat  = CAT[p.category]   || CAT.general
  const today = new Date().toISOString().split('T')[0]
  const canScore = !p.outcome && today >= p.check_date

  const statusText = p.outcome
    ? (p.outcome === 'correct' ? 'Correct' : 'Incorrect')
    : canScore ? 'Ready to Score'
    : `${p.days_remaining}d remaining`

  const statusColor = p.outcome
    ? (p.outcome === 'correct' ? '#4ade80' : C.error)
    : canScore ? C.secondary
    : C.outline

  return (
    <div
      className={`glass-card rounded-xl cursor-pointer hover:bg-white/5 transition-all duration-200 card-enter ${wide ? 'col-span-2' : ''}`}
      style={{ borderLeft: `2px solid ${dir.border}`, animationDelay: `${(index || 0) * 60}ms` }}
      onClick={onToggle}
    >
      <div style={{ padding: 24 }}>
        {/* Header */}
        <div className="flex justify-between" style={{ marginBottom: 16 }}>
          <div className="flex items-center gap-4">
            <div style={{
              width: 40, height: 40, borderRadius: 8,
              background: 'rgba(255,255,255,0.05)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
            }}>
              {subjectIcon(p.subject, dir)}
            </div>
            <div>
              <div className="flex items-center gap-2" style={{ marginBottom: 2 }}>
                <span style={{ fontSize: 18, fontWeight: 700, lineHeight: '28px', color: C.onSurface }}>{p.subject}</span>
                <span style={{
                  fontSize: 10, fontWeight: 600, padding: '1px 7px', borderRadius: 999,
                  background: `${cat.color}18`, color: cat.color,
                  border: `1px solid ${cat.color}30`, letterSpacing: '0.04em'
                }}>{cat.label}</span>
              </div>
              <div className="flex items-center gap-3">
                <span style={{ fontSize: 12, letterSpacing: '0.05em', fontWeight: 500, color: statusColor }}>{statusText}</span>
                {!p.outcome && <LivePrice ticker={p.ticker} baseline={p.baseline_price} compact />}
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="text-right">
              <div style={{ fontSize: 16, fontWeight: 700, color: dir.text }}>{dir.label}</div>
              <div style={{ fontSize: 12, letterSpacing: '0.05em', color: C.outline }}>Sentiment</div>
            </div>
            <Sparkline ticker={p.ticker} color={dir.text} />
          </div>
        </div>

        {/* Reasoning box */}
        <ReasoningBox text={p.reasoning || p.event || 'No reasoning available.'} dir={dir} />

        <ConfBar confidence={p.confidence} direction={p.direction} />
      </div>

      {/* Progress bar */}
      {!p.outcome && p.progress_pct != null && (
        <div style={{ height: 2, background: 'rgba(255,255,255,0.04)' }}>
          <div style={{
            height: '100%', width: `${p.progress_pct}%`,
            background: p.overdue ? C.error : dir.border,
            transition: 'width 0.6s ease',
            opacity: 0.6
          }} />
        </div>
      )}

      {/* Expanded */}
      {expanded && (
        <div
          style={{ borderTop: '1px solid rgba(255,255,255,0.05)', padding: 24, paddingTop: 20 }}
          onClick={e => e.stopPropagation()}
        >
          <div className="flex items-center justify-between flex-wrap gap-3" style={{ marginBottom: 16 }}>
            <LivePrice ticker={p.ticker} baseline={p.baseline_price} />
            <div className="flex gap-6" style={{ fontSize: 13, color: C.outline }}>
              {p.baseline_price && <span>Baseline <span style={{ color: C.onSurface }}>{currencySymbol(p.ticker)}{p.baseline_price}</span></span>}
              <span>Check <span style={{ color: C.onSurface }}>{p.check_date}</span></span>
              {p.outcome_price && <span>Final <span style={{ color: C.onSurface }}>{currencySymbol(p.ticker)}{p.outcome_price}</span></span>}
            </div>
          </div>

          {!p.ticker && canScore && (
            <div style={{
              background: `${C.error}0f`, border: `1px solid ${C.error}33`,
              borderRadius: 8, padding: '10px 14px', marginBottom: 16,
              fontSize: 12, color: C.error, lineHeight: '20px'
            }}>
              No price ticker — check current GPU prices on Newegg or Amazon. Compare to prices on {p.date_logged} and judge whether they moved {dir.label}.
            </div>
          )}

          {(p.signals || []).length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, letterSpacing: '0.05em', fontWeight: 500, color: C.outline, textTransform: 'uppercase', marginBottom: 10 }}>
                Signals
              </div>
              <div className="flex flex-col gap-2">
                {p.signals.map((s, i) => (
                  <div key={i} className="flex gap-2" style={{ fontSize: 14, color: C.onSurfaceVar, lineHeight: '20px' }}>
                    <span style={{ color: C.outline, flexShrink: 0 }}>›</span>{s}
                  </div>
                ))}
              </div>
            </div>
          )}

          {!p.outcome && (
            <div className="flex gap-3" style={{ marginBottom: 10 }}>
              <button
                onClick={() => onScore(p.id, 'correct')}
                className="flex-1 flex items-center justify-center gap-2 transition-opacity hover:opacity-80 cursor-pointer"
                style={{
                  padding: '10px 0', borderRadius: 8,
                  background: 'rgba(74,222,128,0.08)',
                  border: '1px solid rgba(74,222,128,0.25)',
                  fontSize: 14, fontWeight: 600, color: '#4ade80'
                }}>
                <CheckCircle2 size={14} /> Correct
              </button>
              <button
                onClick={() => onScore(p.id, 'incorrect')}
                className="flex-1 flex items-center justify-center gap-2 transition-opacity hover:opacity-80 cursor-pointer"
                style={{
                  padding: '10px 0', borderRadius: 8,
                  background: `${C.error}10`,
                  border: `1px solid ${C.error}33`,
                  fontSize: 14, fontWeight: 600, color: C.error
                }}>
                <XCircle size={14} /> Incorrect
              </button>
            </div>
          )}
          <button
            onClick={() => onDiscard(p.id)}
            className="w-full flex items-center justify-center gap-2 transition-opacity hover:opacity-80 cursor-pointer"
            style={{
              padding: '8px 0', borderRadius: 8,
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
              fontSize: 13, color: C.outline
            }}>
            <Trash2 size={13} /> Discard subject
          </button>
        </div>
      )}
    </div>
  )
}

// ─── Signal Feed ──────────────────────────────────────────────────────────────

function SignalFeed({ predictions }) {
  const items = predictions.flatMap(p =>
    (p.signals || []).map(s => ({ signal: s, subject: p.subject, ...signalMeta(s) }))
  )

  return (
    <div>
      <h2 style={{ fontSize: 24, fontWeight: 600, lineHeight: '32px', color: C.onSurface, marginBottom: 16 }}>
        Signal Feed
      </h2>
      <div className="glass-card rounded-xl" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16, maxHeight: 600, overflowY: 'auto' }}>
        {items.length === 0
          ? <p style={{ fontSize: 13, color: C.outline, padding: '8px 0' }}>No signals yet.</p>
          : items.map((item, i) => (
              <div key={i} className="flex gap-4" style={{ borderBottom: i < items.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none', paddingBottom: i < items.length - 1 ? 16 : 0 }}>
                <div style={{ marginTop: 2, flexShrink: 0 }}>
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: item.dot, boxShadow: item.shadow }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-start" style={{ marginBottom: 4 }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: C.onSurface, letterSpacing: '0.02em' }}>{item.label}</span>
                    <span style={{ fontSize: 12, color: C.outline, flexShrink: 0, marginLeft: 8 }}>{item.subject}</span>
                  </div>
                  <p style={{ fontSize: 12, color: C.onSurfaceVar, lineHeight: '16px' }}>{item.signal}</p>
                </div>
              </div>
            ))
        }
      </div>
    </div>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────

// ─── Pages ───────────────────────────────────────────────────────────────────

function SubjectsPage({ subjects, predictions, onDeleteSubject }) {
  const CHECK_OPTS = [{label:'1 day',val:1},{label:'3 days',val:3},{label:'1 week',val:7},{label:'2 weeks',val:14}]
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: '-0.01em', color: C.onSurface, marginBottom: 4 }}>Subjects</h1>
        <p style={{ fontSize: 16, color: C.outline }}>All monitored subjects and their configuration.</p>
      </div>
      <div className="glass-card rounded-xl" style={{ overflow: 'hidden' }}>
        {/* Header row */}
        <div className="flex items-center" style={{ padding: '10px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          {['Subject','Category','Ticker','Check After','Timeline','Active Prediction',''].map((h, i) => (
            <div key={i} style={{ fontSize: 11, fontWeight: 600, color: C.outline, letterSpacing: '0.06em', textTransform: 'uppercase',
              flex: i === 0 ? 2 : i === 5 ? 2 : 1, textAlign: i === 6 ? 'right' : 'left' }}>{h}</div>
          ))}
        </div>
        {subjects.map((s, i) => {
          const cat = CAT[s.category] || CAT.general
          const activePred = predictions.find(p => p.subject === s.name && !p.outcome)
          const dir = activePred ? (DIR[activePred.direction] || DIR.neutral) : null
          return (
            <div key={s.name} className="flex items-center"
              style={{ padding: '14px 20px', borderBottom: i < subjects.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
              <div style={{ flex: 2, fontSize: 14, fontWeight: 600, color: C.onSurface }}>{s.name}</div>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999,
                  background: `${cat.color}18`, color: cat.color, border: `1px solid ${cat.color}25` }}>{cat.label}</span>
              </div>
              <div style={{ flex: 1, fontSize: 13, color: C.outline, fontFamily: 'monospace' }}>{s.ticker || '—'}</div>
              <div style={{ flex: 1, fontSize: 13, color: C.outline }}>
                {CHECK_OPTS.find(o => o.val === s.check_after_days)?.label || `${s.check_after_days}d`}
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999,
                  background: s.timeline_mode === 'custom' ? `${C.secondary}15` : 'rgba(255,255,255,0.05)',
                  color: s.timeline_mode === 'custom' ? C.secondary : C.outline,
                  border: `1px solid ${s.timeline_mode === 'custom' ? C.secondary + '30' : 'rgba(255,255,255,0.08)'}` }}>
                  {s.timeline_mode === 'custom' ? 'Custom' : 'Auto'}
                </span>
              </div>
              <div style={{ flex: 2, fontSize: 13 }}>
                {activePred
                  ? <span style={{ color: dir.text, fontWeight: 600 }}>{dir.label} · {activePred.days_remaining}d left</span>
                  : <span style={{ color: C.outlineVar }}>No active prediction</span>}
              </div>
              <div style={{ flex: 1, textAlign: 'right' }}>
                <button onClick={() => onDeleteSubject(s.name)}
                  className="cursor-pointer hover:opacity-70 transition-opacity"
                  style={{ color: C.outline }}>
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function HistoryPage({ predictions }) {
  const history = predictions.filter(p => p.outcome && p.outcome !== 'manual')
  const [sort, setSort] = useState('date')

  const sorted = [...history].sort((a, b) => {
    if (sort === 'date')    return (b.outcome_date || '').localeCompare(a.outcome_date || '')
    if (sort === 'subject') return a.subject.localeCompare(b.subject)
    if (sort === 'outcome') return a.outcome.localeCompare(b.outcome)
    return 0
  })

  const correct   = history.filter(p => p.outcome === 'correct').length
  const accuracy  = history.length ? Math.round(correct / history.length * 100) : null

  return (
    <div>
      <div className="flex justify-between items-end" style={{ marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: '-0.01em', color: C.onSurface, marginBottom: 4 }}>History</h1>
          <p style={{ fontSize: 16, color: C.outline }}>
            {history.length} scored predictions{accuracy !== null ? ` · ${accuracy}% accuracy` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          {[{label:'Date',val:'date'},{label:'Subject',val:'subject'},{label:'Outcome',val:'outcome'}].map(o => (
            <button key={o.val} onClick={() => setSort(o.val)}
              className="cursor-pointer filter-btn"
              style={{ fontSize: 12, padding: '5px 12px', borderRadius: 8,
                background: sort === o.val ? `${C.primary}20` : 'rgba(255,255,255,0.04)',
                border: `1px solid ${sort === o.val ? C.primary + '40' : 'rgba(255,255,255,0.08)'}`,
                color: sort === o.val ? C.primary : C.outline }}>
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {history.length === 0
        ? <div className="glass-card rounded-xl flex items-center justify-center" style={{ height: 200 }}>
            <span style={{ fontSize: 14, color: C.outline }}>No scored predictions yet.</span>
          </div>
        : <div className="glass-card rounded-xl" style={{ overflow: 'hidden' }}>
            <div className="flex items-center" style={{ padding: '10px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              {['Subject','Direction','Confidence','Baseline','Final Price','Change','Date','Result'].map((h, i) => (
                <div key={i} style={{ fontSize: 11, fontWeight: 600, color: C.outline, letterSpacing: '0.06em',
                  textTransform: 'uppercase', flex: i === 0 ? 2 : 1 }}>{h}</div>
              ))}
            </div>
            {sorted.map((p, i) => {
              const dir     = DIR[p.direction] || DIR.neutral
              const correct = p.outcome === 'correct'
              const change  = p.baseline_price && p.outcome_price
                ? ((p.outcome_price - p.baseline_price) / p.baseline_price * 100).toFixed(1)
                : null
              return (
                <div key={p.id} className="flex items-center card-enter"
                  style={{ padding: '12px 20px', animationDelay: `${i * 40}ms`,
                    borderBottom: i < sorted.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
                  <div style={{ flex: 2, fontSize: 14, fontWeight: 600, color: C.onSurface }}>{p.subject}</div>
                  <div style={{ flex: 1 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: dir.text }}>{dir.label}</span>
                  </div>
                  <div style={{ flex: 1, fontSize: 12, color: C.outline, textTransform: 'capitalize' }}>{p.confidence}</div>
                  <div style={{ flex: 1, fontSize: 12, color: C.outline }}>{p.baseline_price ? `${currencySymbol(p.ticker)}${p.baseline_price}` : '—'}</div>
                  <div style={{ flex: 1, fontSize: 12, color: C.outline }}>{p.outcome_price  ? `${currencySymbol(p.ticker)}${p.outcome_price}`  : '—'}</div>
                  <div style={{ flex: 1, fontSize: 12, color: change === null ? C.outline : change >= 0 ? '#4ade80' : C.error }}>
                    {change !== null ? `${change >= 0 ? '+' : ''}${change}%` : '—'}
                  </div>
                  <div style={{ flex: 1, fontSize: 12, color: C.outline }}>{p.outcome_date || '—'}</div>
                  <div style={{ flex: 1 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 10px', borderRadius: 999,
                      background: correct ? 'rgba(74,222,128,0.1)' : `${C.error}15`,
                      color: correct ? '#4ade80' : C.error,
                      border: `1px solid ${correct ? 'rgba(74,222,128,0.25)' : C.error + '33'}` }}>
                      {correct ? 'Correct' : 'Incorrect'}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
      }
    </div>
  )
}

function Ring({ pct, size = 120, stroke = 10, color }) {
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const filled = (pct / 100) * circ
  const accColor = pct >= 60 ? C.secondary : pct < 45 ? C.error : C.primary
  const c = color || accColor
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={stroke} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={c} strokeWidth={stroke}
        strokeDasharray={`${filled} ${circ}`} strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 6px ${c}88)`, transition: 'stroke-dasharray 0.6s ease' }} />
    </svg>
  )
}

function AnalyticsPage({ predictions }) {
  const scored = predictions.filter(p => p.outcome === 'correct' || p.outcome === 'incorrect')

  if (scored.length < 20) {
    return (
      <div>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: '-0.01em', color: C.onSurface, marginBottom: 4 }}>Analytics</h1>
          <p style={{ fontSize: 16, color: C.outline }}>Performance insights across all predictions.</p>
        </div>
        <div className="glass-card rounded-xl flex items-center justify-center" style={{ height: 300 }}>
          <div className="flex flex-col items-center gap-3">
            <BookOpen size={32} style={{ color: C.outline, opacity: 0.4 }} />
            <span style={{ fontSize: 14, color: C.outline }}>Needs 20+ scored predictions.</span>
            <span style={{ fontSize: 12, color: C.outlineVar }}>Currently {scored.length} scored.</span>
          </div>
        </div>
      </div>
    )
  }

  const correct = scored.filter(p => p.outcome === 'correct')
  const totalAcc = Math.round(correct.length / scored.length * 100)
  const accColor = totalAcc >= 60 ? C.secondary : totalAcc < 45 ? C.error : C.primary

  const upCalls   = scored.filter(p => p.direction === 'up')
  const downCalls = scored.filter(p => p.direction === 'down')
  const neutCalls = scored.filter(p => p.direction === 'neutral')
  const upAcc   = upCalls.length   ? Math.round(upCalls.filter(p => p.outcome === 'correct').length   / upCalls.length   * 100) : null
  const downAcc = downCalls.length ? Math.round(downCalls.filter(p => p.outcome === 'correct').length / downCalls.length * 100) : null
  const neutAcc = neutCalls.length ? Math.round(neutCalls.filter(p => p.outcome === 'correct').length / neutCalls.length * 100) : null
  const biasFlag = upAcc !== null && downAcc !== null && Math.abs(upAcc - downAcc) > 15

  const confs = ['high','medium','low']
  const byConf = confs.map(c => {
    const g = scored.filter(p => p.confidence === c)
    return { label: c, acc: g.length ? Math.round(g.filter(p => p.outcome === 'correct').length / g.length * 100) : null, n: g.length }
  }).filter(x => x.n > 0)

  const subjects = [...new Set(scored.map(p => p.subject))]
  const bySubject = subjects.map(s => {
    const g = scored.filter(p => p.subject === s)
    const w = g.filter(p => p.outcome === 'correct').length
    return { name: s, w, l: g.length - w, acc: Math.round(w / g.length * 100), n: g.length }
  }).sort((a, b) => b.acc - a.acc)

  const sorted = [...scored].sort((a, b) => (a.date_logged || '').localeCompare(b.date_logged || ''))

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: '-0.01em', color: C.onSurface, marginBottom: 4 }}>Analytics</h1>
        <p style={{ fontSize: 16, color: C.outline }}>{scored.length} scored predictions</p>
      </div>

      {/* Row 1: Overall + Direction — single unified card */}
      <div className="glass-card rounded-xl" style={{ padding: 28, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 0 }}>
        {/* Overall ring */}
        <div className="flex flex-col items-center" style={{ minWidth: 180, paddingRight: 28 }}>
          <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            <Ring pct={totalAcc} size={130} stroke={11} />
            <div style={{ position: 'absolute', textAlign: 'center' }}>
              <div style={{ fontSize: 30, fontWeight: 800, color: accColor, lineHeight: 1 }}>{totalAcc}%</div>
              <div style={{ fontSize: 10, color: C.outline, marginTop: 2 }}>accuracy</div>
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <span style={{ fontSize: 13, color: C.secondary, fontWeight: 700 }}>{correct.length}W</span>
            <span style={{ fontSize: 13, color: C.outline, margin: '0 6px' }}>/</span>
            <span style={{ fontSize: 13, color: C.error, fontWeight: 700 }}>{scored.length - correct.length}L</span>
            <span style={{ fontSize: 12, color: C.outline, marginLeft: 6 }}>{scored.length} total</span>
          </div>
          {biasFlag && (
            <div className="flex items-center gap-2" style={{ marginTop: 10, background: `${C.error}15`,
              border: `1px solid ${C.error}33`, borderRadius: 6, padding: '5px 10px' }}>
              <AlertCircle size={11} style={{ color: C.error }} />
              <span style={{ fontSize: 11, color: C.error }}>Bearish bias</span>
            </div>
          )}
        </div>

        {/* Divider */}
        <div style={{ width: 1, alignSelf: 'stretch', background: 'rgba(255,255,255,0.08)', marginRight: 28 }} />

        {/* Direction rings */}
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 12, fontWeight: 700, color: C.outline, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 16 }}>Accuracy by Direction</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {[
              { label: 'UP',      acc: upAcc,   n: upCalls.length,   color: C.secondary },
              { label: 'DOWN',    acc: downAcc, n: downCalls.length, color: C.error     },
              { label: 'NEUTRAL', acc: neutAcc, n: neutCalls.length, color: C.outline   },
            ].map(({ label, acc, n, color }) => acc === null ? (
              <div key={label} className="flex flex-col items-center justify-center glass-card rounded-xl" style={{ padding: '16px 8px', opacity: 0.3 }}>
                <span style={{ fontSize: 12, color: C.outline }}>{label}</span>
                <span style={{ fontSize: 11, color: C.outlineVar }}>no data</span>
              </div>
            ) : (
              <div key={label} className="flex items-center gap-3 glass-card rounded-xl" style={{ padding: '14px 16px' }}>
                <div style={{ position: 'relative', display: 'inline-flex', flexShrink: 0 }}>
                  <Ring pct={acc} size={72} stroke={7} color={color} />
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontSize: 15, fontWeight: 700, color }}>{acc}%</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color }}>{label}</div>
                  <div style={{ fontSize: 11, color: C.outline }}>{n} calls</div>
                  <div style={{ marginTop: 6, height: 4, width: 60, borderRadius: 2, background: 'rgba(255,255,255,0.07)' }}>
                    <div style={{ height: '100%', width: `${acc}%`, borderRadius: 2, background: color, opacity: 0.7 }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Row 2: Subject leaderboard + Confidence */}
      <div className="grid gap-4" style={{ gridTemplateColumns: '3fr 2fr', marginBottom: 16 }}>

        {/* Subject leaderboard */}
        <div className="glass-card rounded-xl" style={{ padding: 24 }}>
          <p style={{ fontSize: 12, fontWeight: 700, color: C.outline, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 14 }}>Subject Leaderboard</p>
          <div className="flex flex-col gap-2">
            {bySubject.map((s, i) => {
              const color = s.acc >= 60 ? C.secondary : s.acc < 45 ? C.error : C.primary
              return (
                <div key={s.name} className="flex items-center gap-3">
                  <span style={{ fontSize: 11, fontWeight: 700, color: C.outlineVar, width: 20, textAlign: 'right', flexShrink: 0 }}>#{i+1}</span>
                  <span style={{ fontSize: 13, color: C.onSurfaceVar, width: 120, flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</span>
                  <div style={{ flex: 1, height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.07)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${s.acc}%`, borderRadius: 3, background: color, boxShadow: `0 0 6px ${color}55`, transition: 'width 0.5s ease' }} />
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 700, color, width: 36, textAlign: 'right', flexShrink: 0 }}>{s.acc}%</span>
                  <span style={{ fontSize: 11, color: C.outline, width: 48, flexShrink: 0 }}>{s.w}W {s.l}L</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Confidence calibration */}
        <div className="glass-card rounded-xl" style={{ padding: 24 }}>
          <p style={{ fontSize: 12, fontWeight: 700, color: C.outline, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 14 }}>Confidence Calibration</p>
          <div className="flex flex-col gap-3">
            {byConf.map(({ label, acc, n }) => {
              const color = label === 'high' ? C.primary : label === 'medium' ? C.secondary : C.outline
              return (
                <div key={label} className="flex items-center gap-3 glass-card rounded-xl" style={{ padding: '12px 14px' }}>
                  <div style={{ position: 'relative', display: 'inline-flex', flexShrink: 0 }}>
                    <Ring pct={acc} size={56} stroke={6} color={color} />
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color }}>{acc}%</span>
                    </div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color, textTransform: 'capitalize', marginBottom: 4 }}>{label} confidence</div>
                    <div style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.07)' }}>
                      <div style={{ height: '100%', width: `${acc}%`, borderRadius: 2, background: color, opacity: 0.7 }} />
                    </div>
                    <div style={{ fontSize: 11, color: C.outline, marginTop: 3 }}>{n} calls</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Row 3: Recent prediction strip */}
      <div className="glass-card rounded-xl" style={{ padding: 24 }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: C.outline, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 16 }}>Prediction History</p>
        <div className="flex flex-wrap gap-2">
          {sorted.map((p, i) => {
            const ok = p.outcome === 'correct'
            const dir = DIR[p.direction] || DIR.neutral
            return (
              <div key={i} title={`${p.subject} · ${p.direction?.toUpperCase()} · ${p.outcome}`}
                className="flex flex-col items-center gap-1 rounded-lg cursor-default"
                style={{ padding: '8px 10px', minWidth: 68,
                  background: ok ? `${C.secondary}10` : `${C.error}10`,
                  border: `1px solid ${ok ? C.secondary : C.error}2a` }}>
                <span style={{ fontSize: 9, color: C.outlineVar }}>{p.date_logged?.slice(5)}</span>
                <span style={{ fontSize: 12, fontWeight: 800, color: dir.text }}>{p.direction?.toUpperCase()}</span>
                <span style={{ fontSize: 13, color: ok ? C.secondary : C.error }}>{ok ? '✓' : '✗'}</span>
                <span style={{ fontSize: 9, color: C.outlineVar, textAlign: 'center', lineHeight: '12px', maxWidth: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.subject}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function IntelligencePage({ predictions }) {
  const items = predictions.flatMap(p =>
    (p.signals || []).map(s => ({ signal: s, subject: p.subject, direction: p.direction, ...signalMeta(s) }))
  )
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: '-0.01em', color: C.onSurface, marginBottom: 4 }}>Intelligence Feed</h1>
        <p style={{ fontSize: 16, color: C.outline }}>{items.length} signals across {predictions.length} active predictions.</p>
      </div>
      <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
        {items.map((item, i) => {
          const dir = DIR[item.direction] || DIR.neutral
          return (
            <div key={i} className="glass-card rounded-xl card-enter flex gap-4"
              style={{ padding: 20, animationDelay: `${i * 30}ms` }}>
              <div style={{ marginTop: 3, flexShrink: 0 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: item.dot, boxShadow: item.shadow }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start" style={{ marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: C.onSurface }}>{item.label}</span>
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: 11, fontWeight: 700, color: dir.text }}>{dir.label}</span>
                    <span style={{ fontSize: 11, color: C.outline }}>{item.subject}</span>
                  </div>
                </div>
                <p style={{ fontSize: 13, color: C.onSurfaceVar, lineHeight: '20px' }}>{item.signal}</p>
              </div>
            </div>
          )
        })}
        {items.length === 0 && (
          <div className="col-span-2 glass-card rounded-xl flex items-center justify-center" style={{ height: 200 }}>
            <span style={{ fontSize: 14, color: C.outline }}>No signals yet — run the pipeline first.</span>
          </div>
        )}
      </div>
    </div>
  )
}

const TIER_COLORS = { 1: '#4cd7f6', 2: '#d0bcff', 3: '#fbabff' }
const TIER_LABELS = { 1: 'T1', 2: 'T2', 3: 'T3' }

function SourcesPage({ subjects, onRefresh }) {
  const [library, setLibrary] = useState(null)
  const [expandedLib, setExpandedLib] = useState(null) // subject name with open library panel
  const [customUrl, setCustomUrl] = useState({})       // {subjectName: url}
  const [customName, setCustomName] = useState({})

  useEffect(() => {
    fetch('/api/sources/library').then(r => r.json()).then(setLibrary)
  }, [])

  async function removeSource(subjectName, sourceId) {
    await fetch(`/api/subjects/${encodeURIComponent(subjectName)}/sources/${encodeURIComponent(sourceId)}`, { method: 'DELETE' })
    onRefresh()
  }

  async function addFromLibrary(subjectName, source) {
    await fetch(`/api/subjects/${encodeURIComponent(subjectName)}/sources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(source)
    })
    setExpandedLib(null)
    onRefresh()
  }

  async function addCustom(subjectName) {
    const url = (customUrl[subjectName] || '').trim()
    const name = (customName[subjectName] || '').trim() || 'Custom'
    if (!url) return
    const id = 'custom_' + Date.now()
    await fetch(`/api/subjects/${encodeURIComponent(subjectName)}/sources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, name, url, tier: 2, region: 'global', type: 'news' })
    })
    setCustomUrl(p => ({ ...p, [subjectName]: '' }))
    setCustomName(p => ({ ...p, [subjectName]: '' }))
    onRefresh()
  }

  const allLibSources = library ? Object.values(library).flat() : []

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: '-0.01em', color: C.onSurface, marginBottom: 4 }}>Sources</h1>
        <p style={{ fontSize: 16, color: C.outline }}>Manage RSS feeds per subject. T1=official/wire, T2=financial media, T3=social.</p>
      </div>

      <div className="flex flex-col gap-4">
        {subjects.map(subj => {
          const sources = subj.sources || subj.rss_feeds?.map((u, i) => ({ id: `legacy_${i}`, name: 'RSS', url: u, tier: 2, region: 'global', type: 'news' })) || []
          const libOpen = expandedLib === subj.name
          const existingIds = new Set(sources.map(s => s.id || s))
          const addable = allLibSources.filter(s => !existingIds.has(s.id))

          return (
            <div key={subj.name} className="glass-card rounded-xl" style={{ padding: 20 }}>
              <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
                <div>
                  <span style={{ fontSize: 15, fontWeight: 700, color: C.onSurface }}>{subj.name}</span>
                  {subj.ticker && <span style={{ fontSize: 12, color: C.outline, marginLeft: 8 }}>{subj.ticker}</span>}
                </div>
                <span style={{ fontSize: 12, color: C.outline }}>{sources.length} source{sources.length !== 1 ? 's' : ''}</span>
              </div>

              {/* Source list */}
              <div className="flex flex-col gap-2" style={{ marginBottom: 14 }}>
                {sources.map(src => {
                  const tier = src.tier || 2
                  return (
                    <div key={src.id} className="flex items-center gap-3 rounded-lg"
                      style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.04)' }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: TIER_COLORS[tier],
                        background: `${TIER_COLORS[tier]}18`, borderRadius: 4, padding: '2px 6px' }}>
                        {TIER_LABELS[tier]}
                      </span>
                      {src.region && (
                        <span style={{ fontSize: 11, color: C.outline, background: 'rgba(255,255,255,0.06)',
                          borderRadius: 4, padding: '2px 6px' }}>
                          {src.region}
                        </span>
                      )}
                      <span style={{ fontSize: 13, color: C.onSurfaceVar, flex: 1 }}>{src.name}</span>
                      <a href={src.url} target="_blank" rel="noreferrer" style={{ color: C.outline, opacity: 0.5 }}>
                        <ExternalLink size={13} />
                      </a>
                      <button onClick={() => removeSource(subj.name, src.id)}
                        className="cursor-pointer hover:opacity-80" style={{ color: C.error, opacity: 0.6 }}>
                        <X size={14} />
                      </button>
                    </div>
                  )
                })}
              </div>

              {/* Add controls */}
              <div className="flex gap-2 flex-wrap">
                <button onClick={() => setExpandedLib(libOpen ? null : subj.name)}
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  style={{ fontSize: 12, color: C.secondary, background: `${C.secondary}18`,
                    border: `1px solid ${C.secondary}33`, borderRadius: 6, padding: '5px 12px', fontWeight: 600 }}>
                  + From Library
                </button>
                <input value={customUrl[subj.name] || ''} placeholder="Custom RSS URL"
                  onChange={e => setCustomUrl(p => ({ ...p, [subj.name]: e.target.value }))}
                  style={{ fontSize: 12, flex: 1, minWidth: 180, background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '5px 10px', color: C.onSurface }} />
                <input value={customName[subj.name] || ''} placeholder="Name (optional)"
                  onChange={e => setCustomName(p => ({ ...p, [subj.name]: e.target.value }))}
                  style={{ fontSize: 12, width: 130, background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '5px 10px', color: C.onSurface }} />
                <button onClick={() => addCustom(subj.name)}
                  className="cursor-pointer hover:opacity-80"
                  style={{ fontSize: 12, color: C.primary, background: `${C.primary}18`,
                    border: `1px solid ${C.primary}33`, borderRadius: 6, padding: '5px 12px', fontWeight: 600 }}>
                  Add
                </button>
              </div>

              {/* Library panel */}
              {libOpen && (
                <div className="rounded-xl" style={{ marginTop: 12, padding: 14, background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.08)' }}>
                  <p style={{ fontSize: 12, color: C.outline, marginBottom: 10 }}>Pre-vetted feeds — click to add</p>
                  {Object.entries(library || {}).map(([region, feeds]) => {
                    const available = feeds.filter(s => !existingIds.has(s.id))
                    if (!available.length) return null
                    return (
                      <div key={region} style={{ marginBottom: 10 }}>
                        <p style={{ fontSize: 11, color: C.outlineVar, fontWeight: 700, letterSpacing: '0.08em',
                          textTransform: 'uppercase', marginBottom: 6 }}>{region}</p>
                        <div className="flex flex-wrap gap-2">
                          {available.map(src => (
                            <button key={src.id} onClick={() => addFromLibrary(subj.name, src)}
                              className="cursor-pointer hover:opacity-80 transition-opacity flex items-center gap-2"
                              style={{ fontSize: 12, color: C.onSurfaceVar, background: 'rgba(255,255,255,0.06)',
                                border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '5px 10px' }}>
                              <span style={{ fontSize: 10, fontWeight: 700, color: TIER_COLORS[src.tier],
                                background: `${TIER_COLORS[src.tier]}18`, borderRadius: 3, padding: '1px 4px' }}>
                                T{src.tier}
                              </span>
                              {src.name}
                              <Plus size={11} />
                            </button>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function PageShell({ page, predictions, subjects, onDeleteSubject, onRefresh }) {
  const active = predictions.filter(p => !p.outcome)
  if (page === 'subjects')     return <SubjectsPage subjects={subjects} predictions={predictions} onDeleteSubject={onDeleteSubject} />
  if (page === 'history')      return <HistoryPage predictions={predictions} />
  if (page === 'analytics')    return <AnalyticsPage predictions={predictions} />
  if (page === 'intelligence') return <IntelligencePage predictions={active} />
  if (page === 'sources')      return <SourcesPage subjects={subjects} onRefresh={onRefresh} />
  return null
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [predictions, setPredictions] = useState([])
  const [subjects,    setSubjects]    = useState([])
  const [stats,       setStats]       = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)
  const [expandedId,  setExpandedId]  = useState(null)
  const [page,        setPage]        = useState('overview')
  const [showModal,   setShowModal]   = useState(false)
  const [newName,     setNewName]     = useState('')
  const [newTicker,   setNewTicker]   = useState('')
  const [checkDays,     setCheckDays]     = useState(7)
  const [timelineMode,  setTimelineMode]  = useState('auto')
  const [running,     setRunning]     = useState(false)
  const [filterDir,   setFilterDir]   = useState(null)
  const [filterConf,  setFilterConf]  = useState(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const clock = useClock()

  const fetchData = async () => {
    try {
      setError(null)
      const [pr, sr, subr] = await Promise.all([fetch('/api/predictions'), fetch('/api/stats'), fetch('/api/subjects')])
      if (!pr.ok || !sr.ok) throw new Error()
      setPredictions(await pr.json())
      setStats(await sr.json())
      setSubjects(await subr.json())
    } catch {
      setError('Cannot reach API — run: python3 -m uvicorn api:app --port 8000')
    } finally {
      setLoading(false)
    }
  }

  const handleDiscard = async (id) => {
    await fetch(`/api/predictions/${id}`, { method: 'DELETE' })
    fetchData()
  }

  const handleScore = async (id, outcome) => {
    await fetch(`/api/predictions/${id}/score`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outcome }),
    })
    fetchData()
  }

  const handleAddSubject = async () => {
    if (!newName.trim()) return
    setRunning(true)
    setShowModal(false)
    await fetch('/api/subjects', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName.trim(), ticker: newTicker.trim(), check_after_days: checkDays, timeline_mode: timelineMode }),
    })
    setNewName(''); setNewTicker(''); setCheckDays(7); setTimelineMode('auto')
    // pipeline runs in background ~30s, poll until new prediction appears
    const before = predictions.length
    const poll = setInterval(async () => {
      const r = await fetch('/api/predictions')
      const data = await r.json()
      if (data.length > before) { setPredictions(data); setRunning(false); clearInterval(poll) }
    }, 5000)
    setTimeout(() => { clearInterval(poll); setRunning(false); fetchData() }, 90000)
  }

  const handleRunAll = async () => {
    setRunning(true)
    await fetch('/api/run', { method: 'POST' })
    const before = predictions.length
    const poll = setInterval(async () => {
      const r = await fetch('/api/predictions')
      const data = await r.json()
      if (data.length > before) { setPredictions(data); setRunning(false); clearInterval(poll) }
    }, 5000)
    setTimeout(() => { clearInterval(poll); setRunning(false); fetchData() }, 120000)
  }

  useEffect(() => {
    fetchData()
    const i = setInterval(fetchData, 60000)
    return () => clearInterval(i)
  }, [])

  const active  = predictions.filter(p => !p.outcome)
  const history = predictions.filter(p => p.outcome)
  const filtered = active
    .filter(p => !filterDir  || p.direction  === filterDir)
    .filter(p => !filterConf || p.confidence === filterConf)

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: C.surface, fontFamily: "'Geist', system-ui, sans-serif" }}>

      {/* ── Top nav ── */}
      <nav className="fixed top-0 w-full z-50 flex justify-between items-center"
        style={{
          height: 64, paddingLeft: 48, paddingRight: 48,
          background: 'rgba(19,19,20,0.6)', backdropFilter: 'blur(24px)',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 0 20px rgba(208,188,255,0.1)'
        }}>
        <div className="flex items-center gap-10">
          <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.02em', color: C.primary }}>
            World State Engine
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: C.primary, borderBottom: `2px solid ${C.primary}`, paddingBottom: 4 }}>
            Global Dashboard
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span style={{ fontFamily: 'monospace', fontSize: 13, color: C.outline }}>{clock}</span>
          <button onClick={fetchData} className="cursor-pointer transition-colors hover:opacity-80"
            style={{ color: C.outline }}>
            <Bell size={22} />
          </button>
          <div style={{ width: 32, height: 32, borderRadius: '50%', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.2)', background: `linear-gradient(135deg, ${C.primary}, ${C.secondary})`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <User size={16} color="#fff" />
          </div>
        </div>
      </nav>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden" style={{ paddingTop: 64 }}>

        {/* Sidebar */}
        <aside className="hidden md:flex flex-col fixed left-0 top-0 h-full"
          style={{
            width: 256, paddingTop: 80, paddingBottom: 24,
            paddingLeft: 16, paddingRight: 16,
            background: 'rgba(14,14,15,0.6)', backdropFilter: 'blur(32px)',
            borderRight: '1px solid rgba(255,255,255,0.1)', zIndex: 40
          }}>
          <div className="flex flex-col gap-1 flex-1">
            {[
              { id: 'overview',    label: 'Overview',    icon: LayoutDashboard },
              { id: 'subjects',    label: 'Subjects',    icon: Settings2 },
              { id: 'sources',     label: 'Sources',     icon: Database },
              { id: 'history',     label: 'History',     icon: History },
              { id: 'analytics',   label: 'Analytics',   icon: BookOpen },
              { id: 'intelligence',label: 'Intelligence', icon: Rss },
            ].map(({ id, label, icon: Icon }) => {
              const active = page === id
              return (
                <button key={id} onClick={() => setPage(id)}
                  className="flex items-center gap-4 rounded-lg w-full cursor-pointer transition-all duration-150"
                  style={{
                    padding: '8px 16px', textAlign: 'left',
                    background: active ? `${C.secondary}1a` : 'transparent',
                    color: active ? C.secondary : C.outline,
                    fontWeight: active ? 700 : 400,
                  }}>
                  <Icon size={18} />
                  <span style={{ fontSize: 14, letterSpacing: '0.02em' }}>{label}</span>
                </button>
              )
            })}
          </div>

        </aside>

        {/* Main */}
        <main className="flex-1 overflow-y-auto" style={{ marginLeft: 256, padding: 32, paddingTop: 32 }}>

        {page !== 'overview' && (
          <PageShell
            page={page}
            predictions={predictions}
            subjects={subjects}
            onRefresh={fetchData}
            onDeleteSubject={async (name) => {
              const match = predictions.find(p => p.subject === name && !p.outcome)
              if (match) {
                await fetch(`/api/predictions/${match.id}`, { method: 'DELETE' })
              } else {
                const subs = subjects.filter(s => s.name !== name)
                await fetch('/api/subjects', { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(subs) })
              }
              fetchData()
            }}
          />
        )}

        {page === 'overview' && <>
          {/* Page header */}
          <div className="flex justify-between items-end" style={{ marginBottom: 24 }}>
            <div>
              <h1 style={{ fontSize: 32, fontWeight: 600, letterSpacing: '-0.01em', color: C.onSurface, marginBottom: 4 }}>
                Probability Overview
              </h1>
              <p style={{ fontSize: 16, color: C.outline }}>System-wide performance and engagement metrics.</p>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2" style={{
              background: `${C.error}10`, border: `1px solid ${C.error}33`,
              borderRadius: 12, padding: '10px 16px', marginBottom: 24,
              fontSize: 13, color: C.error
            }}>
              <AlertCircle size={14} />{error}
            </div>
          )}

          {/* Stats */}
          <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 32 }}>
            <StatCard icon={TrendingUp}  iconColor={C.primary}   glowClass="neon-glow-purple"
              badge={stats?.total ? '+12.5%' : ''} accent={C.primary}
              value={stats?.total}   label="Total Events" />
            <StatCard icon={Activity}    iconColor={C.secondary} glowClass="neon-glow-cyan"
              badge="Active"
              value={stats?.pending} label="Pending Scrutiny" />
            <StatCard icon={CheckCircle2} iconColor={C.tertiary}  glowClass="neon-glow-pink"
              badge="Scored"
              value={stats?.scored}  label="Recently Finalized" />
            <ConfidenceStatCard predictions={predictions} />
          </div>

          {/* Running banner */}
          {running && (
            <div className="flex items-center gap-3" style={{
              background: `${C.primary}10`, border: `1px solid ${C.primary}30`,
              borderRadius: 12, padding: '10px 16px', marginBottom: 24,
              fontSize: 13, color: C.primary
            }}>
              <Loader2 size={14} className="animate-spin" />
              Generating predictions — this takes ~30s. Page will update automatically.
            </div>
          )}

          {/* Predictions + Signal Feed */}
          <div className="grid gap-6" style={{ gridTemplateColumns: '2fr 1fr' }}>

            {/* Left: active + history */}
            <div className="flex flex-col gap-8">

              {/* Active */}
              <div>
                <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
                  <h2 style={{ fontSize: 24, fontWeight: 600, color: C.onSurface }}>Active Predictions</h2>
                  <div className="flex gap-2">
                    <button onClick={handleRunAll} disabled={running}
                      className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
                      style={{ fontSize: 13, color: C.secondary, background: `${C.secondary}15`, border: `1px solid ${C.secondary}30`, borderRadius: 8, padding: '6px 14px' }}>
                      {running ? <Loader2 size={13} className="animate-spin" /> : '↻'} Run All
                    </button>
                    <button onClick={() => setShowModal(true)}
                      className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
                      style={{ fontSize: 13, color: C.primary, background: `${C.primary}15`, border: `1px solid ${C.primary}30`, borderRadius: 8, padding: '6px 14px' }}>
                      <Plus size={13} /> Add Subject
                    </button>
                  </div>
                </div>

                {/* Filters */}
                {active.length > 0 && (
                  <div className="flex items-center gap-2" style={{ marginBottom: 16, flexWrap: 'wrap' }}>
                    {[...new Set(active.map(p => p.direction).filter(Boolean))].map(d => (
                      <button key={d} onClick={() => setFilterDir(prev => prev === d ? null : d)}
                        className="cursor-pointer filter-btn"
                        style={{
                          fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 999,
                          background: filterDir === d ? `${DIR[d].text}20` : 'rgba(255,255,255,0.04)',
                          border: `1px solid ${filterDir === d ? DIR[d].text + '60' : 'rgba(255,255,255,0.08)'}`,
                          color: filterDir === d ? DIR[d].text : C.outline,
                        }}>{DIR[d].label}</button>
                    ))}
                    <div style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.08)' }} />
                    {['high','medium','low'].map(c => (
                      <button key={c} onClick={() => setFilterConf(prev => prev === c ? null : c)}
                        className="cursor-pointer filter-btn"
                        style={{
                          fontSize: 11, padding: '3px 10px', borderRadius: 999,
                          background: filterConf === c ? `${C.primary}20` : 'rgba(255,255,255,0.04)',
                          border: `1px solid ${filterConf === c ? C.primary + '60' : 'rgba(255,255,255,0.08)'}`,
                          color: filterConf === c ? C.primary : C.outline,
                        }}>{c.charAt(0).toUpperCase() + c.slice(1)} conf</button>
                    ))}
                    {(filterDir || filterConf) && (
                      <button onClick={() => { setFilterDir(null); setFilterConf(null) }}
                        className="cursor-pointer hover:opacity-70"
                        style={{ fontSize: 11, color: C.outline, padding: '3px 8px' }}>✕ clear</button>
                    )}
                  </div>
                )}

                {loading ? (
                  <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
                    {[0,1,2].map(i => <div key={i} className="glass-card rounded-xl animate-pulse" style={{ height: 180 }} />)}
                  </div>
                ) : active.length === 0 ? (
                  <div className="glass-card rounded-xl flex flex-col items-center justify-center gap-3" style={{ height: 180 }}>
                    <span style={{ fontSize: 14, color: C.outline }}>No active predictions.</span>
                    <button onClick={() => setShowModal(true)}
                      className="flex items-center gap-2 cursor-pointer hover:opacity-80"
                      style={{ fontSize: 13, color: C.primary, background: `${C.primary}15`, border: `1px solid ${C.primary}30`, borderRadius: 8, padding: '6px 14px' }}>
                      <Plus size={13} /> Add Subject
                    </button>
                  </div>
                ) : filtered.length === 0 ? (
                  <div className="glass-card rounded-xl flex items-center justify-center" style={{ height: 120 }}>
                    <span style={{ fontSize: 14, color: C.outline }}>No predictions match filters.</span>
                  </div>
                ) : (
                  <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr', alignItems: 'start' }}>
                    {filtered.map((p, i) => (
                      <PredictionCard key={p.id} p={p}
                        index={i}
                        expanded={expandedId === p.id}
                        onToggle={() => setExpandedId(prev => prev === p.id ? null : p.id)}
                        onScore={handleScore}
                        onDiscard={handleDiscard}
                        wide={filtered.length % 2 !== 0 && i === filtered.length - 1}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* History */}
              {history.length > 0 && (
                <div>
                  <button
                    onClick={() => setHistoryOpen(o => !o)}
                    className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity w-full"
                    style={{ marginBottom: historyOpen ? 12 : 0 }}>
                    <h2 style={{ fontSize: 20, fontWeight: 600, color: C.onSurface }}>History</h2>
                    <span style={{ fontSize: 12, color: C.outline, background: 'rgba(255,255,255,0.06)', borderRadius: 999, padding: '2px 8px' }}>{history.length}</span>
                    <span style={{ fontSize: 14, color: C.outline, marginLeft: 'auto' }}>{historyOpen ? '▲' : '▼'}</span>
                  </button>
                  {historyOpen && (
                    <div className="glass-card rounded-xl" style={{ overflow: 'hidden' }}>
                      {history.map((p, i) => {
                        const dir = DIR[p.direction] || DIR.neutral
                        const correct = p.outcome === 'correct'
                        return (
                          <div key={p.id} className="flex items-center justify-between"
                            style={{ padding: '12px 20px', borderBottom: i < history.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
                            <div className="flex items-center gap-3">
                              <span style={{ fontSize: 13, fontWeight: 600, color: C.onSurface }}>{p.subject}</span>
                              <span style={{ fontSize: 11, fontWeight: 700, color: dir.text }}>{dir.label}</span>
                            </div>
                            <div className="flex items-center gap-4">
                              <span style={{ fontSize: 11, color: C.outline }}>{p.outcome_date || p.check_date}</span>
                              <span style={{
                                fontSize: 11, fontWeight: 600, padding: '2px 10px', borderRadius: 999,
                                background: correct ? 'rgba(74,222,128,0.1)' : `${C.error}15`,
                                color: correct ? '#4ade80' : C.error,
                                border: `1px solid ${correct ? 'rgba(74,222,128,0.25)' : C.error + '33'}`
                              }}>{correct ? 'Correct' : 'Incorrect'}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right: signal feed — only active signals */}
            <SignalFeed predictions={active} />

          </div>

          {/* Add Subject Modal */}
          {showModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center"
              style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}
              onClick={() => setShowModal(false)}>
              <div className="glass-card rounded-2xl" style={{ width: 400, padding: 32 }}
                onClick={e => e.stopPropagation()}>
                <div className="flex justify-between items-center" style={{ marginBottom: 24 }}>
                  <h3 style={{ fontSize: 18, fontWeight: 700, color: C.onSurface }}>Add Subject</h3>
                  <button onClick={() => setShowModal(false)} className="cursor-pointer hover:opacity-70" style={{ color: C.outline }}>
                    <X size={18} />
                  </button>
                </div>
                <div className="flex flex-col gap-4">
                  <div>
                    <label style={{ fontSize: 12, color: C.outline, display: 'block', marginBottom: 6 }}>Subject Name *</label>
                    <input value={newName} onChange={e => setNewName(e.target.value)}
                      placeholder="e.g. NVIDIA Stock"
                      style={{
                        width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 14,
                        background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)',
                        color: C.onSurface, outline: 'none'
                      }} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: C.outline, display: 'block', marginBottom: 6 }}>Ticker (optional)</label>
                    <input value={newTicker} onChange={e => setNewTicker(e.target.value)}
                      placeholder="e.g. NVDA"
                      style={{
                        width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 14,
                        background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)',
                        color: C.onSurface, outline: 'none'
                      }} />
                    <p style={{ fontSize: 11, color: C.outline, marginTop: 6 }}>
                      Without a ticker, scoring is manual. With one, live price and auto-baseline are available.
                    </p>
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: C.outline, display: 'block', marginBottom: 8 }}>Timeline</label>
                    <div className="flex gap-2" style={{ marginBottom: 10 }}>
                      {[{label: 'Auto', val: 'auto'}, {label: 'Custom', val: 'custom'}].map(opt => (
                        <button key={opt.val} onClick={() => setTimelineMode(opt.val)}
                          className="flex-1 cursor-pointer hover:opacity-80 transition-opacity"
                          style={{
                            padding: '8px 0', borderRadius: 8, fontSize: 13, fontWeight: 500,
                            background: timelineMode === opt.val ? `${C.primary}20` : 'rgba(255,255,255,0.04)',
                            border: `1px solid ${timelineMode === opt.val ? C.primary + '50' : 'rgba(255,255,255,0.1)'}`,
                            color: timelineMode === opt.val ? C.primary : C.outline,
                          }}>{opt.label}</button>
                      ))}
                    </div>
                    {timelineMode === 'auto'
                      ? <p style={{ fontSize: 11, color: C.outline }}>Model picks the check date based on its predicted timeframe.</p>
                      : <>
                          <div className="flex gap-2">
                            {[{label: '1 day', val: 1}, {label: '3 days', val: 3}, {label: '1 week', val: 7}, {label: '2 weeks', val: 14}].map(opt => (
                              <button key={opt.val} onClick={() => setCheckDays(opt.val)}
                                className="flex-1 cursor-pointer hover:opacity-80 transition-opacity"
                                style={{
                                  padding: '7px 0', borderRadius: 8, fontSize: 12,
                                  background: checkDays === opt.val ? `${C.secondary}20` : 'rgba(255,255,255,0.04)',
                                  border: `1px solid ${checkDays === opt.val ? C.secondary + '50' : 'rgba(255,255,255,0.1)'}`,
                                  color: checkDays === opt.val ? C.secondary : C.outline,
                                }}>{opt.label}</button>
                            ))}
                          </div>
                          <p style={{ fontSize: 11, color: C.outline, marginTop: 6 }}>Model will focus signals on this window. Short timelines may yield lower confidence.</p>
                        </>
                    }
                  </div>
                  <button onClick={handleAddSubject} disabled={!newName.trim()}
                    className="cursor-pointer hover:opacity-80 transition-opacity"
                    style={{
                      marginTop: 8, padding: '12px 0', borderRadius: 8, fontSize: 14, fontWeight: 600,
                      background: newName.trim() ? `${C.primary}20` : 'rgba(255,255,255,0.05)',
                      border: `1px solid ${newName.trim() ? C.primary + '50' : 'rgba(255,255,255,0.1)'}`,
                      color: newName.trim() ? C.primary : C.outline
                    }}>
                    Add &amp; Generate Prediction
                  </button>
                </div>
              </div>
            </div>
          )}
        </>}
        </main>
      </div>


    </div>
  )
}
