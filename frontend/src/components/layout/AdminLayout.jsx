import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  FiGrid, FiUsers, FiTag, FiShoppingBag,
  FiAlertCircle, FiDollarSign, FiSettings,
  FiMenu, FiX, FiLogOut,
} from 'react-icons/fi';
import { useAuthStore } from '../../store/authStore';

const NAV = [
  { to: '/admin/dashboard',       icon: FiGrid,        label: 'Dashboard' },
  { to: '/admin/users',           icon: FiUsers,       label: 'Users' },
  { to: '/admin/verify-sellers',  icon: FiTag,         label: 'Sellers' },
  { to: '/admin/auctions',        icon: FiTag,         label: 'Auctions' },
  { to: '/admin/orders',          icon: FiShoppingBag, label: 'Orders' },
  { to: '/admin/disputes',        icon: FiAlertCircle, label: 'Disputes' },
  { to: '/admin/financial',       icon: FiDollarSign,  label: 'Financial' },
  { to: '/admin/settings',        icon: FiSettings,    label: 'Settings' },
];

const SIDEBAR_W = 220;
const SIDEBAR_W_COLLAPSED = 60;

export default function AdminLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const w = collapsed ? SIDEBAR_W_COLLAPSED : SIDEBAR_W;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--body-bg)' }}>
      {/* ── Sidebar ── */}
      <aside style={{
        width: w, minWidth: w, background: 'var(--text-primary)',
        display: 'flex', flexDirection: 'column',
        position: 'fixed', top: 0, left: 0, bottom: 0,
        zIndex: 100, transition: 'width 0.2s ease',
        overflow: 'hidden',
      }}>
        {/* Logo + toggle */}
        <div style={{
          height: 60, display: 'flex', alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          padding: collapsed ? 0 : '0 1rem',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
        }}>
          {!collapsed && (
            <span className="karakaja-logo" style={{ fontSize: '1.1rem' }}>KaraKaja</span>
          )}
          <button
            onClick={() => setCollapsed(c => !c)}
            style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.6)', cursor: 'pointer', padding: 4 }}
          >
            {collapsed ? <FiMenu size={18} /> : <FiX size={18} />}
          </button>
        </div>

        {/* Nav links */}
        <nav style={{ flex: 1, padding: '0.75rem 0', overflowY: 'auto' }}>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center',
                gap: collapsed ? 0 : '0.75rem',
                justifyContent: collapsed ? 'center' : 'flex-start',
                padding: collapsed ? '0.75rem 0' : '0.625rem 1rem',
                color: isActive ? '#fff' : 'rgba(255,255,255,0.55)',
                background: isActive ? 'rgba(37,99,235,0.35)' : 'transparent',
                borderLeft: isActive ? '3px solid var(--primary)' : '3px solid transparent',
                textDecoration: 'none', fontSize: '0.875rem', fontWeight: 600,
                transition: 'all 0.15s',
              })}
              title={collapsed ? label : undefined}
            >
              <Icon size={17} style={{ flexShrink: 0 }} />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User + logout */}
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', padding: collapsed ? '0.75rem 0' : '0.75rem 1rem' }}>
          {!collapsed && (
            <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.45)', marginBottom: '0.5rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.email}
            </div>
          )}
          <button
            onClick={logout}
            style={{
              display: 'flex', alignItems: 'center', gap: collapsed ? 0 : '0.5rem',
              justifyContent: collapsed ? 'center' : 'flex-start',
              width: '100%', background: 'none', border: 'none',
              color: 'rgba(255,255,255,0.55)', cursor: 'pointer',
              fontSize: '0.8125rem', fontWeight: 600, padding: collapsed ? '0.5rem 0' : 0,
            }}
          >
            <FiLogOut size={15} />
            {!collapsed && 'Logout'}
          </button>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main style={{ marginLeft: w, flex: 1, transition: 'margin-left 0.2s ease', minWidth: 0 }}>
        <Outlet />
      </main>
    </div>
  );
}
