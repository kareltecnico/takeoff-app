import { Link } from 'react-router-dom'

import { InfoCard } from '../../components/ui/InfoCard'
import { formatDateTime } from '../../lib/format'
import { useSession } from '../auth/useSession'
import { useProjects } from './api'

export function ProjectsPage() {
  const session = useSession()
  const projects = useProjects()

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">
            Projects
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
            Current takeoffs at a glance
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Open a current takeoff to review grouped stages, totals, and operational state. This
            shell intentionally starts read-only.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {session.data?.role === 'editor' ? (
            <Link
              className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
              to="/projects/new-takeoff"
            >
              New Takeoff
            </Link>
          ) : null}

          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
            Signed in as <span className="font-medium text-slate-900">{session.data?.role}</span>
          </div>
        </div>
      </section>

      {projects.isLoading ? (
        <InfoCard subtitle="Pulling live data from the HTTP bridge" title="Loading projects">
          <p className="text-sm text-slate-500">Fetching projects and current takeoff summaries...</p>
        </InfoCard>
      ) : null}

      {projects.isError ? (
        <InfoCard subtitle="The frontend could not load the project list." title="Unable to load">
          <p className="text-sm text-rose-700">
            {(projects.error as Error).message || 'Unexpected API error.'}
          </p>
        </InfoCard>
      ) : null}

      {projects.data?.length === 0 ? (
        <InfoCard subtitle="No projects are available yet." title="No projects found">
          <p className="text-sm text-slate-500">
            Once projects and current takeoffs exist, they will appear here.
          </p>
        </InfoCard>
      ) : null}

      <div className="space-y-5">
        {projects.data?.map((project) => (
          <InfoCard
            key={project.project_code}
            subtitle={`${project.contractor_name ?? 'No contractor'} · ${project.foreman_name ?? 'No foreman'}`}
            title={`${project.project_code} — ${project.project_name}`}
          >
            <div className="mb-4 flex items-center justify-between">
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${
                  project.status === 'open'
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                {project.status}
              </span>
              <span className="text-xs uppercase tracking-[0.18em] text-slate-400">
                {project.current_takeoffs.length} current takeoff
                {project.current_takeoffs.length === 1 ? '' : 's'}
              </span>
            </div>

            {project.current_takeoffs.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                No current takeoffs for this project yet.
              </div>
            ) : (
              <div className="grid gap-4 xl:grid-cols-2">
                {project.current_takeoffs.map((takeoff) => (
                  <article
                    key={takeoff.takeoff_id}
                    className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                          {takeoff.template_code}
                        </p>
                        <p className="mt-2 text-sm text-slate-500">
                          Updated {formatDateTime(takeoff.updated_at)}
                        </p>
                      </div>

                      <span
                        className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                          takeoff.is_locked
                            ? 'bg-amber-50 text-amber-700'
                            : 'bg-sky-50 text-sky-700'
                        }`}
                      >
                        {takeoff.is_locked ? 'locked' : 'current'}
                      </span>
                    </div>

                    <dl className="mt-5 grid grid-cols-3 gap-3">
                      <div className="rounded-2xl bg-white px-4 py-3">
                        <dt className="text-[11px] uppercase tracking-[0.18em] text-slate-400">
                          Subtotal
                        </dt>
                        <dd className="mt-1 text-sm font-semibold text-slate-900">
                          ${takeoff.totals.subtotal}
                        </dd>
                      </div>
                      <div className="rounded-2xl bg-white px-4 py-3">
                        <dt className="text-[11px] uppercase tracking-[0.18em] text-slate-400">
                          Tax
                        </dt>
                        <dd className="mt-1 text-sm font-semibold text-slate-900">
                          ${takeoff.totals.tax}
                        </dd>
                      </div>
                      <div className="rounded-2xl bg-white px-4 py-3">
                        <dt className="text-[11px] uppercase tracking-[0.18em] text-slate-400">
                          Total
                        </dt>
                        <dd className="mt-1 text-sm font-semibold text-slate-900">
                          ${takeoff.totals.total}
                        </dd>
                      </div>
                    </dl>

                    <div className="mt-5 flex items-center justify-between">
                      <p className="text-sm text-slate-500">
                        {takeoff.version_count} revision
                        {takeoff.version_count === 1 ? '' : 's'}
                      </p>
                      <Link
                        className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                        to={`/takeoffs/${takeoff.takeoff_id}`}
                      >
                        Open current takeoff
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </InfoCard>
        ))}
      </div>
    </div>
  )
}
