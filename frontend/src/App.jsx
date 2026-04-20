import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PublicRoute from './components/common/PublicRoute';
import ProtectedRoute from './components/common/ProtectedRoute';
import AuthLayout from './components/layout/AuthLayout';
import MainLayout from './components/layout/MainLayout';
import { ToastProvider } from './components/common/Toast';
import WalletPage from './pages/wallet/WalletPage';
import TransactionsPage from './pages/wallet/TransactionsPage';
import PaymentConfirmPage from './pages/wallet/PaymentConfirmPage';
import { FiMail, FiArrowRight, FiTrendingUp, FiSearch, FiShoppingBag } from 'react-icons/fi';
import { useAuthStore } from './store/authStore';

// Auction / Browse Pages
import HomePage from './pages/auctions/HomePage';
import AuctionDetailPage from './pages/auctions/AuctionDetailPage';
import HowItWorksPage from './pages/HowItWorksPage';

// Auth Pages
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import VerifyEmailPage from './pages/auth/VerifyEmailPage';
import ResetPasswordPage from './pages/auth/ResetPasswordPage';

// Profile Pages
import MyProfilePage from './pages/profile/MyProfilePage';
import BecomeSellerPage from './pages/profile/BecomeSellerPage';
import PublicProfilePage from './pages/profile/PublicProfilePage';

// Bids Pages
import MyBidsPage from './pages/bids/MyBidsPage';

// Orders Pages
import MyOrdersPage from './pages/orders/MyOrdersPage';
import OrderDetailPage from './pages/orders/OrderDetailPage';

// Dispute Pages
import DisputeDetailPage from './pages/disputes/DisputeDetailPage';
import MyDisputesPage from './pages/disputes/MyDisputesPage';

// Admin Pages
import VerifySellersPage from './pages/admin/VerifySellersPage';
import AdminDisputesPage from './pages/admin/AdminDisputesPage';

// Seller Pages
import SellerDashboardPage from './pages/seller/SellerDashboardPage';
import SellerPendingPage from './pages/seller/SellerPendingPage';
import CreateAuctionPage from './pages/seller/CreateAuctionPage';

// KYC
import KYCPage from './pages/kyc/KYCPage';

const queryClient = new QueryClient();

/** Derive where "Start Selling" should navigate based on seller status */
const getSellerRoute = (user) => {
  const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPERUSER';
  if (isAdmin) return '/seller/dashboard';
  if (!user?.seller_profile)               return '/become-seller';
  if (!user.seller_profile.is_verified)    return '/seller/pending';
  return '/seller/dashboard';
};

