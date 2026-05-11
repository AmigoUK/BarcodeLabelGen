import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppLayout } from "./layouts/AppLayout";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EditorPage } from "./pages/EditorPage";
import { LoginPage } from "./pages/LoginPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { UsersPage } from "./pages/admin/UsersPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/change-password" element={<ChangePasswordPage />} />

        {/* Editor lives outside AppLayout — it has its own full-screen chrome. */}
        <Route
          path="/templates/:id/edit"
          element={
            <ProtectedRoute>
              <EditorPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout>
                <DashboardPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/templates"
          element={
            <ProtectedRoute>
              <AppLayout>
                <TemplatesPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute adminOnly>
              <AppLayout>
                <UsersPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
