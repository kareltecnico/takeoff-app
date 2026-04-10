import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '../../lib/api'

export type TakeoffDetail = {
  takeoff_id: string
  template_code: string
  model_display: string | null
  project: {
    project_code: string
    project_name: string
    status: 'open' | 'closed'
  }
  state: {
    is_current: boolean
    is_locked: boolean
  }
  created_at: string
  updated_at: string
  totals: {
    subtotal: string
    tax: string
    total: string
  }
  stage_totals: {
    ground: {
      subtotal: string
      tax: string
      total: string
    }
    topout: {
      subtotal: string
      tax: string
      total: string
    }
    final: {
      subtotal: string
      tax: string
      total: string
    }
  }
  summary: {
    line_count: number
    stage_counts: {
      ground: number
      topout: number
      final: number
    }
  }
}

export type TakeoffLine = {
  line_id: string
  mapping_id: string | null
  item_code: string
  description: string
  qty: string
  stage: 'ground' | 'topout' | 'final'
  factor: string
  unit_price: string
  line_total: string
  sort_order: number
}

export type TakeoffVersionSummary = {
  version_id: string
  version_number: number
  created_at: string
  totals: {
    subtotal: string
    tax: string
    total: string
  }
}

export type VersionLine = {
  version_line_id: string
  mapping_id: string | null
  item_code: string
  description: string
  qty: string
  stage: 'ground' | 'topout' | 'final'
  factor: string
  sort_order: number
}

export type VersionDetail = {
  version_id: string
  takeoff_id: string
  version_number: number
  created_at: string
  totals: {
    subtotal: string
    tax: string
    total: string
  }
  summary: {
    line_count: number
    stage_counts: {
      ground: number
      topout: number
      final: number
    }
  }
  lines: VersionLine[]
}

export type ExportResult = {
  format: 'pdf' | 'csv' | 'json'
  file_name: string
  download_url: string
}

export function useTakeoffDetail(takeoffId: string) {
  return useQuery({
    queryKey: ['takeoff', takeoffId],
    queryFn: async () => {
      const response = await apiRequest<{ takeoff: TakeoffDetail }>(`/api/v1/takeoffs/${takeoffId}`)
      return response.takeoff
    },
    enabled: Boolean(takeoffId),
  })
}

export function useTakeoffLines(takeoffId: string) {
  return useQuery({
    queryKey: ['takeoff-lines', takeoffId],
    queryFn: async () => {
      const response = await apiRequest<{ items: TakeoffLine[] }>(
        `/api/v1/takeoffs/${takeoffId}/lines`,
      )
      return response.items
    },
    enabled: Boolean(takeoffId),
  })
}

export function useTakeoffVersions(takeoffId: string) {
  return useQuery({
    queryKey: ['takeoff-versions', takeoffId],
    queryFn: async () => {
      const response = await apiRequest<{ items: TakeoffVersionSummary[] }>(
        `/api/v1/takeoffs/${takeoffId}/versions`,
      )
      return response.items
    },
    enabled: Boolean(takeoffId),
  })
}

export function useVersionDetail(versionId: string) {
  return useQuery({
    queryKey: ['version', versionId],
    queryFn: async () => {
      const response = await apiRequest<{ version: VersionDetail }>(`/api/v1/versions/${versionId}`)
      return response.version
    },
    enabled: Boolean(versionId),
  })
}

type UpdateTakeoffLinePayload = {
  takeoffId: string
  lineId: string
  qty?: string
  stage?: 'ground' | 'topout' | 'final'
  factor?: string
  sort_order?: number
}

export function useUpdateTakeoffLine() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ takeoffId, lineId, ...payload }: UpdateTakeoffLinePayload) =>
      apiRequest<{
        line: TakeoffLine
        totals: {
          subtotal: string
          tax: string
          total: string
        }
      }>(`/api/v1/takeoffs/${takeoffId}/lines/${lineId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
    onSuccess: async (_, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['takeoff-lines', variables.takeoffId] }),
        queryClient.invalidateQueries({ queryKey: ['takeoff', variables.takeoffId] }),
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
      ])
    },
  })
}

export function useDeleteTakeoffLine() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ takeoffId, lineId }: { takeoffId: string; lineId: string }) =>
      apiRequest<void>(`/api/v1/takeoffs/${takeoffId}/lines/${lineId}`, {
        method: 'DELETE',
      }),
    onSuccess: async (_, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['takeoff-lines', variables.takeoffId] }),
        queryClient.invalidateQueries({ queryKey: ['takeoff', variables.takeoffId] }),
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
      ])
    },
  })
}

export function useCreateRevision() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ takeoffId }: { takeoffId: string }) =>
      apiRequest<{
        version: {
          version_id: string
          takeoff_id: string
          version_number: number
          created_at: string
        }
      }>(`/api/v1/takeoffs/${takeoffId}/revisions`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    onSuccess: async (_, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['takeoff-versions', variables.takeoffId] }),
        queryClient.invalidateQueries({ queryKey: ['takeoff', variables.takeoffId] }),
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
      ])
    },
  })
}

export function useExportTakeoff() {
  return useMutation({
    mutationFn: ({
      takeoffId,
      format,
    }: {
      takeoffId: string
      format: ExportResult['format']
    }) =>
      apiRequest<{ export: ExportResult }>(`/api/v1/takeoffs/${takeoffId}/exports`, {
        method: 'POST',
        body: JSON.stringify({ format }),
      }),
  })
}

export function useExportVersion() {
  return useMutation({
    mutationFn: ({
      versionId,
      format,
    }: {
      versionId: string
      format: ExportResult['format']
    }) =>
      apiRequest<{ export: ExportResult }>(`/api/v1/versions/${versionId}/exports`, {
        method: 'POST',
        body: JSON.stringify({ format }),
      }),
  })
}
