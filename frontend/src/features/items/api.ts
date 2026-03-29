import { useQueries } from '@tanstack/react-query'

import { apiRequest } from '../../lib/api'

export type CatalogItem = {
  code: string
  item_number: string | null
  description: string
  details: string | null
  category: string | null
  unit_price: string
  taxable: boolean
  is_active: boolean
}

export function useItemsByCategories(categories: string[]) {
  const uniqueCategories = Array.from(new Set(categories.filter(Boolean)))

  const queries = useQueries({
    queries: uniqueCategories.map((category) => ({
      queryKey: ['items', category],
      queryFn: async () => {
        const response = await apiRequest<{ items: CatalogItem[] }>('/api/v1/items?category=' + encodeURIComponent(category))
        return response.items
      },
    })),
  })

  const itemsByCategory = Object.fromEntries(
    uniqueCategories.map((category, index) => [category, queries[index]?.data ?? []]),
  ) as Record<string, CatalogItem[]>

  return {
    itemsByCategory,
    isLoading: queries.some((query) => query.isLoading),
    isError: queries.some((query) => query.isError),
    error: queries.find((query) => query.error)?.error ?? null,
  }
}
