/**
 * MainLayout.jsx — Wraps all authenticated pages
 * Includes Navbar and Footer.
 */
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import { FiGrid } from 'react-icons/fi';

export default function MainLayout() {
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
            Nohans
          </div>
          <div>&copy; {new Date().getFullYear()} Nohans. All rights reserved.</div>
        </div>
      </footer>
    </div>
  );
}
