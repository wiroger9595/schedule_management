import { useEffect, useState } from 'react'
import { api, Stats } from '../api'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { Users, CalendarDays, Contact, UserCheck } from 'lucide-react'

const STATUS_LABEL: Record<string, string> = {
  PD: '待確認', AT: '已接受/進行中', NG: '已拒絕',
  NA: '未出席', CL: '取消', CS: '即將到來',
}

function StatCard({ label, value, sub, icon: Icon, color }: {
  label: string; value: number; sub?: string; icon: React.ElementType; color: string
}) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm flex items-start gap-4">
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-gray-500 text-sm">{label}</p>
        <p className="text-3xl font-bold mt-0.5">{value.toLocaleString()}</p>
        {sub && <p className="text-gray-400 text-xs mt-1">{sub}</p>}
      </div>
    </div>
  )
}

export default function Overview() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.stats().then(setStats).catch(e => setError(e.message))
  }, [])

  if (error) return <p className="text-red-500">{error}</p>
  if (!stats) return <p className="text-gray-400">載入中…</p>

  const { users, schedules, contacts, attends, charts } = stats

  // Merge daily charts
  const chartData = charts.daily_users.map((d, i) => ({
    date: d.date,
    用戶: d.count,
    行程: charts.daily_schedules[i]?.count ?? 0,
  }))

  const statusEntries = Object.entries(schedules.status_breakdown)

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">總覽</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="總用戶數" value={users.total}
          sub={`本週 +${users.new_this_week}`}
          icon={Users} color="bg-black"
        />
        <StatCard
          label="總行程數" value={schedules.total}
          sub={`本週 +${schedules.new_this_week}`}
          icon={CalendarDays} color="bg-blue-500"
        />
        <StatCard
          label="聯絡人" value={contacts.total}
          icon={Contact} color="bg-emerald-500"
        />
        <StatCard
          label="出席記錄" value={attends.total}
          icon={UserCheck} color="bg-purple-500"
        />
      </div>

      {/* Charts */}
      <div className="bg-white rounded-2xl p-6 shadow-sm">
        <h2 className="font-semibold mb-4">近 14 天新增趨勢</h2>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="用戶" stroke="#000" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="行程" stroke="#3b82f6" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Schedule status breakdown */}
      <div className="bg-white rounded-2xl p-6 shadow-sm">
        <h2 className="font-semibold mb-4">行程狀態分佈</h2>
        <div className="flex flex-wrap gap-3">
          {statusEntries.map(([status, count]) => (
            <div key={status} className="bg-gray-100 rounded-xl px-4 py-3 text-center min-w-[90px]">
              <p className="text-gray-500 text-xs">{STATUS_LABEL[status] ?? status}</p>
              <p className="text-2xl font-bold mt-1">{count}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
