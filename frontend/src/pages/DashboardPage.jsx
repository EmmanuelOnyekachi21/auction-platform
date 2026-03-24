/**
 * DashboardPage.jsx — A Protected Page
 *
 * This is a placeholder page that only authenticated users can see.
 * It demonstrates how to use the useAuth() hook to access user data
 * and the logout function.
 */

import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function DashboardPage() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <div className="container mt-5">
            <div className="row">
                <div className="col-md-8 mx-auto">
                    <div className="card shadow-sm">
                        <div className="card-body p-4">
                            <div className="d-flex justify-content-between align-items-center mb-4">
                                <h2 className="card-title mb-0">Dashboard</h2>
                                <button
                                    className="btn btn-outline-danger btn-sm"
                                    onClick={handleLogout}
                                >
                                    Logout
                                </button>
                            </div>

                            <div className="alert alert-success" role="alert">
                                Welcome, <strong>{user?.first_name} {user?.last_name}</strong>!
                                You are logged in.
                            </div>

                            <div className="card bg-light">
                                <div className="card-body">
                                    <h5 className="card-title">Your Profile</h5>
                                    <ul className="list-unstyled mb-0">
                                        <li><strong>Email:</strong> {user?.email}</li>
                                        <li><strong>Role:</strong> {user?.role}</li>
                                        <li>
                                            <strong>Email Verified:</strong>{' '}
                                            {user?.is_email_verified ? (
                                                <span className="badge bg-success">Yes</span>
                                            ) : (
                                                <span className="badge bg-warning text-dark">No</span>
                                            )}
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
