import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

/** Route guard — only ADMIN and SUPERUSER roles can pass through. */
export default function AdminRoute() {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPERUSER';
  if (!isAdmin) return <Navigate to="/" replace />;

  return <Outlet />;
}
