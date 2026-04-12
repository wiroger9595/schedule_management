const BASE = '/api/admin'

function getKey(): string {
  return localStorage.getItem('admin_key') || ''
}

async function req<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(BASE + path, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  }
  const res = await fetch(url.toString(), {
    headers: { 'X-Admin-Key': getKey() },
  })
  if (res.status === 403) throw new Error('FORBIDDEN')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  stats: () => req<Stats>('/stats'),
  users: (page: number, q: string, name?: string, email?: string, status?: string, createdFrom?: string, createdTo?: string) => 
    req<PagedResult<UserRow>>('/users', { 
      page, q,
      ...(name ? { name } : {}),
      ...(email ? { email } : {}),
      ...(status ? { status } : {}),
      ...(createdFrom ? { created_from: createdFrom } : {}),
      ...(createdTo ? { created_to: createdTo } : {}),
    }),
  schedules: (page: number, q: string, status: string, dateFrom: string, dateTo: string, createdFrom?: string, createdTo?: string) =>
    req<PagedResult<ScheduleRow>>('/schedules', {
      page, q,
      ...(status ? { status } : {}),
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
      ...(createdFrom ? { created_from: createdFrom } : {}),
      ...(createdTo ? { created_to: createdTo } : {}),
    }),
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface Stats {
  users: { total: number; new_this_week: number; new_this_month: number }
  schedules: { total: number; new_this_week: number; status_breakdown: Record<string, number> }
  contacts: { total: number }
  attends: { total: number }
  charts: {
    daily_users: { date: string; count: number }[]
    daily_schedules: { date: string; count: number }[]
  }
}

export interface UserRow {
  user_id: string
  full_name: string | null
  email: string | null
  status: string
  language: string | null
  created_at: string | null
}

export interface ScheduleRow {
  schedule_id: string
  title: string
  user_id: string
  status: string
  meeting_location: string | null
  meeting_start_time: string | null
  created_at: string | null
}

export interface PagedResult<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}
