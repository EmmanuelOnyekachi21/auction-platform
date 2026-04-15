/**
 * KYCPage.jsx — Identity Verification (KYC Tiers)
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FiCheckCircle, FiAlertCircle, FiArrowUp, FiShield, FiX,
} from 'react-icons/fi';
import { getKYCStatus, verifyBVN } from '../../api/kyc';
import './KYCPage.css';

const formatNaira = (n) =>
  Number(n || 0).toLocaleString('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0 });

/* ── BVN Modal ─────────────────────────────────────────────────────────────── */
function BVNModal({ onClose, onSuccess }) {
  const [bvnValue, setBvnValue] = useState('');
  const [bvnDisplay, setBvnDisplay] = useState('');
  const [dob, setDob] = useState('');
  const [error, setError] = useState('');
  const [verified, setVerified] = useState(false);

  const handleBvnBlur = () => {
    if (bvnValue.length === 11) setBvnDisplay('*******' + bvnValue.slice(-4));
  };
  const handleBvnFocus = () => setBvnDisplay(bvnValue);

  const mutation = useMutation({
    mutationFn: () => verifyBVN({ bvn: bvnValue, date_of_birth: dob }),
    onSuccess: (data) => {
      setVerified(true);
      onSuccess(data);
      setTimeout(onClose, 800);
    },
    onError: (err) => {
      const msg = err?.response?.data?.message || err?.response?.data?.detail || 'Verification failed. Please check your details.';
      const remaining = err?.response?.data?.remaining_attempts;
      setError(remaining !== undefined ? `${msg} (${remaining} attempt${remaining !== 1 ? 's' : ''} remaining)` : msg);
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    if (bvnValue.length !== 11) { setError('BVN must be exactly 11 digits.'); return; }
    if (!dob) { setError('Date of birth is required.'); return; }
    mutation.mutate();
  };

  return (
    <div className="kyc-modal-overlay" onClick={onClose}>
      <div className="kyc-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="kyc-modal__header">
          <h2 className="kyc-modal__title">Verify Your Identity</h2>
          <button className="kyc-modal__close" onClick={onClose} aria-label="Close"><FiX size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} noValidate>
          <div className="kyc-modal__body">
            <div className="kyc-form-group">
              <label className="kyc-form-label">BVN (Bank Verification Number)</label>
              <input
                type="text"
                className={`kyc-form-input ${error ? 'kyc-form-input--error' : ''}`}
                value={bvnDisplay}
                onChange={(e) => {
                  const raw = e.target.value.replace(/\D/g, '').slice(0, 11);
                  setBvnValue(raw);
                  setBvnDisplay(raw);
                }}
                onBlur={handleBvnBlur}
                onFocus={handleBvnFocus}
                placeholder="Enter your 11-digit BVN"
                inputMode="numeric"
                maxLength={11}
                disabled={mutation.isPending}
              />
            </div>
            <div className="kyc-form-group">
              <label className="kyc-form-label">Date of Birth</label>
              <input
                type="date"
                className={`kyc-form-input ${error ? 'kyc-form-input--error' : ''}`}
                value={dob}
                onChange={(e) => { setDob(e.target.value); setError(''); }}
                disabled={mutation.isPending}
              />
            </div>
            {error && <p className="kyc-form-error"><FiAlertCircle size={13} /> {error}</p>}
            <div className="kyc-security-notice">
              <FiShield size={16} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>Your BVN is encrypted and used only for identity verification. We never store your full BVN.</span>
            </div>
          </div>
          <div className="kyc-modal__footer">
            <button type="button" className="kyc-btn-ghost" onClick={onClose} disabled={mutation.isPending || verified}>Cancel</button>
            <button type="submit" className="kyc-verify-btn" disabled={mutation.isPending || verified}>
              {verified
                ? <><FiCheckCircle size={15} /> Verified!</>
                : mutation.isPending
                  ? <><span className="kyc-spinner" /> Verifying…</>
                  : 'Verify Identity'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Main Page ─────────────────────────────────────────────────────────────── */
export default function KYCPage() {
  const queryClient = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [justVerified, setJustVerified] = useState(false);

  const { data: status, isLoading } = useQuery({
    queryKey: ['kyc-status'],
    queryFn: getKYCStatus,
  });

  const tier2Complete = (status?.tier_2_complete ?? false) || justVerified;
  const tier2Status = justVerified ? 'verified' : (status?.tier_2_verification_status ?? 'none');

  const steps = [
    { label: 'Tier 1', state: 'complete' },
    { label: 'Tier 2', state: tier2Complete ? 'complete' : 'active' },
    { label: 'Tier 3', state: 'future' },
  ];

  const handleVerifySuccess = (data) => {
    setJustVerified(true);
    if (data) {
      queryClient.setQueryData(['kyc-status'], data);
    }
  };

  if (isLoading) {
    return (
      <div className="kyc-page">
        <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Loading verification status…</div>
      </div>
    );
  }

  return (
    <div className="kyc-page">
      <h1 className="kyc-page__title">Identity Verification</h1>
      <p className="kyc-page__subtitle">Complete verification to unlock higher bid limits and withdrawals.</p>

      {/* ── Progress Steps ── */}
      <div className="kyc-steps">
        {steps.map((step, i) => (
          <div key={step.label} style={{ display: 'contents' }}>
            <div className="kyc-step">
              <div className={`kyc-step__circle kyc-step__circle--${step.state}`}>
                {step.state === 'complete' ? <FiCheckCircle size={16} /> : i + 1}
              </div>
              <span className={`kyc-step__label kyc-step__label--${step.state}`}>{step.label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`kyc-step-connector ${steps[i + 1].state !== 'future' || step.state === 'complete' ? 'kyc-step-connector--complete' : ''}`} />
            )}
          </div>
        ))}
      </div>

      {/* ── Tier 1 Card ── */}
      <div className="kyc-card">
        <div className="kyc-card__header">
          <span className="kyc-card__icon"><FiCheckCircle size={20} color="#16A34A" /></span>
          <span className="kyc-card__title">Tier 1 — Basic Verification</span>
          <span className="kyc-card__status kyc-card__status--complete">Complete</span>
        </div>
        <div className="kyc-card__body">
          <div className="kyc-verified-row"><FiCheckCircle size={14} color="#16A34A" /> Email Verified ✓</div>
          <div className="kyc-verified-row"><FiCheckCircle size={14} color="#16A34A" /> Phone Verified ✓</div>
        </div>
      </div>

      {/* ── Tier 2 Card ── */}
      <div className="kyc-card">
        <div className="kyc-card__header">
          <span className="kyc-card__icon">
            {tier2Complete
              ? <FiCheckCircle size={20} color="#16A34A" />
              : tier2Status === 'pending_review'
                ? <FiAlertCircle size={20} color="#2563EB" />
                : tier2Status === 'rejected'
                  ? <FiAlertCircle size={20} color="#DC2626" />
                  : <FiAlertCircle size={20} color="#D97706" />}
          </span>
          <span className="kyc-card__title">
            {tier2Complete
              ? 'Tier 2 — Identity Verified'
              : tier2Status === 'pending_review'
                ? 'Tier 2 — Under Review'
                : 'Tier 2 — Identity Verification Required'}
          </span>
          <span className={`kyc-card__status ${
            tier2Complete ? 'kyc-card__status--complete'
            : tier2Status === 'pending_review' ? 'kyc-card__status--review'
            : tier2Status === 'rejected' ? 'kyc-card__status--rejected'
            : 'kyc-card__status--pending'
          }`}>
            {tier2Complete ? 'Complete'
              : tier2Status === 'pending_review' ? 'Under Review'
              : tier2Status === 'rejected' ? 'Rejected'
              : 'Action Required'}
          </span>
        </div>
        <div className="kyc-card__body">
          {tier2Complete ? (
            <div className="kyc-verified-row">
              <FiCheckCircle size={14} color="#16A34A" />
              Identity verified
            </div>
          ) : tier2Status === 'pending_review' ? (
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
              <FiAlertCircle size={14} color="#2563EB" style={{ flexShrink: 0, marginTop: 2 }} />
              <span>Your BVN submission is being reviewed. This usually takes a few minutes. You can leave this page — we'll update your status automatically.</span>
            </div>
          ) : tier2Status === 'rejected' ? (
            <>
              <div style={{ fontSize: '0.875rem', color: '#DC2626', marginBottom: '0.75rem', display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
                <FiAlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Verification failed. Please check your details and try again.</span>
              </div>
              <button className="kyc-verify-btn" onClick={() => setShowModal(true)}>
                <FiShield size={15} /> Try Again
              </button>
            </>
          ) : (
            <>
              <ul className="kyc-benefits-list">
                {[
                  'Bid up to ₦500,000',
                  'Wallet balance up to ₦2,000,000',
                  'Enable withdrawals',
                ].map((benefit) => (
                  <li key={benefit}>
                    <FiArrowUp size={14} color="var(--primary)" />
                    {benefit}
                  </li>
                ))}
              </ul>
              <button className="kyc-verify-btn" onClick={() => setShowModal(true)}>
                <FiShield size={15} /> Verify Now
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Tier 3 Card ── */}
      <div className="kyc-card kyc-card--muted">
        <div className="kyc-card__header">
          <span className="kyc-card__icon"><FiAlertCircle size={20} color="var(--text-muted)" /></span>
          <span className="kyc-card__title">Tier 3 — Enhanced Verification</span>
          <span className="kyc-card__status kyc-card__status--soon">Coming Soon</span>
        </div>
        <div className="kyc-card__body">
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: 0 }}>
            Enhanced verification for high-volume traders. Available in a future update.
          </p>
        </div>
      </div>

      {/* ── Current Limits Card ── */}
      {status?.limits && (
        <div className="kyc-card">
          <div className="kyc-card__header">
            <span className="kyc-card__title">Current Limits</span>
          </div>
          <div className="kyc-card__body">
            <div className="kyc-limits-grid">
              <div className="kyc-limit-row">
                <span className="kyc-limit-label">Bid Limit</span>
                <span className="kyc-limit-value">{formatNaira(status.limits.max_bid)}</span>
              </div>
              <div className="kyc-limit-row">
                <span className="kyc-limit-label">Wallet Limit</span>
                <span className="kyc-limit-value">{formatNaira(status.limits.max_wallet_balance)}</span>
              </div>
              <div className="kyc-limit-row">
                <span className="kyc-limit-label">Withdrawals</span>
                <span className={`kyc-limit-value ${Number(status.limits.max_daily_withdrawal) === 0 ? 'kyc-limit-value--amber' : ''}`}>
                  {Number(status.limits.max_daily_withdrawal) === 0
                    ? 'Not available'
                    : formatNaira(status.limits.max_daily_withdrawal)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {showModal && (
        <BVNModal
          onClose={() => setShowModal(false)}
          onSuccess={handleVerifySuccess}
        />
      )}
    </div>
  );
}
