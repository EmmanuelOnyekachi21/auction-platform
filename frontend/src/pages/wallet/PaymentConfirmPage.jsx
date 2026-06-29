/**
 * PaymentConfirmPage.jsx — Payment Confirmation Screen
 * Polls backend payment status instead of trusting redirect params alone.
 */
import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { FiCheckCircle, FiXCircle, FiLoader, FiArrowRight, FiShield } from 'react-icons/fi';
import apiClient from '../../api/client';

const MAX_POLLS = 12;       // 12 × 2.5s = 30s max wait
const POLL_INTERVAL = 2500;

const PaymentConfirmPage = () => {
  const { paymentId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('processing'); // processing | success | failed
  const [message, setMessage] = useState('We are verifying your transaction with Paystack. This usually takes a few seconds.');
  const pollCount = useRef(0);
  const timerRef = useRef(null);

  useEffect(() => {
    const urlStatus = searchParams.get('status');

    // Paystack cancelled/failed — no need to poll
    if (urlStatus === 'cancelled' || urlStatus === 'failed') {
      setStatus('failed');
      setMessage('The payment was cancelled or failed. No funds were debited from your account.');
      return;
    }

    if (!paymentId) {
      setStatus('failed');
      setMessage('No payment reference found. If you were debited, please contact support.');
      return;
    }

    const poll = async () => {
      pollCount.current += 1;

      try {
        const res = await apiClient.get(`/wallets/payments/${paymentId}/status`);
        const data = res.data;

        if (data.status === 'COMPLETED') {
          setStatus('success');
          setMessage(`Your wallet has been credited ₦${parseFloat(data.amount).toLocaleString()}. You can now use your balance to bid on auctions.`);
          queryClient.invalidateQueries({ queryKey: ['wallet'] });
          return; // stop polling
        }

        if (data.status === 'FAILED') {
          setStatus('failed');
          setMessage('Payment verification failed. If you were debited, please contact our support team.');
          return;
        }

        // Still PENDING — keep polling if under limit
        if (pollCount.current >= MAX_POLLS) {
          // Webhook may be delayed — show a softer message
          setStatus('failed');
          setMessage(
            'We haven\'t received payment confirmation yet. If you completed the payment, your wallet will be credited automatically within a few minutes. Check back shortly.'
          );
          return;
        }

        timerRef.current = setTimeout(poll, POLL_INTERVAL);
      } catch (err) {
        console.error('Payment status poll error:', err);
        if (pollCount.current >= MAX_POLLS) {
          setStatus('failed');
          setMessage('Could not confirm payment status. If you were debited, please contact support.');
        } else {
          timerRef.current = setTimeout(poll, POLL_INTERVAL);
        }
      }
    };

    // Start first poll after a short delay to give webhook time to arrive
    timerRef.current = setTimeout(poll, 2000);

    return () => clearTimeout(timerRef.current);
  }, [paymentId, searchParams, queryClient]);

  const renderStatus = () => {
    switch (status) {
      case 'success':
        return { icon: <FiCheckCircle size={64} color="var(--success)" />, title: 'Payment Successful', color: 'success' };
      case 'failed':
        return { icon: <FiXCircle size={64} color="var(--danger)" />, title: 'Payment Not Confirmed', color: 'danger' };
      default:
        return { icon: <FiLoader size={64} color="var(--primary)" className="spin" />, title: 'Confirming Payment…', color: 'primary' };
    }
  };

  const config = renderStatus();

  return (
    <div className="container" style={{ maxWidth: 500, padding: '4rem 1.5rem' }}>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 'var(--radius-xl)', textAlign: 'center', overflow: 'hidden' }}>
        <div style={{ height: 6, background: `var(--${config.color})`, opacity: status === 'processing' ? 0.3 : 1 }} />

        <div className="card-body p-4 p-md-5">
          <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'center' }}>
            {config.icon}
          </div>

          <h2 style={{ fontWeight: 800, fontSize: '1.5rem', marginBottom: '0.75rem', letterSpacing: '-0.02em' }}>
            {config.title}
          </h2>

          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem', marginBottom: '2rem', lineHeight: 1.6 }}>
            {message}
          </p>

          {status !== 'processing' && (
            <div className="d-grid gap-3">
              <button
                onClick={() => navigate('/wallet')}
                className="btn btn-primary w-100"
                style={{ padding: '0.75rem', fontWeight: 600, borderRadius: 'var(--radius)' }}
              >
                Go to Wallet Dashboard <FiArrowRight size={18} className="ms-2" />
              </button>
              {status === 'failed' && (
                <button
                  onClick={() => navigate('/wallet')}
                  className="btn btn-outline-secondary w-100"
                  style={{ padding: '0.75rem', fontWeight: 600, borderRadius: 'var(--radius)' }}
                >
                  Try Again
                </button>
              )}
            </div>
          )}

          {status === 'processing' && (
            <div style={{ background: 'var(--surface)', padding: '1rem', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
              <div className="d-flex align-items-center justify-content-center gap-2" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontWeight: 500 }}>
                <FiShield size={14} />
                Secure Verification via Paystack
              </div>
            </div>
          )}
        </div>

        {status === 'success' && (
          <div style={{ background: 'var(--success-light)', padding: '0.75rem', fontSize: '0.75rem', fontWeight: 600, color: 'var(--success)' }}>
            TRANSACTION CONFIRMED • ID: {paymentId || '---'}
          </div>
        )}
      </div>

      <div className="text-center mt-4">
        <Link to="/how-it-works" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', textDecoration: 'none' }}>
          Need help? Contact KaraKaja Support
        </Link>
      </div>

      <style>{`
        .spin { animation: spin 2s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default PaymentConfirmPage;
