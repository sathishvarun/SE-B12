import { useQuery } from "@tanstack/react-query"

import api from "@/services/api"
import type { ContactOption } from "@/types"

/** All of the user's contacts as {id, name, company} for select dropdowns. */
export function useContactOptions() {
  return useQuery({
    queryKey: ["contacts", "options"],
    queryFn: async (): Promise<ContactOption[]> => {
      const { data } = await api.get<ContactOption[]>("/contacts/options")
      return data
    },
  })
}
