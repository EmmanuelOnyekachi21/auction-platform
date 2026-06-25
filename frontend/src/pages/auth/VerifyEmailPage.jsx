import { useEffect, useState, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { authActions } from "../../api/auth";
import { FiCheckCircle, FiXCircle, FiLoader } from 'react-icons/fi';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('verifying');
  const [message, setMessage] = useState('');
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;
    const token = searchParams.get('token');
    const verify = async () => {
      if (!token) {
        setStatus('error');
        setMessage('No verification token found in the URL.');
        return;
      }
      try {
        await authActions.verifyEmail(token);
        setStatus('success');
        setMessage('Your email has been successfully verified! You can now log in.');
      } catch (err) {
        setStatus('error');
        setMessage(err.response?.data?.detail || 'Verification failed. The link may be expired.');
      }
    };
    verify();
  }, [searchParams]);

  const iconStyle = { width: 56, height: 56, borderRadius: 'var(--radius-full)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.25rem' };

  return (
    <div className="card" style={{ borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-md)', textAlign: 'center' }}>
      <div className="card-body p-4 p-md-5">
        {status === 'verifying' && (
          <div>
            <div style={{ ...iconStyle, background: 'var(--primary-50)', color: 'var(--primary)' }}>
              <FiLoader size={24} className="spinner-sm" style={{ width: 24, height: 24, border: 'none', animation: 'spin 1s linear infinite' }} />
            </div>
            <h3 style={{ fontWeight: 700, fontSize: '1.25rem' }}>Verifying your email</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Please wait a moment...</p>
          </div>
        )}
        {status === 'success' && (
          <div>
            <div style={{ ...iconStyle, background: 'var(--success-light)', color: 'var(--success)' }}>
              <FiCheckCircle size={28} />
            </div>
            <h3 style={{ fontWeight: 700, fontSize: '1.25rem', marginBottom: '0.75rem' }}>Verification Successful</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>{message}</p>
            <Link to="/login" className="btn btn-primary" style={{ padding: '0.5rem 2rem' }}>
              Go to Login
            </Link>
          </div>
        )}
        {status === 'error' && (
          <div>
            <div style={{ ...iconStyle, background: 'var(--danger-light)', color: 'var(--danger)' }}>
              <FiXCircle size={28} />
            </div>
            <h3 style={{ fontWeight: 700, fontSize: '1.25rem', marginBottom: '0.75rem' }}>Verification Failed</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>{message}</p>
            <Link to="/login" className="btn btn-outline-primary" style={{ padding: '0.5rem 2rem' }}>
              Return to Login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
