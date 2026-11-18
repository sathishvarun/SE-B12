import { useQuery } from "@tanstack/react-query";
import { appApi } from "@/services/api";

/** Dashboard numbers for the whole restaurant or one outlet. */
export function useOverview(outletId?: number, enabled = true) {
  return useQuery({ queryKey: ["overview", outletId ?? "all"], queryFn: () => appApi.overview(outletId), staleTime: 15_000, refetchInterval: 30_000, enabled });
}
