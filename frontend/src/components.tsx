import { useEffect, type ReactNode } from 'react'
import { X, type LucideIcon } from 'lucide-react'

type Tone = 'green' | 'amber' | 'red' | 'neutral' | 'blue'

const STATUS_TONES: Record<string, Tone> = {
  Pass: 'green',
  Normal: 'green',
  Completed: 'green',
  approved: 'green',
  Hold: 'red',
  Open: 'amber',
  Review: 'amber',
  pending: 'amber',
}

export function ProcessSchematic() {
  return (
    <svg className="lattice" viewBox="0 0 585 340" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="pipeGlow" x1="0" y1="0" x2="585" y2="340">
          <stop stopColor="#838383" stopOpacity=".08" />
          <stop offset=".6" stopColor="#CBCBCB" stopOpacity=".55" />
          <stop offset="1" stopColor="#BCBCBC" stopOpacity=".35" />
        </linearGradient>
        <radialGradient id="plantHalo">
          <stop stopColor="#BCBCBC" stopOpacity=".15" />
          <stop offset="1" stopColor="#BCBCBC" stopOpacity="0" />
        </radialGradient>
      </defs>
      <ellipse cx="345" cy="175" rx="250" ry="160" fill="url(#plantHalo)" />
      {Array.from({ length: 10 }, (_, i) => (
        <line
          key={`gridv${i}`}
          x1={i * 65}
          y1="10"
          x2={i * 65}
          y2="335"
          stroke="#929292"
          strokeOpacity=".12"
          strokeDasharray="3 7"
        />
      ))}
      {Array.from({ length: 6 }, (_, i) => (
        <line
          key={`gridh${i}`}
          x1="12"
          y1={i * 62 + 22}
          x2="570"
          y2={i * 62 + 22}
          stroke="#929292"
          strokeOpacity=".12"
          strokeDasharray="3 7"
        />
      ))}
      {/* process piping, pump, control valve and pressure vessel symbols */}
      <path
        d="M20 214 H110 M180 214 H291 M340 214 H434"
        stroke="url(#pipeGlow)"
        strokeWidth="7"
        strokeLinecap="round"
      />
      <path
        d="M20 214 H110 M180 214 H291 M340 214 H434"
        stroke="#D1D1D1"
        strokeOpacity=".18"
        strokeWidth="2"
      />
      <circle cx="145" cy="214" r="35" stroke="#D5D5D5" strokeOpacity=".75" strokeWidth="3" />
      <circle cx="145" cy="214" r="8" fill="#BCBCBC" fillOpacity=".8" />
      <path
        d="M145 206l18 -13 -3 23M153 217l-8 21 -12 -20M138 215l-19 -14 24 -4"
        stroke="#D5D5D5"
        strokeOpacity=".65"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <path
        d="M291 192 L341 235 L341 192 L291 235 Z"
        stroke="#D0D0D0"
        strokeWidth="3"
        strokeOpacity=".75"
      />
      <path d="M315 192 V167 M299 167 H333" stroke="#D0D0D0" strokeOpacity=".65" strokeWidth="3" />
      <path
        d="M434 119 Q434 106 467 106 H505 Q538 106 538 119 V250 Q538 268 505 268 H467 Q434 268 434 250 Z"
        fill="#303030"
        fillOpacity=".3"
        stroke="#D3D3D3"
        strokeOpacity=".65"
        strokeWidth="3"
      />
      <path d="M436 133 H537 M436 246 H537" stroke="#BCBCBC" strokeOpacity=".5" strokeWidth="2" />
      <path
        d="M486 106 V60 H548 M486 268 V296 H544"
        stroke="#D1D1D1"
        strokeOpacity=".38"
        strokeWidth="4"
      />
      <g fill="#D0D0D0" fontSize="13" fontFamily="monospace" opacity=".7">
        <text x="109" y="166">
          P-204
        </text>
        <text x="281" y="145">
          CV-310
        </text>
        <text x="454" y="92">
          PV-120
        </text>
      </g>
      <circle cx="20" cy="214" r="5" fill="#BCBCBC" opacity=".5" />
      <circle cx="548" cy="60" r="5" fill="#BCBCBC" opacity=".5" />
    </svg>
  )
}
export function Pill({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}
export function StatusPill({ status }: { status: string }) {
  return (
    <Pill tone={STATUS_TONES[status] ?? 'neutral'}>
      <span className="tiny-dot" />
      {status}
    </Pill>
  )
}
export function TextButton({
  children,
  onClick,
  outline = false,
  disabled = false,
}: {
  children: ReactNode
  onClick: () => void
  outline?: boolean
  disabled?: boolean
}) {
  return (
    <button
      className={outline ? 'btn-outline' : 'btn-primary'}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}
export function SectionTitle({
  eyebrow,
  title,
  subtitle,
  action,
}: {
  eyebrow: string
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div className="section-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {action && <div className="section-action">{action}</div>}
    </div>
  )
}
export function StatCard({
  title,
  value,
  icon: Icon,
  footer,
}: {
  title: string
  value: string | number
  icon: LucideIcon
  footer: string
}) {
  return (
    <div className="metric-card">
      <div className="metric-card-top">
        <span>{title}</span>
        <Icon size={18} />
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-footer">
        <span className="online-dot" />
        {footer}
      </div>
    </div>
  )
}
export function Overlay({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string
  subtitle?: string
  onClose: () => void
  children: ReactNode
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div
      className="overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="drawer">
        <div className="drawer-head">
          <div>
            <div className="eyebrow">DETAIL VIEW</div>
            <h2>{title}</h2>
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close detail">
            <X size={19} />
          </button>
        </div>
        <div className="drawer-body">{children}</div>
      </div>
    </div>
  )
}
export function Empty({
  title,
  description,
  icon: Icon,
}: {
  title: string
  description: string
  icon: LucideIcon
}) {
  return (
    <div className="empty">
      <Icon size={30} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  )
}
export function TableShell({ children }: { children: ReactNode }) {
  return (
    <div className="table-scroll">
      <table className="data-table">{children}</table>
    </div>
  )
}
