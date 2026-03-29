import { useQuery } from '@tanstack/react-query'

import { apiRequest } from '../../lib/api'

export type OfficialTemplate = {
  template_code: string
  template_name: string
  category: string
}

export function useOfficialTemplates() {
  return useQuery({
    queryKey: ['templates', 'official'],
    queryFn: async () => {
      const response = await apiRequest<{ items: OfficialTemplate[] }>('/api/v1/templates')
      return response.items
    },
  })
}
