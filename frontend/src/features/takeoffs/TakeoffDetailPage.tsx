import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { InfoCard } from '../../components/ui/InfoCard'
import { ApiError } from '../../lib/api'
import { formatDateTime } from '../../lib/format'
import { useSession } from '../auth/useSession'
import {
  useCreateRevision,
  useDeleteTakeoffLine,
  useExportTakeoff,
  useTakeoffDetail,
  useTakeoffLines,
  useUpdateTakeoffLine,
  type TakeoffLine,
} from './api'
import { ExportActions } from './ExportActions'

const STAGE_ORDER = [
  { key: 'ground', label: 'Ground' },
  { key: 'topout', label: 'TopOut' },
  { key: 'final', label: 'Final' },
] as const

type EditDraft = {
  qty: string
  stage: TakeoffLine['stage']
  factor: string
  sort_order: string
}

function buildDraft(line: TakeoffLine): EditDraft {
  return {
    qty: line.qty,
    stage: line.stage,
    factor: line.factor,
    sort_order: String(line.sort_order),
  }
}

function humanizeMutationError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'takeoff_locked':
        return 'This CURRENT takeoff is locked and cannot be changed.'
      case 'project_closed':
        return 'This project is closed and its CURRENT takeoff cannot be changed.'
      case 'invalid_takeoff_state':
        return 'This takeoff is no longer in a mutable CURRENT state.'
      case 'line_not_found':
        return 'The selected line could not be found. Refresh and try again.'
      case 'validation_error':
        return error.message || 'One or more line fields are invalid.'
      default:
        return error.message || 'Unexpected API error.'
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unexpected API error.'
}

function humanizeRevisionError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'takeoff_locked':
        return 'This takeoff is already locked and cannot be revised again from the current screen.'
      case 'project_closed':
        return 'This project is closed and cannot receive a new revision.'
      case 'invalid_takeoff_state':
        return 'Only an open CURRENT takeoff can be revised.'
      default:
        return error.message || 'Unexpected API error.'
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unexpected API error.'
}

