import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'

import { InfoCard } from '../../components/ui/InfoCard'
import { formatDateTime } from '../../lib/format'
import { useExportVersion, useVersionDetail } from './api'
import { ExportActions } from './ExportActions'

const STAGE_ORDER = [
  { key: 'ground', label: 'Ground' },
  { key: 'topout', label: 'TopOut' },
  { key: 'final', label: 'Final' },
] as const

export function VersionDetailPage() {
  const { versionId = '' } = useParams()
  const version = useVersionDetail(versionId)
  const exportVersion = useExportVersion()

  const groupedLines = useMemo(() => {
    const items = version.data?.lines ?? []
    return STAGE_ORDER.map(({ key, label }) => ({
      key,
      label,
      items: items
        .filter((line) => line.stage === key)
        .sort((left, right) =>
          left.sort_order === right.sort_order
            ? left.item_code.localeCompare(right.item_code)
            : left.sort_order - right.sort_order,
        ),
    }))
  }, [version.data?.lines])

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">
            Version Detail
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
            {version.data ? `Version ${version.data.version_number}` : 'Snapshot detail'}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            This view is read-only for all roles. It preserves the exact lines and totals captured
            when the snapshot was created.
          </p>
        </div>

        {version.data ? (
          <Link
            className="rounded-full border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
            to={`/takeoffs/${version.data.takeoff_id}/versions`}
          >
            Back to versions
          </Link>
        ) : null}
      </section>

      {version.isLoading ? (
        <InfoCard subtitle="Pulling snapshot lines and totals from the HTTP bridge" title="Loading version">
          <p className="text-sm text-slate-500">Fetching snapshot detail...</p>
        </InfoCard>
      ) : null}

      {version.isError ? (
        <InfoCard subtitle="The frontend could not load the selected version." title="Unable to load">
          <p className="text-sm text-rose-700">
            {(version.error as Error | undefined)?.message || 'Unexpected API error.'}
          </p>
        </InfoCard>
      ) : null}

      {version.data ? (
        <>
          <InfoCard
            subtitle={`Created ${formatDateTime(version.data.created_at)}`}
            title={`Snapshot ${version.data.version_number}`}
          >
            <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-5">
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Takeoff</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{version.data.takeoff_id}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Created</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {formatDateTime(version.data.created_at)}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Line count</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {version.data.summary.line_count}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Ground</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {version.data.summary.stage_counts.ground}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">TopOut / Final</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {version.data.summary.stage_counts.topout} / {version.data.summary.stage_counts.final}
                </p>
              </div>
            </div>
          </InfoCard>

          <section className="grid gap-4 md:grid-cols-3">
            <InfoCard subtitle="Before tax" title="Subtotal">
              <p className="text-3xl font-semibold tracking-tight text-slate-900">
                ${version.data.totals.subtotal}
              </p>
            </InfoCard>
            <InfoCard subtitle="Tax summary" title="Tax">
              <p className="text-3xl font-semibold tracking-tight text-slate-900">
                ${version.data.totals.tax}
              </p>
            </InfoCard>
            <InfoCard subtitle="Snapshot total" title="Total">
              <p className="text-3xl font-semibold tracking-tight text-slate-900">
                ${version.data.totals.total}
              </p>
            </InfoCard>
          </section>

          <ExportActions
            onExport={(format) => exportVersion.mutateAsync({ versionId, format })}
            subtitle="Create a PDF, CSV, or JSON output from this read-only snapshot."
            title="Export version"
          />

          <div className="space-y-5">
            {groupedLines.map((group) => (
              <InfoCard
                key={group.key}
                subtitle={`${group.items.length} line${group.items.length === 1 ? '' : 's'} in this stage`}
                title={group.label}
              >
                {group.items.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                    No lines in this stage.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full border-separate border-spacing-y-2">
                      <thead>
                        <tr className="text-left text-[11px] uppercase tracking-[0.18em] text-slate-400">
                          <th className="px-3 py-2">Item</th>
                          <th className="px-3 py-2">Description</th>
                          <th className="px-3 py-2">Qty</th>
                          <th className="px-3 py-2">Stage</th>
                          <th className="px-3 py-2">Factor</th>
                          <th className="px-3 py-2">Sort</th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.items.map((line) => (
                          <tr
                            key={line.version_line_id}
                            className="rounded-2xl bg-slate-50 text-sm text-slate-700"
                          >
                            <td className="rounded-l-2xl px-3 py-3 font-semibold text-slate-900">
                              {line.item_code}
                            </td>
                            <td className="px-3 py-3">{line.description}</td>
                            <td className="px-3 py-3">{line.qty}</td>
                            <td className="px-3 py-3 capitalize">{line.stage}</td>
                            <td className="px-3 py-3">{line.factor}</td>
                            <td className="rounded-r-2xl px-3 py-3">{line.sort_order}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </InfoCard>
            ))}
          </div>
        </>
      ) : null}
    </div>
  )
}
