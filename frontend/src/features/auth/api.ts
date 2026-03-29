import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { apiRequest } from '../../lib/api'

type LoginPayload = {
  username: string
  password: string
}

export function useLogin() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: LoginPayload) =>
      apiRequest<{ user: SessionUser }>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['session'] })
      navigate('/projects', { replace: true })
    },
  })
}

export function useLogout() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiRequest<void>('/api/v1/auth/logout', {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: ['session'] })
      navigate('/login', { replace: true })
    },
  })
}

export type SessionUser = {
  id: string
  username: string
  display_name: string
  role: 'editor' | 'viewer'
}