// Homepage / Dashboard
const Dashboard = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const sellerRoute = getSellerRoute(user);
  const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPERUSER';

  // Smart seller label for the quick-actions list
  const sellerAction = (() => {
    if (isAdmin)                           return { label: 'Seller Dashboard', desc: 'Create and manage auctions' };
    if (!user?.seller_profile)             return { label: 'Start Selling', desc: 'Register as a seller to list items' };
    if (!user.seller_profile.is_verified)  return { label: 'Seller Status',  desc: 'Check the status of your application' };
    return { label: 'Seller Dashboard', desc: 'Manage your auctions and earnings' };
  })();

  return (
    <div>
      {/* Hero Section */}
      <section style={{
        background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)',
        color: '#fff',
        padding: '4rem 0 3.5rem',
      }}>
        <div className="container text-center" style={{ maxWidth: 720 }}>
          <h1 style={{ fontWeight: 800, fontSize: 'clamp(2rem, 5vw, 3rem)', letterSpacing: '-0.03em', marginBottom: '0.75rem' }}>
            Bid. Win. Own.
          </h1>
          <p style={{ fontSize: '1.0625rem', opacity: 0.85, marginBottom: '2rem', lineHeight: 1.7 }}>
            Nigeria&rsquo;s most trusted online auction marketplace.
            Discover unique items, place competitive bids, and win premium products at unbeatable prices.
          </p>
          <div className="d-flex justify-content-center gap-3 flex-wrap">
            <Link to="/auctions" className="btn btn-light" style={{ fontWeight: 600, padding: '0.625rem 1.5rem', color: 'var(--primary)' }}>
              <FiSearch size={16} /> Browse Auctions
            </Link>
            <button
              className="btn"
              style={{ fontWeight: 600, padding: '0.625rem 1.5rem', background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)' }}
              onClick={() => navigate(sellerRoute)}
            >
              <FiShoppingBag size={16} /> Start Selling
            </button>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section style={{ background: 'var(--card-bg)', borderBottom: '1px solid var(--border)', padding: '1.5rem 0' }}>
        <div className="container">
          <div className="row text-center g-3">
            {[
              { icon: <FiShoppingBag size={20} />, value: '2,450+', label: 'Active Auctions' },
              { icon: <FiTrendingUp size={20} />, value: '18,000+', label: 'Items Sold' },
              { icon: <FiSearch size={20} />, value: '45,000+', label: 'Registered Users' },
            ].map((stat, i) => (
              <div className="col-4" key={i}>
                <div className="d-flex flex-column align-items-center gap-1">
                  <div style={{ color: 'var(--primary)' }}>{stat.icon}</div>
                  <div style={{ fontWeight: 800, fontSize: '1.25rem', color: 'var(--text-primary)' }}>{stat.value}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>{stat.label}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Welcome Section */}
      <div className="container" style={{ maxWidth: 800, padding: '3rem 1.5rem' }}>
        <div className="card" style={{ borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
          <div style={{ padding: '2rem', background: 'var(--primary-50)', borderBottom: '1px solid var(--primary-light)' }}>
            <h3 style={{ fontWeight: 700, fontSize: '1.125rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
              Welcome back, {user?.first_name || 'there'}
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: 0 }}>
              Here are some quick actions to get you started.
            </p>
          </div>
          <div className="card-body p-0">
            {[
              { to: '/wallet', label: 'View Wallet', desc: 'Check your balance, fund or withdraw' },
              { to: '/profile', label: 'My Profile', desc: 'Update your details and bank info' },
              { to: sellerRoute, label: sellerAction.label, desc: sellerAction.desc },
            ].map((item, i) => (
              <Link key={i} to={item.to} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '1rem 1.5rem', borderBottom: i < 2 ? '1px solid var(--border)' : 'none',
                color: 'var(--text-primary)', textDecoration: 'none', transition: 'var(--transition-fast)',
              }}
                onMouseOver={e => e.currentTarget.style.background = 'var(--surface)'}
                onMouseOut={e => e.currentTarget.style.background = 'transparent'}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9375rem' }}>{item.label}</div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>{item.desc}</div>
                </div>
                <FiArrowRight size={16} style={{ color: 'var(--text-muted)' }} />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Email Sent Page
const EmailSentPage = () => (
  <div className="card" style={{ borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-md)', textAlign: 'center' }}>
    <div className="card-body p-4 p-md-5">
      <div style={{
        width: 56, height: 56, borderRadius: 'var(--radius-full)',
        background: 'var(--primary-50)', color: 'var(--primary)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 1.25rem',
      }}>
        <FiMail size={24} />
      </div>
      <h2 style={{ fontWeight: 700, fontSize: '1.25rem', marginBottom: '0.75rem' }}>Verification Email Sent</h2>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
        Please check your inbox (and spam folder) to verify your account before logging in.
      </p>
      <Link to="/login" className="btn btn-primary" style={{ padding: '0.5rem 2rem' }}>
        Back to Login
      </Link>
    </div>
  </div>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Auth Routes */}
            <Route element={<PublicRoute />}>
              <Route element={<AuthLayout />}>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/verify-email" element={<VerifyEmailPage />} />
                <Route path="/verify-email-sent" element={<EmailSentPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                <Route path="/forgot-password" element={<ResetPasswordPage />} />
              </Route>
            </Route>

            {/* Protected Routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<MainLayout />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/profile" element={<MyProfilePage />} />
                <Route path="/become-seller" element={<BecomeSellerPage />} />
                <Route path="/admin/verify-sellers" element={<VerifySellersPage />} />
                <Route path="/admin/disputes" element={<AdminDisputesPage />} />
                <Route path="/wallet" element={<WalletPage />} />
                <Route path="/wallet/transactions" element={<TransactionsPage />} />
                <Route path="/payment/:paymentId/confirm" element={<PaymentConfirmPage />} />
                <Route path="/my-bids" element={<MyBidsPage />} />
                <Route path="/my-orders" element={<MyOrdersPage />} />
                <Route path="/orders/:orderId" element={<OrderDetailPage />} />
                <Route path="/my-disputes" element={<MyDisputesPage />} />
                <Route path="/disputes/:disputeId" element={<DisputeDetailPage />} />
                <Route path="/seller/dashboard" element={<SellerDashboardPage />} />
                <Route path="/seller/pending" element={<SellerPendingPage />} />
                <Route path="/seller/create-auction" element={<CreateAuctionPage />} />
                <Route path="/kyc" element={<KYCPage />} />
              </Route>
            </Route>

            {/* Public Auction + Profile Routes (no auth required) */}
            <Route element={<MainLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/how-it-works" element={<HowItWorksPage />} />
              <Route path="/auctions" element={<HomePage />} />
              <Route path="/auctions/:auctionId" element={<AuctionDetailPage />} />
              <Route path="/users/:userId" element={<PublicProfilePage />} />
            </Route>

            {/* Default Redirect — send authenticated users to dashboard, everyone else to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}

export default App;
