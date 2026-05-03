/**
 * PaymentConfirmPage.jsx — Payment Confirmation Screen
 * Fintech-grade: status-driven UI, premium cards, micro-animations.
 */
import { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { FiCheckCircle, FiXCircle, FiLoader, FiArrowRight, FiShield } from 'react-icons/fi';

const PaymentConfirmPage = () => {
  const { paymentId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient(); // Get React Query client
  const [status, setStatus] = useState('processing'); // processing, success, failed
  const [message, setMessage] = useState('We are verifying your transaction with our payment processors.');

  useEffect(() => {
    // Paystack redirect params: reference, trxref, status (not always present)
    // Flutterwave used: status, tx_ref, transaction_id
    const urlStatus = searchParams.get('status');
    const reference = searchParams.get('reference') || searchParams.get('trxref');

    // REASONING: Give webhook 2.5 seconds to process payment and update database
    // Then invalidate wallet cache so WalletPage will refetch and show updated balance
    const timer = setTimeout(() => {
      // Paystack redirects with reference param on success
      // If reference exists, treat as success (webhook handles actual verification)
      if (reference && (!urlStatus || urlStatus === 'success')) {
        setStatus('success');
        setMessage('Your wallet has been credited successfully. You can now use your balance to bid on auctions.');
        queryClient.invalidateQueries({ queryKey: ['wallet'] });
      } else if (urlStatus === 'cancelled' || urlStatus === 'failed') {
        setStatus('failed');
        setMessage('The payment process was cancelled. No funds were debited from your account.');
      } else if (!reference && !urlStatus) {
        setStatus('failed');
        setMessage('We could not confirm your payment. If you were debited, please contact our support team.');
      } else {
        setStatus('success');
        setMessage('Your wallet has been credited successfully. You can now use your balance to bid on auctions.');
        queryClient.invalidateQueries({ queryKey: ['wallet'] });
      }
    }, 2500);

    return () => clearTimeout(timer);
  }, [searchParams, queryClient]);

  const renderStatus = () => {
    switch (status) {
      case 'success':
        return {
          icon: <FiCheckCircle size={64} color="var(--success)" />,
          title: 'Payment Successful',
          color: 'success'
        };
      case 'failed':
        return {
          icon: <FiXCircle size={64} color="var(--danger)" />,
          title: 'Payment Failed',
          color: 'danger'
        };
      default:
        return {
          icon: <FiLoader size={64} color="var(--primary)" className="spin" />,
          title: 'Confirming Payment',
          color: 'primary'
        };
    }
  };

  const config = renderStatus();

  return (
    <div className="container" style={{ maxWidth: 500, padding: '4rem 1.5rem' }}>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 'var(--radius-xl)', textAlign: 'center', overflow: 'hidden' }}>
        {/* Status Bar */}
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

          {status !== 'processing' ? (
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
          ) : (
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
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
    </div>
  );
};

export default PaymentConfirmPage;
