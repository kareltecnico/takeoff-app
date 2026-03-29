import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { apiRequest } from '../../lib/api'

export type ProjectRow = {
  project_code: string
  project_name: string
  contractor_name: string | null
  foreman_name: string | null
  status: 'open' | 'closed'
  current_takeoffs: Array<{
    takeoff_id: string
    template_code: string
    updated_at: string
    totals: {
      subtotal: string
      tax: string
      total: string
    }
    is_locked: boolean
    version_count: number
  }>
}

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await apiRequest<{ items: ProjectRow[] }>('/api/v1/projects')
      return response.items
    },
  })
}

type CreateProjectPayload = {
  project_code: string
  project_name: string
  contractor_name?: string
  foreman_name?: string
}

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateProjectPayload) =>
      apiRequest<{
        project: {
          project_code: string
          project_name: string
          contractor_name: string | null
          foreman_name: string | null
          status: 'open' | 'closed'
        }
      }>('/api/v1/projects', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

type GenerateTakeoffPayload = {
  project_code: string
  template_code: string
  tax_rate_override: null
  plan: {
    stories: number
    kitchens: number
    garbage_disposals: number
    laundry_rooms: number
    lav_faucets: number
    toilets: number
    showers: number
    bathtubs: number
    half_baths: number
    double_bowl_vanities: number
    hose_bibbs: number
    ice_makers: number
    water_heater_tank_qty: number
    water_heater_tankless_qty: number
    sewer_distance_lf: string
    water_distance_lf: string
  }
}

export function useGenerateTakeoff() {
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (payload: GenerateTakeoffPayload) =>
      apiRequest<{
        takeoff: {
          takeoff_id: string
        }
      }>('/api/v1/takeoffs/generate-from-plan', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    onSuccess: (response) => {
      navigate(`/takeoffs/${response.takeoff.takeoff_id}`)
    },
  })
}
