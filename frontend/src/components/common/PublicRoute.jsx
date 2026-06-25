import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

export default function PublicRoute() {
    const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

    // If already authenticated, skip the login/register pages and go to dashboard
    if (isAuthenticated) {
        return <Navigate to="/dashboard" replace />;
    }

    // Otherwise, allow access to the login/register pages
    return <Outlet />;
}
