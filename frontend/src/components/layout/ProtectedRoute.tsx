import { Navigate, useLocation } from 'react-router-dom'
import type { PropsWithChildren } from 'react'

import { useSession } from '../../features/auth/useSession'

export function ProtectedRoute({ children }: PropsWithChildren) {
  const location = useLocation()
  const session = useSession()

  if (session.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 text-sm text-slate-600 shadow-sm">
          Loading session...
        </div>
      </div>
    )
  }

  if (!session.data) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />
  }

  return <>{children}</>
}
