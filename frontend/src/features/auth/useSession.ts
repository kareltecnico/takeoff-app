import { useQuery } from '@tanstack/react-query'

import { apiRequest, ApiError } from '../../lib/api'
import type { SessionUser } from './api'

export function useSession() {
  return useQuery({
    queryKey: ['session'],
    queryFn: async () => {
      try {
        const response = await apiRequest<{ user: SessionUser }>('/api/v1/auth/me')
        return response.user
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          return null
        }
        throw error
      }
    },
  })
}
