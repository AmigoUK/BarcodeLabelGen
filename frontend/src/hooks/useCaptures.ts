import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Capture } from "../lib/types";

const CAPTURES_KEY = ["captures"] as const;

export function useCaptures() {
  return useQuery({
    queryKey: CAPTURES_KEY,
    queryFn: () => api<{ captures: Capture[] }>("/api/captures").then((r) => r.captures),
    // The agent may push new captures at any time while the page is open.
    refetchInterval: 30_000,
  });
}

/** Fetch one capture's full ZPL on demand (list is metadata-only). */
export function fetchCaptureZpl(id: number): Promise<string> {
  return api<{ capture: Capture & { zpl: string } }>(`/api/captures/${id}`).then(
    (r) => r.capture.zpl,
  );
}

export function useDeleteCapture() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/api/captures/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: CAPTURES_KEY });
    },
  });
}
