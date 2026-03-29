import { Outlet } from 'react-router-dom'

import { useLogout } from '../../features/auth/api'
import { useSession } from '../../features/auth/useSession'

export function AppShell() {
  const { data } = useSession()
  const logout = useLogout()

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f7f9fc_0%,#eef3f8_100%)] text-slate-900">
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">
              Take-Off App
            </p>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">
              Operational Workspace
            </h1>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-slate-900">{data?.display_name}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                {data?.role}
              </p>
            </div>

            <button
              className="rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
              onClick={() => logout.mutate()}
              type="button"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
