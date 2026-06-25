/**
 * ProtectedRoute.jsx — Route Guard
 *
 * This component wraps any page that requires authentication.
 *
 * HOW IT WORKS:
 * - It checks useAuth() to see if a user is logged in.
 * - If YES → it renders the child page normally.
 * - If NO → it redirects the user to /login.
 *
 * Usage in App.jsx:
 *   <Route path="/dashboard" element={
 *     <ProtectedRoute>
 *       <DashboardPage />
 *     </ProtectedRoute>
 *   } />
 */

import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
    const { isAuthenticated, loading } = useAuth();

    // While we're still checking localStorage, show a loading spinner
    if (loading) {
        return (
            <div className="d-flex justify-content-center align-items-center vh-100">
                <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                </div>
            </div>
        );
    }

    // Not logged in? Redirect to login page.
    // "replace" prevents the login page from appearing in browser history
    // so the user can't press the "Back" button to get back to the protected page.
    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    // Logged in — show the protected page
    return children;
}
