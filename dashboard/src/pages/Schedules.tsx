import { useEffect, useState } from 'react'
import { api, ScheduleRow } from '../api'
import { Search, X } from 'lucide-react'

const PAGE_SIZE = 20

const STATUS_OPTIONS = [
  { value: '', label: '全部狀態' },
  { value: 'PD', label: '待確認' },
  { value: 'AT', label: '已接受/進行中' },
  { value: 'NG', label: '已拒絕' },
  { value: 'CS', label: '即將到來' },
  { value: 'CL', label: '取消' },
  { value: 'NA', label: '未出席' },
]

const STATUS_COLOR: Record<string, string> = {
  PD: 'bg-yellow-100 text-yellow-700',
  AT: 'bg-green-100 text-green-700',
  NG: 'bg-red-100 text-red-600',
  NA: 'bg-gray-100 text-gray-500',
  CL: 'bg-red-100 text-red-500',
  CS: 'bg-purple-100 text-purple-700',
}

export default function Schedules() {
  const [items, setItems] = useState<ScheduleRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)

  // Filter state (applied)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [createdFrom, setCreatedFrom] = useState('')
  const [createdTo, setCreatedTo] = useState('')

  // Input state (pending)
  const [inputQ, setInputQ] = useState('')
  const [inputStatus, setInputStatus] = useState('')
  const [inputDateFrom, setInputDateFrom] = useState('')
  const [inputDateTo, setInputDateTo] = useState('')
  const [inputCreatedFrom, setInputCreatedFrom] = useState('')
  const [inputCreatedTo, setInputCreatedTo] = useState('')

  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.schedules(page, q, status, dateFrom, dateTo, createdFrom, createdTo)
      .then(r => { setItems(r.items); setTotal(r.total) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [page, q, status, dateFrom, dateTo, createdFrom, createdTo])

  function applyFilters() {
    setQ(inputQ)
    setStatus(inputStatus)
    setDateFrom(inputDateFrom)
    setDateTo(inputDateTo)
    setCreatedFrom(inputCreatedFrom)
    setCreatedTo(inputCreatedTo)
    setPage(1)
  }

  function resetFilters() {
    setInputQ(''); setInputStatus(''); setInputDateFrom(''); setInputDateTo(''); setInputCreatedFrom(''); setInputCreatedTo('')
    setQ(''); setStatus(''); setDateFrom(''); setDateTo(''); setCreatedFrom(''); setCreatedTo('')
    setPage(1)
  }

  const hasFilter = q || status || dateFrom || dateTo || createdFrom || createdTo
  const totalPages = Math.ceil(total / PAGE_SIZE)

  function fmtTime(iso: string | null) {
    if (!iso) return '—'
    const d = new Date(iso)
    return `${d.getFullYear()}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
  }

  function fmtDate(iso: string | null) {
    if (!iso) return '—'
    const d = new Date(iso)
    return `${d.getFullYear()}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')}`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">行程管理</h1>
        <span className="text-gray-500 text-sm">共 {total.toLocaleString()} 筆</span>
      </div>

      {/* Filter bar */}
      <div className="bg-white rounded-2xl shadow-sm p-5 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">

          {/* Title search */}
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              value={inputQ}
              onChange={e => setInputQ(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && applyFilters()}
              placeholder="模糊搜尋標題…"
              className="w-full pl-9 pr-8 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black"
            />
            {inputQ && (
              <button
                onClick={() => setInputQ('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-black transition"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Status */}
          <select
            value={inputStatus}
            onChange={e => setInputStatus(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black bg-white"
          >
            {STATUS_OPTIONS.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>

          {/* Start Date */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 pl-1">開始時間範圍</label>
            <div className="flex items-center gap-2">
              <div className="relative w-full">
                <input
                  type="date"
                  value={inputDateFrom}
                  onChange={e => setInputDateFrom(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  title="開始時間（從）"
                />
                {inputDateFrom && (
                  <button onClick={() => setInputDateFrom('')} className="absolute right-7 top-1/2 -translate-y-1/2 text-gray-400 hover:text-black bg-white p-0.5">
                    <X size={14} />
                  </button>
                )}
              </div>
              <span className="text-gray-400 text-xs">-</span>
              <div className="relative w-full">
                <input
                  type="date"
                  value={inputDateTo}
                  onChange={e => setInputDateTo(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  title="開始時間（至）"
                />
                {inputDateTo && (
                  <button onClick={() => setInputDateTo('')} className="absolute right-7 top-1/2 -translate-y-1/2 text-gray-400 hover:text-black bg-white p-0.5">
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Created Date */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 pl-1">建立時間範圍</label>
            <div className="flex items-center gap-2">
              <div className="relative w-full">
                <input
                  type="date"
                  value={inputCreatedFrom}
                  onChange={e => setInputCreatedFrom(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  title="建立時間（從）"
                />
                {inputCreatedFrom && (
                  <button onClick={() => setInputCreatedFrom('')} className="absolute right-7 top-1/2 -translate-y-1/2 text-gray-400 hover:text-black bg-white p-0.5">
                    <X size={14} />
                  </button>
                )}
              </div>
              <span className="text-gray-400 text-xs">-</span>
              <div className="relative w-full">
                <input
                  type="date"
                  value={inputCreatedTo}
                  onChange={e => setInputCreatedTo(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  title="建立時間（至）"
                />
                {inputCreatedTo && (
                  <button onClick={() => setInputCreatedTo('')} className="absolute right-7 top-1/2 -translate-y-1/2 text-gray-400 hover:text-black bg-white p-0.5">
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={applyFilters}
            className="flex items-center gap-1.5 bg-black text-white px-5 py-2 rounded-lg text-sm hover:bg-gray-800 transition"
          ><Search size={14} /> 搜尋</button>
          {hasFilter && (
            <button
              onClick={resetFilters}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm border border-gray-300 text-gray-600 hover:bg-gray-50 transition"
            >
              <X size={14} /> 清除
            </button>
          )}
        </div>


      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              {['標題', '地點', '開始時間', '狀態', '建立日期'].map(h => (
                <th key={h} className="text-left px-5 py-3 font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {loading ? (
              <tr><td colSpan={5} className="text-center py-16 text-gray-400">載入中…</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-16 text-gray-400">查無資料</td></tr>
            ) : items.map(s => (
              <tr key={s.schedule_id} className="hover:bg-gray-50 transition">
                <td className="px-5 py-3 font-medium max-w-[220px] truncate" title={s.title}>{s.title}</td>
                <td className="px-5 py-3 text-gray-500 max-w-[160px] truncate">{s.meeting_location ?? '—'}</td>
                <td className="px-5 py-3 text-gray-500 whitespace-nowrap">{fmtTime(s.meeting_start_time)}</td>
                <td className="px-5 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[s.status] ?? 'bg-gray-100 text-gray-500'}`}>
                    {STATUS_OPTIONS.find(o => o.value === s.status)?.label ?? s.status}
                  </span>
                </td>
                <td className="px-5 py-3 text-gray-500 whitespace-nowrap">{fmtDate(s.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center gap-2 justify-end">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 disabled:opacity-40 hover:bg-gray-100"
          >上一頁</button>
          <span className="text-sm text-gray-500">{page} / {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 disabled:opacity-40 hover:bg-gray-100"
          >下一頁</button>
        </div>
      )}
    </div>
  )
}

