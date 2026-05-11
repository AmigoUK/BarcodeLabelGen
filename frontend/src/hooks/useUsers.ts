import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { CreateUserResponse, Role, User } from "../lib/types";

const USERS_KEY = ["admin", "users"] as const;

export function useUsers() {
  return useQuery({
    queryKey: USERS_KEY,
    queryFn: () => api<{ users: User[] }>("/api/admin/users").then((r) => r.users),
  });
}

type CreateUserInput = {
  email: string;
  role: Role;
  language: string;
  temporary_password: string;
};

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateUserInput) =>
      api<CreateUserResponse>("/api/admin/users", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

type UpdateUserInput = {
  id: number;
  patch: Partial<{ role: Role; is_active: boolean; language: string }>;
};

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: UpdateUserInput) =>
      api<User>(`/api/admin/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

export function useResetUserPassword() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) =>
      api<{ user: User; temporary_password: string }>(`/api/admin/users/${id}/reset-password`, {
        method: "POST",
        body: JSON.stringify({ new_temporary_password: password }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}
