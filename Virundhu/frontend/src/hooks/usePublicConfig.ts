import { useQuery } from "@tanstack/react-query";
import { publicApi } from "@/services/api";

/** Public settings (is Google sign-in on? is the AI ready?). Cached for the session. */
export function usePublicConfig() {
  return useQuery({ queryKey: ["public-config"], queryFn: publicApi.config, staleTime: Infinity, retry: 1 });
}
