/**
 * AuthLayout.jsx — Wraps public auth pages (login, register, etc.)
 * Centered card layout with KaraKaja branding on a subtle --surface background.
 */
import { Outlet } from 'react-router-dom';
import { FiGrid } from 'react-icons/fi';

export default function AuthLayout() {
    return (
        <div style={{
            minHeight: '100vh',
            background: 'var(--surface)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '2rem 1rem',
        }}>
            <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    fontSize: '1.75rem',
                    fontWeight: 800,
                    color: 'var(--primary)',
                    letterSpacing: '-0.02em',
                    marginBottom: '0.25rem',
                }}>
                    <FiGrid size={28} />
                    <span className="karakaja-logo" style={{ fontSize: 'inherit' }}>KaraKaja</span>
                </div>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
                    Nigeria&rsquo;s Premier Auction Marketplace
                </p>
            </div>
            <div style={{ width: '100%', maxWidth: 420 }}>
                <Outlet />
            </div>
        </div>
    );
}