export function TakeoffDetailPage() {
  const { takeoffId = '' } = useParams()
  const navigate = useNavigate()
  const session = useSession()
  const detail = useTakeoffDetail(takeoffId)
  const lines = useTakeoffLines(takeoffId)
  const updateLine = useUpdateTakeoffLine()
  const deleteLine = useDeleteTakeoffLine()
  const createRevision = useCreateRevision()
  const exportTakeoff = useExportTakeoff()
  const isEditor = session.data?.role === 'editor'

  const [editingLine, setEditingLine] = useState<TakeoffLine | null>(null)
  const [editDraft, setEditDraft] = useState<EditDraft | null>(null)
  const [linePendingDelete, setLinePendingDelete] = useState<TakeoffLine | null>(null)
  const [mutationError, setMutationError] = useState<string | null>(null)

  const groupedLines = useMemo(() => {
    const items = lines.data ?? []
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
  }, [lines.data])

  function openEditModal(line: TakeoffLine) {
    setMutationError(null)
    setEditingLine(line)
    setEditDraft(buildDraft(line))
  }

  function closeEditModal() {
    if (updateLine.isPending) return
    setEditingLine(null)
    setEditDraft(null)
  }

  function closeDeleteDialog() {
    if (deleteLine.isPending) return
    setLinePendingDelete(null)
  }

  async function handleSaveEdit() {
    if (!editingLine || !editDraft) return

    setMutationError(null)

    try {
      await updateLine.mutateAsync({
        takeoffId,
        lineId: editingLine.line_id,
        qty: editDraft.qty,
        stage: editDraft.stage,
        factor: editDraft.factor,
        sort_order: Number(editDraft.sort_order),
      })
      setEditingLine(null)
      setEditDraft(null)
    } catch (error) {
      setMutationError(humanizeMutationError(error))
    }
  }

  async function handleDeleteLine() {
    if (!linePendingDelete) return

    setMutationError(null)

    try {
      await deleteLine.mutateAsync({
        takeoffId,
        lineId: linePendingDelete.line_id,
      })
      setLinePendingDelete(null)
    } catch (error) {
      setMutationError(humanizeMutationError(error))
    }
  }

  async function handleCreateRevision() {
    setMutationError(null)

    try {
      await createRevision.mutateAsync({ takeoffId })
      navigate(`/takeoffs/${takeoffId}/versions`)
    } catch (error) {
      setMutationError(humanizeRevisionError(error))
    }
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">
            Current Takeoff
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
            {detail.data?.project.project_code ?? 'Takeoff detail'}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            Review stage-grouped lines, confirm financial totals, and apply controlled CURRENT
            line adjustments by line identity when needed.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            className="rounded-full border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
            to={`/takeoffs/${takeoffId}/versions`}
          >
            View versions
          </Link>
          {isEditor ? (
            <button
              className="rounded-full bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={createRevision.isPending || detail.data?.state.is_locked}
              onClick={handleCreateRevision}
              type="button"
            >
              {createRevision.isPending ? 'Creating snapshot...' : 'Snapshot / Revise'}
            </button>
          ) : null}
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
            Signed in as <span className="font-medium text-slate-900">{session.data?.role}</span>
          </div>
        </div>
      </section>

      {mutationError ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {mutationError}
        </div>
      ) : null}

      {detail.isLoading || lines.isLoading ? (
        <InfoCard subtitle="Pulling live takeoff detail and grouped lines" title="Loading takeoff">
          <p className="text-sm text-slate-500">
            Fetching current lines, totals, and operational state...
          </p>
        </InfoCard>
      ) : null}

      {detail.isError || lines.isError ? (
        <InfoCard subtitle="The frontend could not load the selected takeoff." title="Unable to load">
          <p className="text-sm text-rose-700">
            {((detail.error ?? lines.error) as Error | undefined)?.message || 'Unexpected API error.'}
          </p>
        </InfoCard>
      ) : null}

      {detail.data ? (
        <>
          <InfoCard
            subtitle={detail.data.project.project_name}
            title={`${detail.data.project.project_code} operational summary`}
          >
            <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-5">
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Project</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {detail.data.project.project_name}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Created</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {formatDateTime(detail.data.created_at)}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Updated</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {formatDateTime(detail.data.updated_at)}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Line count</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {detail.data.summary.line_count}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Mode</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {detail.data.state.is_locked ? 'Locked snapshot' : 'Mutable current'}
                </p>
              </div>
            </div>
          </InfoCard>

          <section className="grid gap-4 md:grid-cols-3">
            <InfoCard subtitle="Before tax" title="Subtotal">
              <p className="text-3xl font-semibold tracking-tight text-slate-900">
                ${detail.data.totals.subtotal}
              </p>
            </InfoCard>
            <InfoCard subtitle="Tax summary" title="Tax">
              <p className="text-3xl font-semibold tracking-tight text-slate-900">
                ${detail.data.totals.tax}
              </p>
            </InfoCard>
            <InfoCard subtitle="Operational total" title="Total">
              <p className="text-3xl font-semibold tracking-tight text-slate-900">
                ${detail.data.totals.total}
              </p>
            </InfoCard>
          </section>

          <ExportActions
            onExport={(format) => exportTakeoff.mutateAsync({ takeoffId, format })}
            subtitle="Create a PDF, CSV, or JSON output from the current takeoff."
            title="Export current takeoff"
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
                          {isEditor ? <th className="px-3 py-2 text-right">Actions</th> : null}
                        </tr>
                      </thead>
                      <tbody>
                        {group.items.map((line) => (
                          <tr key={line.line_id} className="rounded-2xl bg-slate-50 text-sm text-slate-700">
                            <td className="rounded-l-2xl px-3 py-3 font-semibold text-slate-900">
                              {line.item_code}
                            </td>
                            <td className="px-3 py-3">{line.description}</td>
                            <td className="px-3 py-3">{line.qty}</td>
                            <td className="px-3 py-3 capitalize">{line.stage}</td>
                            <td className="px-3 py-3">{line.factor}</td>
                            <td className="px-3 py-3">{line.sort_order}</td>
                            {isEditor ? (
                              <td className="rounded-r-2xl px-3 py-3">
                                <div className="flex justify-end gap-2">
                                  <button
                                    className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-white"
                                    onClick={() => openEditModal(line)}
                                    type="button"
                                  >
                                    Edit
                                  </button>
                                  <button
                                    className="rounded-full border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-50"
                                    onClick={() => {
                                      setMutationError(null)
                                      setLinePendingDelete(line)
                                    }}
                                    type="button"
                                  >
                                    Delete
                                  </button>
                                </div>
                              </td>
                            ) : null}
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

      {isEditor && editingLine && editDraft ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/45 px-6 py-10">
          <div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">
                  Edit Current Line
                </p>
                <h3 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
                  {editingLine.item_code}
                </h3>
                <p className="mt-2 text-sm text-slate-500">
                  Line ID {editingLine.line_id} · Current stage {editingLine.stage}
                </p>
              </div>
              <button
                className="rounded-full border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:border-slate-400 hover:bg-slate-50"
                onClick={closeEditModal}
                type="button"
              >
                Close
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Qty</span>
                <input
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-500"
                  min="0"
                  onChange={(event) =>
                    setEditDraft((current) =>
                      current ? { ...current, qty: event.target.value } : current,
                    )
                  }
                  step="0.01"
                  type="number"
                  value={editDraft.qty}
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Stage</span>
                <select
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-500"
                  onChange={(event) =>
                    setEditDraft((current) =>
                      current
                        ? {
                            ...current,
                            stage: event.target.value as TakeoffLine['stage'],
                          }
                        : current,
                    )
                  }
                  value={editDraft.stage}
                >
                  {STAGE_ORDER.map((stage) => (
                    <option key={stage.key} value={stage.key}>
                      {stage.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Factor</span>
                <input
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-500"
                  min="0"
                  onChange={(event) =>
                    setEditDraft((current) =>
                      current ? { ...current, factor: event.target.value } : current,
                    )
                  }
                  step="0.01"
                  type="number"
                  value={editDraft.factor}
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Sort order</span>
                <input
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-500"
                  min="0"
                  onChange={(event) =>
                    setEditDraft((current) =>
                      current ? { ...current, sort_order: event.target.value } : current,
                    )
                  }
                  step="1"
                  type="number"
                  value={editDraft.sort_order}
                />
              </label>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                className="rounded-full border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={updateLine.isPending}
                onClick={closeEditModal}
                type="button"
              >
                Cancel
              </button>
              <button
                className="rounded-full bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                disabled={updateLine.isPending}
                onClick={handleSaveEdit}
                type="button"
              >
                {updateLine.isPending ? 'Saving...' : 'Save changes'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {isEditor && linePendingDelete ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/45 px-6 py-10">
          <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-rose-700">
              Delete Current Line
            </p>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
              {linePendingDelete.item_code}
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              Confirm deletion of line ID {linePendingDelete.line_id}. This removes the CURRENT
              line from the takeoff immediately.
            </p>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                className="rounded-full border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={deleteLine.isPending}
                onClick={closeDeleteDialog}
                type="button"
              >
                Cancel
              </button>
              <button
                className="rounded-full bg-rose-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:bg-rose-300"
                disabled={deleteLine.isPending}
                onClick={handleDeleteLine}
                type="button"
              >
                {deleteLine.isPending ? 'Deleting...' : 'Delete line'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
