/**
 * Navbar.jsx — KaraKaja Top Navigation
 * Fintech-grade: fixed top, white, wallet widget, user avatar dropdown.
 */
import { useState, useRef, useEffect } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../store/authStore';
import { walletActions } from '../../api/wallet';
import { getKYCStatus } from '../../api/kyc';
import {
  FiMenu, FiX, FiHome, FiGrid, FiHelpCircle,
  FiCreditCard, FiBell, FiUser, FiLogOut,
  FiShield, FiSettings, FiShoppingBag, FiChevronDown, FiList, FiAlertCircle,
} from 'react-icons/fi';
import './Navbar.css';

/** Format Naira */
const fmtNaira = (n) => {
  const v = parseFloat(n) || 0;
  return v.toLocaleString('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0, maximumFractionDigits: 0 });
};

/** Initials circle */
function Avatar({ user, showDot, needsKYC }) {
  const initials = `${(user?.first_name?.[0] || '').toUpperCase()}${(user?.last_name?.[0] || '').toUpperCase()}`;
  const title = [
    showDot && !needsKYC ? 'You have items awaiting confirmation' : null,
    needsKYC ? 'Complete identity verification' : null,
    !showDot ? `${user?.first_name || ''} ${user?.last_name || ''}` : null,
  ].filter(Boolean).join(' · ');
  return (
    <div className="bw-avatar" title={title} style={{ position: 'relative' }}>
      {initials || <FiUser size={14} />}
      {showDot && (
        <span style={{
          position: 'absolute', top: -2, right: -2,
          width: 10, height: 10, borderRadius: '50%',
          backgroundColor: '#D97706',
          border: '2px solid var(--card-bg)',
        }} />
      )}
    </div>
  );
}

export default function Navbar() {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuthStore();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Wallet balance (only fetch when authenticated)
  const { data: wallet } = useQuery({
    queryKey: ['wallet'],
    queryFn: walletActions.getWallet,
    enabled: isAuthenticated,
    staleTime: 60_000,
    retry: 1,
  });

  // Check for orders awaiting buyer's delivery confirmation
  const { data: pendingOrders } = useQuery({
    queryKey: ['pending-confirmations'],
    queryFn: async () => {
      const res = await apiClient.get('/users/me/orders?role=buyer&status=shipped&limit=50');
      return res.data?.data ?? res.data?.items ?? [];
    },
    enabled: isAuthenticated,
    staleTime: 60_000,
    retry: 1,
  });
  const hasPendingConfirmations = (pendingOrders?.length ?? 0) > 0;

  // KYC status — show amber dot if user is still on Tier 1
  const { data: kycData } = useQuery({
    queryKey: ['kyc-status'],
    queryFn: getKYCStatus,
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  });
  const needsKYC = isAuthenticated && kycData?.current_tier === 'TIER_1';

  const balance = parseFloat(wallet?.available_funds ?? wallet?.available_balance ?? 0);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleLogout = () => {
    setDropdownOpen(false);
    logout();
    navigate('/login');
  };

  return (
    <nav className="bw-navbar" id="main-navbar">
      <div className="bw-navbar__inner container">
        {/* Brand */}
        <Link to="/" className="bw-navbar__brand">
          <FiGrid size={22} />
          <span className="karakaja-logo">KaraKaja</span>
        </Link>

        {/* Nav Links (desktop) */}
        <div className="bw-navbar__links d-none d-lg-flex">
          <NavLink to="/dashboard" className={({ isActive }) => `bw-nav-link ${isActive ? 'bw-nav-link--active' : ''}`}>
            <FiHome size={15} /> Home
          </NavLink>
          <NavLink to="/auctions" className={({ isActive }) => `bw-nav-link ${isActive ? 'bw-nav-link--active' : ''}`}>
            <FiShoppingBag size={15} /> Auctions
          </NavLink>
          <NavLink to="/how-it-works" className={({ isActive }) => `bw-nav-link ${isActive ? 'bw-nav-link--active' : ''}`}>
            <FiHelpCircle size={15} /> How It Works
          </NavLink>
          {user?.role === 'ADMIN' && (
            <NavLink to="/admin/verify-sellers" className={({ isActive }) => `bw-nav-link ${isActive ? 'bw-nav-link--active' : ''}`}>
              <FiShield size={15} /> Admin
            </NavLink>
          )}
        </div>

        {/* Right Side */}
        <div className="bw-navbar__right">
          {isAuthenticated ? (
            <>
              {/* Wallet Widget */}
              <Link to="/wallet" className="bw-wallet-widget" id="navbar-wallet-widget">
                <FiCreditCard size={16} />
                <span className="bw-wallet-widget__amount">{fmtNaira(balance)}</span>
              </Link>

              {/* Notification Bell */}
              <button className="bw-icon-btn" aria-label="Notifications" id="navbar-notifications-btn">
                <FiBell size={18} />
                <span className="bw-badge">0</span>
              </button>

              {/* User Dropdown */}
              <div className="bw-dropdown" ref={dropdownRef}>
                <button
                  className="bw-dropdown__trigger"
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  aria-expanded={dropdownOpen}
                  id="navbar-user-dropdown"
                >
                  <Avatar user={user} showDot={hasPendingConfirmations || needsKYC} needsKYC={needsKYC} />
                  <span className="bw-dropdown__name d-none d-md-inline">
                    {user?.first_name || 'Account'}
                  </span>
                  <FiChevronDown size={14} className={`bw-dropdown__chevron ${dropdownOpen ? 'bw-dropdown__chevron--open' : ''}`} />
                </button>
                {dropdownOpen && (
                  <div className="bw-dropdown__menu">
                    <Link to="/profile" className="bw-dropdown__item" onClick={() => setDropdownOpen(false)}>
                      <FiUser size={15} /> My Profile
                    </Link>
                    <Link to="/wallet" className="bw-dropdown__item" onClick={() => setDropdownOpen(false)}>
                      <FiCreditCard size={15} /> Wallet
                    </Link>
                    <Link to="/my-bids" className="bw-dropdown__item" onClick={() => setDropdownOpen(false)}>
                      <FiList size={15} /> My Bids
                    </Link>
                    <Link to="/my-orders" className="bw-dropdown__item" onClick={() => setDropdownOpen(false)}>
                      <FiShoppingBag size={15} /> My Orders
                    </Link>
                    <Link to="/my-disputes" className="bw-dropdown__item" onClick={() => setDropdownOpen(false)}>
                      <FiAlertCircle size={15} /> My Disputes
                    </Link>
                    {user?.seller_profile?.is_verified ? (
                      <Link to="/seller/dashboard" className="bw-dropdown__item" onClick={() => setDropdownOpen(false)}>
                        <FiShoppingBag size={15} /> Seller Dashboard
                      </Link>
                    ) : (
                      <Link to="/become-seller" className="bw-dropdown__item" onClick={() => setDropdownOpen(false)}>
                        <FiSettings size={15} /> Become a Seller
                      </Link>
                    )}
                    <div className="bw-dropdown__divider" />
                    <button className="bw-dropdown__item bw-dropdown__item--danger" onClick={handleLogout}>
                      <FiLogOut size={15} /> Logout
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bw-navbar__auth-btns">
              <Link to="/login" className="btn btn-outline-primary btn-sm">Login</Link>
              <Link to="/register" className="btn btn-primary btn-sm">Register</Link>
            </div>
          )}

          {/* Mobile Toggle */}
          <button className="bw-icon-btn d-lg-none" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle menu">
            {mobileOpen ? <FiX size={20} /> : <FiMenu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="bw-mobile-menu d-lg-none">
          <NavLink to="/dashboard" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
            <FiHome size={16} /> Home
          </NavLink>
          <NavLink to="/auctions" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
            <FiShoppingBag size={16} /> Auctions
          </NavLink>
          <NavLink to="/how-it-works" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
            <FiHelpCircle size={16} /> How It Works
          </NavLink>
          {isAuthenticated && (
            <>
              <NavLink to="/profile" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
                <FiUser size={16} /> Profile
              </NavLink>
              <NavLink to="/wallet" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
                <FiCreditCard size={16} /> Wallet
              </NavLink>
              <NavLink to="/my-bids" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
                <FiList size={16} /> My Bids
              </NavLink>
              <NavLink to="/my-orders" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
                <FiShoppingBag size={16} /> My Orders
              </NavLink>
              <NavLink to="/my-disputes" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
                <FiAlertCircle size={16} /> My Disputes
              </NavLink>
              {user?.seller_profile?.is_verified ? (
                <NavLink to="/seller/dashboard" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
                  <FiShoppingBag size={16} /> Seller Dashboard
                </NavLink>
              ) : (
                <NavLink to="/become-seller" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
                  <FiSettings size={16} /> Become a Seller
                </NavLink>
              )}
            </>
          )}
          {user?.role === 'ADMIN' && (
            <NavLink to="/admin/verify-sellers" className="bw-mobile-link" onClick={() => setMobileOpen(false)}>
              <FiShield size={16} /> Admin
            </NavLink>
          )}
        </div>
      )}
    </nav>
  );
}
