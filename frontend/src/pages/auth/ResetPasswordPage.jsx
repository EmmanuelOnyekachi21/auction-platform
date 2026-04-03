import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useState } from 'react';
import { authActions } from '../../api/auth';
import { FiMail, FiLock, FiArrowLeft, FiArrowRight, FiCheckCircle } from 'react-icons/fi';

const requestSchema = z.object({ email: z.email('Invalid email address') });
const resetSchema = z.object({
  new_password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, { message: "Passwords don't match", path: ['confirm_password'] });

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
      setMessage(`We've sent a password reset link to ${data.email}. Please check your inbox.`);
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
      setMessage('Your password has been reset successfully! Redirecting to login...');
      setTimeout(() => navigate('/login'), 3000);
    } catch (err) {
      setStatus('error');
      const errorData = err.response?.data;
      let msg = 'Failed to reset password. The link may be expired.';
      if (errorData) {
        if (Array.isArray(errorData.details) && errorData.details.length > 0) {
          msg = errorData.details.map(e => e.message.replace(/^Value error,\s*/i, '')).join(', ');
        } else if (errorData.message) {
          msg = errorData.message;
        } else if (typeof errorData.detail === 'string') {
          msg = errorData.detail;
        }
      }
      setMessage(msg);
    }
  };

  const inputIcon = (Icon) => (
    <Icon size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
  );

  return (
    <div className="card" style={{ borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-md)' }}>
      <div className="card-body p-4 p-md-5">
        <h2 style={{ fontWeight: 800, fontSize: '1.5rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
          {token ? 'Set New Password' : 'Reset Your Password'}
        </h2>

        {status === 'success' && (
          <div style={{ padding: '1rem', background: 'var(--success-light)', border: '1px solid #BBF7D0', borderRadius: 'var(--radius)', color: 'var(--success)', fontSize: '0.8125rem', fontWeight: 500, margin: '1.25rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FiCheckCircle size={16} /> {message}
          </div>
        )}
        {status === 'error' && (
          <div style={{ padding: '0.75rem 1rem', background: 'var(--danger-light)', border: '1px solid #FECACA', borderRadius: 'var(--radius)', color: 'var(--danger)', fontSize: '0.8125rem', fontWeight: 500, margin: '1.25rem 0' }}>
            {message}
          </div>
        )}

        {!token && status !== 'success' && (
          <form onSubmit={requestForm.handleSubmit(onRequestSubmit)}>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
              Enter your email address and we will send you a link to reset your password.
            </p>
            <div className="mb-3">
              <div style={{ position: 'relative' }}>
                {inputIcon(FiMail)}
                <input type="email" {...requestForm.register('email')} className={`form-control ${requestForm.formState.errors.email ? 'is-invalid' : ''}`} placeholder="name@example.com" style={{ paddingLeft: '2.5rem' }} />
              </div>
              {requestForm.formState.errors.email && <div className="text-danger" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{requestForm.formState.errors.email.message}</div>}
            </div>
            <button type="submit" disabled={status === 'loading'} className="btn btn-primary w-100 mb-3" style={{ padding: '0.625rem', fontWeight: 600 }}>
              {status === 'loading' ? <><span className="spinner-sm" /> Sending...</> : <>Send Reset Link <FiArrowRight size={16} /></>}
            </button>
          </form>
        )}

        {token && status !== 'success' && (
          <form onSubmit={resetForm.handleSubmit(onResetSubmit)} style={{ marginTop: '1.5rem' }}>
            <div className="mb-3">
              <label className="form-label">New Password</label>
              <div style={{ position: 'relative' }}>
                {inputIcon(FiLock)}
                <input type="password" {...resetForm.register('new_password')} className={`form-control ${resetForm.formState.errors.new_password ? 'is-invalid' : ''}`} style={{ paddingLeft: '2.5rem' }} />
              </div>
              {resetForm.formState.errors.new_password && <div className="text-danger" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{resetForm.formState.errors.new_password.message}</div>}
            </div>
            <div className="mb-4">
              <label className="form-label">Confirm New Password</label>
              <div style={{ position: 'relative' }}>
                {inputIcon(FiLock)}
                <input type="password" {...resetForm.register('confirm_password')} className={`form-control ${resetForm.formState.errors.confirm_password ? 'is-invalid' : ''}`} style={{ paddingLeft: '2.5rem' }} />
              </div>
              {resetForm.formState.errors.confirm_password && <div className="text-danger" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{resetForm.formState.errors.confirm_password.message}</div>}
            </div>
            <button type="submit" disabled={status === 'loading'} className="btn btn-primary w-100 mb-3" style={{ padding: '0.625rem', fontWeight: 600 }}>
              {status === 'loading' ? <><span className="spinner-sm" /> Saving...</> : <>Update Password <FiArrowRight size={16} /></>}
            </button>
          </form>
        )}

        <div className="text-center" style={{ marginTop: '0.5rem' }}>
          <Link to="/login" style={{ fontSize: '0.8125rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <FiArrowLeft size={14} /> Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
