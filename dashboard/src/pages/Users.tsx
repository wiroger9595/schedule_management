import { useEffect, useState } from 'react'
import { api, UserRow } from '../api'
import { Search, X } from 'lucide-react'

const PAGE_SIZE = 20

const STATUS_OPTIONS = [
  { value: '', label: '全部狀態' },
  { value: 'Y', label: '啟用' },
  { value: 'N', label: '停用' },
]

export default function Users() {
  const [items, setItems] = useState<UserRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)

  // Filter state (applied)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState('')
  const [createdFrom, setCreatedFrom] = useState('')
  const [createdTo, setCreatedTo] = useState('')

  // Input state (pending)
  const [inputName, setInputName] = useState('')
  const [inputEmail, setInputEmail] = useState('')
  const [inputStatus, setInputStatus] = useState('')
  const [inputCreatedFrom, setInputCreatedFrom] = useState('')
  const [inputCreatedTo, setInputCreatedTo] = useState('')

  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.users(page, '', name, email, status, createdFrom, createdTo)
      .then(r => { setItems(r.items); setTotal(r.total) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [page, name, email, status, createdFrom, createdTo])

  const totalPages = Math.ceil(total / PAGE_SIZE)

  function applyFilters() {
    setName(inputName)
    setEmail(inputEmail)
    setStatus(inputStatus)
    setCreatedFrom(inputCreatedFrom)
    setCreatedTo(inputCreatedTo)
    setPage(1)
  }

  function resetFilters() {
    setInputName(''); setInputEmail(''); setInputStatus(''); setInputCreatedFrom(''); setInputCreatedTo('')
    setName(''); setEmail(''); setStatus(''); setCreatedFrom(''); setCreatedTo('')
    setPage(1)
  }

  const hasFilter = name || email || status || createdFrom || createdTo

  function fmt(iso: string | null) {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('zh-TW')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">用戶管理</h1>
        <span className="text-gray-500 text-sm">共 {total.toLocaleString()} 位</span>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-2xl shadow-sm space-y-4">
        <div className="flex flex-wrap gap-3 items-end">
          
          {/* Name search */}
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              value={inputName}
              onChange={e => setInputName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && applyFilters()}
              placeholder="搜尋姓名…"
              className="w-[180px] pl-9 pr-8 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black"
            />
            {inputName && (
              <button
                onClick={() => setInputName('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-black transition"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Email search */}
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              value={inputEmail}
              onChange={e => setInputEmail(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && applyFilters()}
              placeholder="搜尋 Email…"
              className="w-[220px] pl-9 pr-8 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black"
            />
            {inputEmail && (
              <button
                onClick={() => setInputEmail('')}
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

          {/* Created Date */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 pl-1">註冊日期範圍</label>
            <div className="flex items-center gap-2">
              <div className="relative w-[150px]">
                <input
                  type="date"
                  value={inputCreatedFrom}
                  onChange={e => setInputCreatedFrom(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  title="註冊時間（從）"
                />
                {inputCreatedFrom && (
                  <button onClick={() => setInputCreatedFrom('')} className="absolute right-7 top-1/2 -translate-y-1/2 text-gray-400 hover:text-black bg-white p-0.5" title="清除">
                    <X size={14} />
                  </button>
                )}
              </div>
              <span className="text-gray-400 text-xs">-</span>
              <div className="relative w-[150px]">
                <input
                  type="date"
                  value={inputCreatedTo}
                  onChange={e => setInputCreatedTo(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  title="註冊時間（至）"
                />
                {inputCreatedTo && (
                  <button onClick={() => setInputCreatedTo('')} className="absolute right-7 top-1/2 -translate-y-1/2 text-gray-400 hover:text-black bg-white p-0.5" title="清除">
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
            className="bg-black text-white px-5 py-2 rounded-lg text-sm hover:bg-gray-800 transition"
          >套用篩選</button>
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
              {['姓名', 'Email', '狀態', '語言', '註冊日期'].map(h => (
                <th key={h} className="text-left px-5 py-3 font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {loading ? (
              <tr><td colSpan={5} className="text-center py-16 text-gray-400">載入中…</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-16 text-gray-400">查無資料</td></tr>
            ) : items.map(u => (
              <tr key={u.user_id} className="hover:bg-gray-50 transition">
                <td className="px-5 py-3 font-medium">{u.full_name ?? '—'}</td>
                <td className="px-5 py-3 text-gray-500">{u.email ?? '—'}</td>
                <td className="px-5 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium
                    ${u.status === 'Y' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}>
                    {u.status === 'Y' ? '啟用' : '停用'}
                  </span>
                </td>
                <td className="px-5 py-3 text-gray-500">{u.language ?? '—'}</td>
                <td className="px-5 py-3 text-gray-500">{fmt(u.created_at)}</td>
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
