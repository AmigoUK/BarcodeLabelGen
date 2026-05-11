import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../lib/api";
import type { User } from "../lib/types";

export const ME_QUERY_KEY = ["me"] as const;

export function useMe() {
  return useQuery<User | null>({
    queryKey: ME_QUERY_KEY,
    queryFn: async () => {
      try {
        return await api<User>("/api/me");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          return null;
        }
        throw err;
      }
    },
    staleTime: 60_000,
  });
}
