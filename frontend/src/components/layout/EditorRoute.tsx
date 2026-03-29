import { Navigate, useLocation } from 'react-router-dom'
import type { PropsWithChildren } from 'react'

import { useSession } from '../../features/auth/useSession'

export function EditorRoute({ children }: PropsWithChildren) {
  const location = useLocation()
  const session = useSession()

  if (session.isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 text-sm text-slate-600 shadow-sm">
          Checking access...
        </div>
      </div>
    )
  }

  if (!session.data) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />
  }

  if (session.data.role !== 'editor') {
    return <Navigate replace to="/projects" />
  }

  return <>{children}</>
}
