/**
 * MainLayout.jsx — Wraps all authenticated pages
 * Includes Navbar and Footer.
 */
import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import { FiGrid } from 'react-icons/fi';
import { useAuthStore } from '../../store/authStore';
import apiClient from '../../api/client';

export default function MainLayout() {
  const { isAuthenticated, updateUser } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      apiClient.get('/users/me')
        .then((res) => updateUser(res.data))
        .catch((err) => console.error("Failed to sync user profile in MainLayout:", err));
    }
  }, [isAuthenticated, updateUser]);

  return (
    <div className="d-flex flex-column" style={{ minHeight: '100vh' }}>
      <Navbar />
      <main className="flex-grow-1">
        <Outlet />
      </main>
      <footer style={{
        background: 'var(--card-bg)',
        borderTop: '1px solid var(--border)',
        padding: '1.5rem 0',
        color: 'var(--text-muted)',
        fontSize: '0.8125rem',
      }}>
        <div className="container d-flex flex-column flex-md-row align-items-center justify-content-between gap-2">
          <div className="d-flex align-items-center gap-2" style={{ fontWeight: 700, color: 'var(--text-secondary)' }}>
            <FiGrid size={16} style={{ color: 'var(--primary)' }} />
            <span className="karakaja-logo" style={{ fontSize: '1rem' }}>KaraKaja</span>
          </div>
          <div>&copy; {new Date().getFullYear()} KaraKaja. All rights reserved.</div>
        </div>
      </footer>
    </div>
  );
}
