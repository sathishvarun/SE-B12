import { useQuery } from "@tanstack/react-query"

import api from "@/services/api"
import type { Lead, Page } from "@/types"

/** Up to 100 most recent leads, for the "link to lead" select in the task form. */
export function useLeadOptions() {
  return useQuery({
    queryKey: ["leads", "options"],
    queryFn: async (): Promise<Lead[]> => {
      const { data } = await api.get<Page<Lead>>("/leads", { params: { page_size: 100 } })
      return data.items
    },
  })
}
