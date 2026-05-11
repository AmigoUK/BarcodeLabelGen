import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { User } from "../lib/types";
import { ME_QUERY_KEY } from "./useMe";

type LoginInput = { email: string; password: string };

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: LoginInput) => {
      const body = await api<{ user: User }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(input),
      });
      return body.user;
    },
    onSuccess: (user) => {
      qc.setQueryData(ME_QUERY_KEY, user);
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api("/api/auth/logout", { method: "POST" });
    },
    onSuccess: () => {
      qc.setQueryData(ME_QUERY_KEY, null);
      qc.clear();
    },
  });
}

type ChangePwInput = { current_password: string; new_password: string };

export function useChangePassword() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: ChangePwInput) => {
      await api("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify(input),
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ME_QUERY_KEY });
    },
  });
}
