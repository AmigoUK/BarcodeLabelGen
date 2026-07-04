import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { PrintJob } from "../lib/types";

const PRINT_JOBS_KEY = ["print-jobs"] as const;

export function usePrintJobs(options?: { watch?: boolean }) {
  return useQuery({
    queryKey: PRINT_JOBS_KEY,
    queryFn: () => api<{ jobs: PrintJob[] }>("/api/print-jobs").then((r) => r.jobs),
    // While a submitted job is in flight the dialog polls for its outcome.
    refetchInterval: options?.watch ? 1500 : false,
  });
}

type CreatePrintJobInput = {
  device_id: number;
  printer: string;
  zpl: string;
  copies: number;
};

export function useCreatePrintJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreatePrintJobInput) =>
      api<{ job: PrintJob }>("/api/print-jobs", {
        method: "POST",
        body: JSON.stringify(input),
      }).then((r) => r.job),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PRINT_JOBS_KEY });
    },
  });
}
