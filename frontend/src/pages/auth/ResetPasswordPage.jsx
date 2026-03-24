import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useState } from 'react';
import { authActions } from '../../api/auth';

// 🛡️ Schema 1: Just the email (for requesting reset)
const requestSchema = z.object({
  email: z.email('Invalid email address'),
});

// 🛡️ Schema 2: New passwords (for actual reset)
const resetSchema = z
  .object({
    new_password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  });

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');

  const requestForm = useForm({ resolver: zodResolver(requestSchema) });
  const resetForm = useForm({ resolver: zodResolver(resetSchema) });

  const onRequestSubmit = async (data) => {
    setStatus('loading');
    try {
      await authActions.forgotPassword(data.email);
      setStatus('success');
      setMessage(
        `We've sent a password reset link to ${data.email}. Please check your inbox (and spam folder)!`
      );
    } catch (err) {
      setStatus('error');
      setMessage(err.response?.data?.detail || 'Something went wrong. Please try again later.');
    }
  };

  const onResetSubmit = async (data) => {
    setStatus('loading');
    try {
      await authActions.resetPassword(token, data.new_password, data.confirm_password);
      setStatus('success');
      setMessage('Your password has been reset successfully! Redirecting you to login...');
      setTimeout(() => navigate('/login'), 3000);
    } catch (err) {
      setStatus('error');
      setMessage(err.response?.data?.detail || 'Failed to reset password. The link may be expired.');
    }
  };

  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-5 card shadow p-4">
          <h2 className="text-center mb-4">{token ? 'Set New Password' : 'Reset Your Password'}</h2>

          {status === 'success' && <div className="alert alert-success">{message}</div>}
          {status === 'error' && <div className="alert alert-danger">{message}</div>}

          {!token && status !== 'success' && (
            <form onSubmit={requestForm.handleSubmit(onRequestSubmit)}>
              <p className="text-muted mb-4 text-center">
                Enter your email address and we'll send you a link to reset your password.
              </p>
              <div className="mb-3">
                <input
                  type="email"
                  {...requestForm.register('email')}
                  className={`form-control ${
                    requestForm.formState.errors.email ? 'is-invalid' : ''
                  }`}
                  placeholder="name@example.com"
                />
                <div className="invalid-feedback">
                  {requestForm.formState.errors.email?.message}
                </div>
              </div>
              <button
                type="submit"
                disabled={status === 'loading'}
                className="btn btn-primary w-100 mb-3"
              >
                {status === 'loading' ? 'Sending...' : 'Send Reset Link'}
              </button>
            </form>
          )}

          {token && status !== 'success' && (
            <form onSubmit={resetForm.handleSubmit(onResetSubmit)}>
              <div className="mb-3">
                <label className="form-label">New Password</label>
                <input
                  type="password"
                  {...resetForm.register('new_password')}
                  className={`form-control ${
                    resetForm.formState.errors.new_password ? 'is-invalid' : ''
                  }`}
                />
                <div className="invalid-feedback">
                  {resetForm.formState.errors.new_password?.message}
                </div>
              </div>
              <div className="mb-4">
                <label className="form-label">Confirm New Password</label>
                <input
                  type="password"
                  {...resetForm.register('confirm_password')}
                  className={`form-control ${
                    resetForm.formState.errors.confirm_password ? 'is-invalid' : ''
                  }`}
                />
                <div className="invalid-feedback">
                  {resetForm.formState.errors.confirm_password?.message}
                </div>
              </div>
              <button
                type="submit"
                disabled={status === 'loading'}
                className="btn btn-success w-100 mb-3"
              >
                {status === 'loading' ? 'Saving...' : 'Update Password'}
              </button>
            </form>
          )}

          <div className="text-center">
            <Link to="/login" className="text-decoration-none">
              ← Back to Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
