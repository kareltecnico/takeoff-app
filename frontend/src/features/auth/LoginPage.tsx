import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import type { FormEvent } from 'react'

import { ApiError } from '../../lib/api'
import { useLogin } from './api'
import { useSession } from './useSession'

export function LoginPage() {
  const session = useSession()
  const login = useLogin()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  if (session.data) {
    return <Navigate replace to="/projects" />
  }

  const error =
    login.error instanceof ApiError ? login.error.message : 'Unable to sign in right now.'

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    login.mutate({ username, password })
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#dff7f2_0%,#eff5fa_48%,#f7f9fc_100%)] px-6 py-12">
      <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="flex flex-col justify-between rounded-[2rem] border border-teal-200/60 bg-slate-950 p-10 text-white shadow-[0_30px_80px_-40px_rgba(15,23,42,0.85)]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-teal-300">
              Leza&apos;s Plumbing
            </p>
            <h1 className="mt-6 max-w-xl text-4xl font-semibold leading-tight tracking-tight">
              Takeoff generation for daily operational use.
            </h1>
            <p className="mt-5 max-w-lg text-base leading-7 text-slate-300">
              Review current takeoffs, compare revisions, and work from validated template
              baselines without going back to Excel.
            </p>
          </div>

          <div className="grid gap-4 text-sm text-slate-300 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="font-medium text-white">Readability</p>
              <p className="mt-2 leading-6">Grouped stages, clean summaries, and reduced noise.</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="font-medium text-white">Safety</p>
              <p className="mt-2 leading-6">Role-based access and line-level targeting.</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="font-medium text-white">Speed</p>
              <p className="mt-2 leading-6">Generate, inspect, and revise from one workflow.</p>
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-slate-200/80 bg-white p-8 shadow-[0_22px_60px_-40px_rgba(15,23,42,0.45)]">
          <div className="mb-8">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              Sign In
            </p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">
              Access your workspace
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Editor and Viewer users sign in here. Password resets remain operationally managed
              outside the MVP UI.
            </p>
          </div>

          <form className="space-y-5" onSubmit={onSubmit}>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">Username</span>
              <input
                autoComplete="username"
                className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                onChange={(event) => setUsername(event.target.value)}
                required
                type="text"
                value={username}
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">Password</span>
              <input
                autoComplete="current-password"
                className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>

            {login.isError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            ) : null}

            <button
              className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={login.isPending}
              type="submit"
            >
              {login.isPending ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </section>
      </div>
    </div>
  )
}
