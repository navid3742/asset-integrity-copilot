import type {
  ChatResult,
  AssetRecord,
  DocItem,
  Inspection,
  Maintenance,
  Incident,
  Message,
  Report,
  Stats,
} from './types'
const PASSWORD_KEY = 'asset-integrity-copilot-demo-access'
export function savePassword(p: string) {
  sessionStorage.setItem(PASSWORD_KEY, p)
}
export function clearPassword() {
  sessionStorage.removeItem(PASSWORD_KEY)
}
export function hasPassword() {
  return Boolean(sessionStorage.getItem(PASSWORD_KEY))
}
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(sessionStorage.getItem(PASSWORD_KEY)
          ? { 'X-Demo-Key': sessionStorage.getItem(PASSWORD_KEY)! }
          : {}),
        ...(options?.headers || {}),
      },
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the backend. Start FastAPI on port 8000.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(
      response.status,
      typeof body.detail === 'string' ? body.detail : 'Request failed',
    )
  }
  return response.json() as Promise<T>
}
export const api = {
  status: () => request<Stats>('/status'),
  documents: () => request<DocItem[]>('/documents'),
  document: (id: string) => request<DocItem>(`/documents/${encodeURIComponent(id)}`),
  assets: (query = '') => request<AssetRecord[]>(`/assets?q=${encodeURIComponent(query)}`),
  asset: (id: string) => request<AssetRecord>(`/assets/${encodeURIComponent(id)}`),
  history: (id: string) =>
    request<{ inspections: Inspection[]; maintenance: Maintenance[]; incidents: Incident[] }>(
      `/assets/${encodeURIComponent(id)}/history`,
    ),
  reports: () => request<Report[]>('/reports'),
  draft: (id: string) =>
    request<Report>('/reports/draft', { method: 'POST', body: JSON.stringify({ asset_id: id }) }),
  approve: (id: string) =>
    request<Report>(`/reports/${encodeURIComponent(id)}/approve`, {
      method: 'POST',
      body: JSON.stringify({ confirmation: 'I_REVIEWED_THIS_DEMO_REPORT' }),
    }),
  chat: (question: string, history: Message[]) =>
    request<ChatResult>('/chat', {
      method: 'POST',
      body: JSON.stringify({
        question,
        history: history
          .filter((m) => ['assistant', 'user'].includes(m.role))
          .slice(-6)
          .map((m) => ({ role: m.role, content: m.content })),
      }),
    }),
}
