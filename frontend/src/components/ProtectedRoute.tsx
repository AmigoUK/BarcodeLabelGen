import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useMe } from "../hooks/useMe";

type Props = {
  children: ReactNode;
  /** When true, only admins are allowed; non-admins get bounced to dashboard. */
  adminOnly?: boolean;
};

export function ProtectedRoute({ children, adminOnly = false }: Props) {
  const { data: me, isLoading } = useMe();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        …
      </div>
    );
  }

  if (!me) return <Navigate to="/login" replace />;

  if (me.must_change_password) {
    return <Navigate to="/change-password" replace />;
  }

  if (adminOnly && me.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
