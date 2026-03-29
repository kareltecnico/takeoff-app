import type { PropsWithChildren } from 'react'

type InfoCardProps = PropsWithChildren<{
  title: string
  subtitle?: string
}>

export function InfoCard({ children, title, subtitle }: InfoCardProps) {
  return (
    <section className="rounded-3xl border border-slate-200/80 bg-white p-6 shadow-[0_18px_50px_-36px_rgba(15,23,42,0.45)]">
      <div className="mb-5">
        <h2 className="text-lg font-semibold tracking-tight text-slate-900">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  )
}
