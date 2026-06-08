import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useNavigate, Link } from 'react-router-dom';
import { useState } from 'react';
import { authActions } from '../../api/auth';
import { useAuthStore } from '../../store/authStore';
import { FiMail, FiLock, FiEye, FiEyeOff, FiArrowRight, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';

const loginSchema = z.object({
  email: z.email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
  remember_me: z.boolean().optional(),
});

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [apiError, setApiError] = useState(null);
  const [unverifiedEmail, setUnverifiedEmail] = useState(null);
  const [resendState, setResendState] = useState('idle'); // 'idle' | 'sending' | 'sent' | 'error'
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleResend = async () => {
    setResendState('sending');
    try {
      await authActions.resendVerification(unverifiedEmail);
      setResendState('sent');
    } catch {
      setResendState('error');
    }
  };

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { remember_me: false },
  });

  const onSubmit = async (data) => {
    setIsSubmitting(true);
    setApiError(null);
    setUnverifiedEmail(null);
    setResendState('idle');
    try {
      const response = await authActions.login(data);
      setAuth(response.user, response.access_token, response.refresh_token);
      navigate('/dashboard');
    } catch (err) {
      const errorData = err.response?.data;

      // Specific handling for unverified email — show a distinct banner
      if (errorData?.code === 'EMAIL_NOT_VERIFIED') {
        setUnverifiedEmail(data.email);
        return;
      }

      let errorMessage = 'Invalid email or password';
      if (errorData) {
        if (errorData.message) errorMessage = errorData.message;
        else if (typeof errorData.detail === 'string') errorMessage = errorData.detail;
        else if (errorData.detail?.message) errorMessage = errorData.detail.message;
        else if (Array.isArray(errorData.detail)) errorMessage = errorData.detail.map(e => e.msg).join(', ');
      }
      setApiError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="card" style={{ borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-md)' }}>
      <div className="card-body p-4 p-md-5">
        <h2 style={{ fontWeight: 800, fontSize: '1.5rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
          Welcome back
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.75rem' }}>
          Sign in to your KaraKaja account
        </p>

        {/* Unverified email — distinct banner with guidance */}
        {unverifiedEmail && (
          <div style={{
            padding: '0.875rem 1rem',
            background: '#FFF7ED',
            border: '1px solid #FED7AA',
            borderRadius: 'var(--radius)',
            marginBottom: '1.25rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.8125rem', color: '#C2410C', marginBottom: '0.3rem' }}>
              <FiAlertCircle size={14} /> Email not verified
            </div>
            <div style={{ fontSize: '0.8125rem', color: '#9A3412', lineHeight: 1.6, marginBottom: '0.75rem' }}>
              We sent a verification link to <strong>{unverifiedEmail}</strong>. Please check your inbox and spam folder.
            </div>

            {resendState === 'sent' ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8125rem', fontWeight: 600, color: '#15803D' }}>
                <FiCheckCircle size={14} /> New link sent — check your inbox.
              </div>
            ) : (
              <button
                type="button"
                onClick={handleResend}
                disabled={resendState === 'sending'}
                style={{
                  background: 'none', border: '1px solid #C2410C', borderRadius: 'var(--radius)',
                  color: '#C2410C', fontWeight: 600, fontSize: '0.8125rem',
                  padding: '0.3rem 0.75rem', cursor: resendState === 'sending' ? 'not-allowed' : 'pointer',
                  opacity: resendState === 'sending' ? 0.6 : 1,
                }}
              >
                {resendState === 'sending' ? 'Sending…' : resendState === 'error' ? 'Failed — try again' : 'Resend verification email'}
              </button>
            )}
          </div>
        )}

        {/* Generic error */}
        {apiError && (
          <div style={{
            padding: '0.75rem 1rem',
            background: 'var(--danger-light)',
            border: '1px solid #FECACA',
            borderRadius: 'var(--radius)',
            color: 'var(--danger)',
            fontSize: '0.8125rem',
            fontWeight: 500,
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}>
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="mb-3">
            <label className="form-label">Email Address</label>
            <div style={{ position: 'relative' }}>
              <FiMail size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="email"
                {...register('email')}
                className={`form-control ${errors.email ? 'is-invalid' : ''}`}
                placeholder="name@example.com"
                style={{ paddingLeft: '2.5rem' }}
              />
            </div>
            {errors.email && <div className="text-danger" style={{ fontSize: '0.8125rem', marginTop: '0.25rem' }}>{errors.email.message}</div>}
          </div>

          <div className="mb-3">
            <label className="form-label">Password</label>
            <div style={{ position: 'relative' }}>
              <FiLock size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type={showPassword ? 'text' : 'password'}
                {...register('password')}
                className={`form-control ${errors.password ? 'is-invalid' : ''}`}
                style={{ paddingLeft: '2.5rem', paddingRight: '2.5rem' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.25rem',
                }}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
              </button>
            </div>
            {errors.password && <div className="text-danger" style={{ fontSize: '0.8125rem', marginTop: '0.25rem' }}>{errors.password.message}</div>}
          </div>

          <div className="mb-4 d-flex justify-content-between align-items-center">
            <div className="form-check">
              <input type="checkbox" {...register('remember_me')} className="form-check-input" id="remember" />
              <label className="form-check-label" htmlFor="remember" style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                Remember me
              </label>
            </div>
            <Link to="/forgot-password" style={{ fontSize: '0.8125rem', fontWeight: 600 }}>
              Forgot password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn btn-primary w-100 mb-3"
            style={{ padding: '0.625rem', fontWeight: 600 }}
          >
            {isSubmitting ? (
              <><span className="spinner-sm" /> Signing in...</>
            ) : (
              <>Sign In <FiArrowRight size={16} /></>
            )}
          </button>

          <p className="text-center mb-0" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Don&rsquo;t have an account?{' '}
            <Link to="/register" style={{ fontWeight: 600 }}>Create one</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
