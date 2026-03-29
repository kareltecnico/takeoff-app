import { Link, useParams } from 'react-router-dom'

import { InfoCard } from '../../components/ui/InfoCard'
import { formatDateTime } from '../../lib/format'
import { useTakeoffDetail, useTakeoffVersions } from './api'

export function VersionHistoryPage() {
  const { takeoffId = '' } = useParams()
  const detail = useTakeoffDetail(takeoffId)
  const versions = useTakeoffVersions(takeoffId)

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">
            Version History
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
            {detail.data?.project.project_code ?? 'Takeoff versions'}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            Review read-only snapshots created from the current takeoff. Each version preserves
            the exact lines and totals at the moment it was created.
          </p>
        </div>

        <Link
          className="rounded-full border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          to={`/takeoffs/${takeoffId}`}
        >
          Back to current
        </Link>
      </section>

      {detail.isLoading || versions.isLoading ? (
        <InfoCard subtitle="Pulling live revision data from the HTTP bridge" title="Loading versions">
          <p className="text-sm text-slate-500">Fetching current takeoff context and version list...</p>
        </InfoCard>
      ) : null}

      {detail.isError || versions.isError ? (
        <InfoCard subtitle="The frontend could not load version history." title="Unable to load">
          <p className="text-sm text-rose-700">
            {((detail.error ?? versions.error) as Error | undefined)?.message || 'Unexpected API error.'}
          </p>
        </InfoCard>
      ) : null}

      {detail.data ? (
        <InfoCard
          subtitle={detail.data.project.project_name}
          title={`${detail.data.project.project_code} snapshot history`}
        >
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-2xl bg-slate-50 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Current total</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">${detail.data.totals.total}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Current lines</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{detail.data.summary.line_count}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">State</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">
                {detail.data.state.is_locked ? 'Locked snapshot' : 'Mutable current'}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-50 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Snapshots</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{versions.data?.length ?? 0}</p>
            </div>
          </div>
        </InfoCard>
      ) : null}

      {versions.data?.length === 0 ? (
        <InfoCard subtitle="No revisions have been created yet." title="No versions found">
          <p className="text-sm text-slate-500">
            Editors can create the first snapshot from the current takeoff detail screen.
          </p>
        </InfoCard>
      ) : null}

      <div className="space-y-4">
        {versions.data?.map((version) => (
          <InfoCard
            key={version.version_id}
            subtitle={`Created ${formatDateTime(version.created_at)}`}
            title={`Version ${version.version_number}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-4">
              <dl className="grid min-w-[320px] flex-1 grid-cols-3 gap-3">
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <dt className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Subtotal</dt>
                  <dd className="mt-1 text-sm font-semibold text-slate-900">
                    ${version.totals.subtotal}
                  </dd>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <dt className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Tax</dt>
                  <dd className="mt-1 text-sm font-semibold text-slate-900">${version.totals.tax}</dd>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <dt className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Total</dt>
                  <dd className="mt-1 text-sm font-semibold text-slate-900">${version.totals.total}</dd>
                </div>
              </dl>

              <Link
                className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                to={`/versions/${version.version_id}`}
              >
                Open version
              </Link>
            </div>
          </InfoCard>
        ))}
      </div>
    </div>
  )
}
