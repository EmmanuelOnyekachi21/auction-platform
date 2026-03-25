import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PublicRoute from './components/common/PublicRoute';
import ProtectedRoute from './components/common/ProtectedRoute';
import AuthLayout from './components/layout/AuthLayout';
import MainLayout from './components/layout/MainLayout';

// 📝 Import our new Auth Pages
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import VerifyEmailPage from './pages/auth/VerifyEmailPage';
import ResetPasswordPage from './pages/auth/ResetPasswordPage';

// 📝 Import Profile Pages
import MyProfilePage from './pages/profile/MyProfilePage';
import BecomeSellerPage from './pages/profile/BecomeSellerPage';
import PublicProfilePage from './pages/profile/PublicProfilePage';

// 📝 Import Admin Pages
import VerifySellersPage from './pages/admin/VerifySellersPage';

// 🛠️ Create a Query Client for React Query
const queryClient = new QueryClient();

// 🚧 Placeholder Dashboard (Will build this soon!)
const Dashboard = () => (
  <div className="container mt-5 text-center">
    <h1>🚀 Welcome to your Dashboard!</h1>
    <p className="lead">This area is only for authenticated users.</p>
    <button className="btn btn-danger" onClick={() => {
      localStorage.removeItem('auth-storage');
      window.location.href = '/login';
    }}>
      Logout
    </button>
  </div>
);

// 📧 Simple Email Sent Info Page
const EmailSentPage = () => (
  <div className="container mt-5 text-center card shadow p-5">
    <div className="h1 mb-4">📧</div>
    <h2>Verification Email Sent!</h2>
    <p className="lead">Please check your inbox (and spam) to verify your account before logging in.</p>
    <button className="btn btn-primary" onClick={() => window.location.href = '/login'}>Back to Login</button>
  </div>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public Routes (Wrapped in AuthLayout) */}
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

          {/* Protected Routes (The VIP Section) */}
          <Route element={<ProtectedRoute />}>
            <Route element={<MainLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/profile" element={<MyProfilePage />} />
              <Route path="/become-seller" element={<BecomeSellerPage />} />
              <Route path="/admin/verify-sellers" element={<VerifySellersPage />} />
            </Route>
          </Route>

          {/* Public Profile Route (No auth required) */}
          <Route element={<MainLayout />}>
            <Route path="/users/:userId" element={<PublicProfilePage />} />
          </Route>

          {/* Default Redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
