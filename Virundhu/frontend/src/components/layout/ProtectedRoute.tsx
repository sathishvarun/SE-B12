import { rememberNext } from "@/lib/next";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { LogoMark } from "@/components/layout/Logo";
import { useAuth } from "@/context/AuthContext";

/** Waits for the saved session, then sends signed-out visitors to /login. */
export function ProtectedRoute() {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) {
    return (
      <div className="flex min-h-dvh items-center justify-center" aria-busy="true">
        <LogoMark className="h-12 w-12 animate-pulse" />
      </div>
    );
  }
  if (!user) {
    rememberNext(location.pathname + location.search);
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return <Outlet />;
}
