import { useState } from 'react'

import { ApiError } from '../../lib/api'
import type { ExportResult } from './api'

const EXPORT_FORMATS: Array<{ value: ExportResult['format']; label: string }> = [
  { value: 'pdf', label: 'PDF' },
  { value: 'csv', label: 'CSV' },
  { value: 'json', label: 'JSON' },
]

function humanizeExportError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'validation_error':
        return error.message || 'The requested export format is not valid.'
      case 'forbidden':
        return 'You do not have permission to export this takeoff.'
      case 'not_found':
        return 'The requested takeoff or version could not be found.'
      default:
        return error.message || 'Unexpected API error.'
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unexpected API error.'
}

type ExportActionsProps = {
  title: string
  subtitle: string
  onExport: (format: ExportResult['format']) => Promise<{ export: ExportResult }>
}

export function ExportActions({ title, subtitle, onExport }: ExportActionsProps) {
  const [result, setResult] = useState<ExportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pendingFormat, setPendingFormat] = useState<ExportResult['format'] | null>(null)

  const hasDirectLink =
    result?.download_url?.startsWith('/') || result?.download_url?.startsWith('http')

  async function handleExport(format: ExportResult['format']) {
    setPendingFormat(format)
    setError(null)

    try {
      const response = await onExport(format)
      setResult(response.export)
    } catch (exportError) {
      setError(humanizeExportError(exportError))
    } finally {
      setPendingFormat(null)
    }
  }

  return (
    <section className="rounded-3xl border border-slate-200/80 bg-white p-6 shadow-[0_18px_50px_-36px_rgba(15,23,42,0.45)]">
      <div className="mb-5">
        <h3 className="text-lg font-semibold tracking-tight text-slate-900">{title}</h3>
        <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
      </div>

      <div className="flex flex-wrap gap-3">
        {EXPORT_FORMATS.map((format) => (
          <button
            key={format.value}
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={pendingFormat !== null}
            onClick={() => handleExport(format.value)}
            type="button"
          >
            {pendingFormat === format.value ? `Exporting ${format.label}...` : format.label}
          </button>
        ))}
      </div>

      {result ? (
        <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
          <p className="font-semibold">Export ready: {result.file_name}</p>
          {hasDirectLink ? (
            <a
              className="mt-2 inline-flex rounded-full border border-emerald-300 px-4 py-2 font-medium text-emerald-800 transition hover:bg-emerald-100"
              href={result.download_url}
              rel="noreferrer"
              target="_blank"
            >
              Open export
            </a>
          ) : (
            <div className="mt-2 space-y-2">
              <p>
                The current HTTP bridge returned a local server path instead of a browser download
                link.
              </p>
              <p className="rounded-xl bg-white/80 px-3 py-2 font-mono text-xs text-slate-700">
                {result.download_url}
              </p>
            </div>
          )}
        </div>
      ) : null}

      {error ? (
        <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}
    </section>
  )
}
