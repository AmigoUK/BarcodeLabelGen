import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { CreateDeviceResponse, Device } from "../lib/types";

const DEVICES_KEY = ["devices"] as const;

export function useDevices() {
  return useQuery({
    queryKey: DEVICES_KEY,
    queryFn: () => api<{ devices: Device[] }>("/api/devices").then((r) => r.devices),
    // Devices report last_seen via the agent heartbeat — keep it fresh-ish.
    refetchInterval: 30_000,
  });
}

export function useCreateDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api<CreateDeviceResponse>("/api/devices", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DEVICES_KEY });
    },
  });
}

export function useDeleteDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/api/devices/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DEVICES_KEY });
    },
  });
}

// Polls the devices list fast (every 3s) while the connect wizard waits for a
// specific device to come online. Mirrors the 60s window used elsewhere.
export function useDeviceOnline(deviceId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ["device-online", deviceId] as const,
    queryFn: () => api<{ devices: Device[] }>("/api/devices").then((r) => r.devices),
    enabled: enabled && deviceId != null,
    refetchInterval: enabled ? 3000 : false,
    select: (devices: Device[]) => {
      const d = devices.find((x) => x.id === deviceId);
      if (!d?.last_seen_at) return false;
      return Date.now() - new Date(d.last_seen_at).getTime() < 60_000;
    },
  });
}
