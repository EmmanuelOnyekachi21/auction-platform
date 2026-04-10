/**
 * WalletPage.jsx — KaraKaja Wallet Dashboard
    * Fintech - grade wallet with balance cards, fund / withdraw modals.
 * Uses react - icons exclusively.
 */
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, Link } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import apiClient from '../../api/client';
import { walletActions } from '../../api/wallet';
import { getKYCStatus } from '../../api/kyc';
import { useToast } from '../../components/common/Toast';
import {
    FiDollarSign, FiLock, FiShield, FiBarChart2,
    FiPlus, FiArrowDownLeft, FiList, FiRefreshCw,
    FiAlertCircle, FiInfo, FiCreditCard, FiX,
} from 'react-icons/fi';
import './WalletPage.css';

const formatNaira = (amount) => {
    const num = parseFloat(amount) || 0;
    return num.toLocaleString('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// ─── Skeleton Card ──────────────────────────────────────────────────────────
function SkeletonCard() {
    return (
        <div className="wallet-card wallet-card--skeleton">
            <div className="skeleton" style={{ width: 40, height: 40, borderRadius: 'var(--radius)' }} />
            <div className="skeleton" style={{ width: '60%', height: 14, marginTop: 12 }} />
            <div className="skeleton" style={{ width: '80%', height: 24, marginTop: 8 }} />
            <div className="skeleton" style={{ width: '50%', height: 12, marginTop: 8 }} />
        </div>
    );
}

// ─── Balance Card ───────────────────────────────────────────────────────────
function BalanceCard({ icon, label, amount, subtitle, colorClass }) {
    return (
        <div className={`wallet-card wallet-card--${colorClass}`}>
            <div className="wallet-card__icon">{icon}</div>
            <div className="wallet-card__label">{label}</div>
            <div className="wallet-card__amount">{formatNaira(amount)}</div>
            <div className="wallet-card__subtitle">{subtitle}</div>
        </div>
    );
}

// ─── Fund Modal ─────────────────────────────────────────────────────────────
function FundModal({ show, onClose }) {
    const [amount, setAmount] = useState('');
    const [amountError, setAmountError] = useState('');
    const [kycError, setKycError] = useState('');
    const { showToast } = useToast();

    const mutation = useMutation({
        mutationFn: (amt) => walletActions.fundWallet(amt),
        onSuccess: (data) => {
            if (data?.payment_link) {
                showToast('Redirecting to payment gateway...', 'info');
                window.location.href = data.payment_link;
            } else {
                showToast('Funding initiated successfully!', 'success');
                handleClose();
            }
        },
        onError: (error) => {
            const code = error?.response?.data?.code;
            const msg = error?.response?.data?.message ?? '';
            if (code === 'PERMISSION_DENIED' && msg.includes('wallet limit')) {
                setKycError(msg);
            } else {
                showToast(msg || 'Failed to initiate funding.', 'error');
            }
        },
    });

    const handleClose = () => { setAmount(''); setAmountError(''); setKycError(''); onClose(); };

    const handleSubmit = (e) => {
        e.preventDefault();
        const parsed = parseFloat(amount);
        if (!amount || isNaN(parsed)) { setAmountError('Please enter a valid amount.'); return; }
        if (parsed < 100) { setAmountError('Minimum funding amount is ₦100.'); return; }
        setAmountError('');
        mutation.mutate(parsed);
    };

    if (!show) return null;

    return (
        <div className="wallet-modal-overlay" onClick={handleClose}>
            <div className="wallet-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
                <div className="wallet-modal__header">
                    <div className="wallet-modal__header-icon wallet-modal__header-icon--green">
                        <FiPlus size={24} />
                    </div>
                    <h2 className="wallet-modal__title">Fund Wallet</h2>
                    <button className="wallet-modal__close" onClick={handleClose} aria-label="Close">
                        <FiX size={18} />
                    </button>
                </div>
                <form onSubmit={handleSubmit} noValidate>
                    <div className="wallet-modal__body">
                        <div className="wallet-form-group">
                            <label className="wallet-form-label">Amount</label>
                            <div className="wallet-input-wrapper">
                                <span className="wallet-input-prefix">₦</span>
                                <input id="fund-amount" type="number" className={`wallet-input ${amountError ? 'wallet-input--error' : ''}`}
                                    placeholder="Enter amount (min ₦100)" value={amount}
                                    onChange={(e) => { setAmount(e.target.value); if (amountError) setAmountError(''); }}
                                    min="100" step="any" disabled={mutation.isPending} />
                            </div>
                            {amountError && <p className="wallet-form-error">{amountError}</p>}
                        </div>
                        <div className="wallet-fee-notice">
                            <FiInfo size={16} />
                            <span><strong>0% platform fee</strong> — you pay exactly what you enter. Payments are processed securely via Flutterwave.</span>
                        </div>
                        {kycError && (
                            <div className="wallet-warning-box" style={{ marginTop: '0.75rem' }}>
                                <FiAlertCircle size={18} />
                                <div>
                                    <strong>Wallet limit reached</strong>
                                    <p>{kycError}</p>
                                    <Link to="/kyc" className="wallet-btn wallet-btn--primary wallet-btn--sm mt-2 d-inline-flex" onClick={handleClose}>
                                        Verify Identity
                                    </Link>
                                </div>
                            </div>
                        )}
                    </div>
                    <div className="wallet-modal__footer">
                        <button type="button" className="wallet-btn wallet-btn--ghost" onClick={handleClose} disabled={mutation.isPending}>Cancel</button>
                        <button type="submit" className="wallet-btn wallet-btn--primary" disabled={mutation.isPending}>
                            {mutation.isPending ? <><span className="wallet-spinner" /> Processing...</> : 'Proceed to Payment'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// ─── Withdraw Modal ─────────────────────────────────────────────────────────
function WithdrawModal({ show, onClose, availableBalance, user }) {
    const [amount, setAmount] = useState('');
    const [amountError, setAmountError] = useState('');
    const [kycError, setKycError] = useState('');
    const { showToast } = useToast();
    const queryClient = useQueryClient();

    const bankDetails = user?.profile || user;
    const hasBankDetails = bankDetails?.account_name && bankDetails?.account_number && bankDetails?.bank_code;

    const mutation = useMutation({
        mutationFn: (amt) => walletActions.withdrawFunds(amt),
        onSuccess: () => {
            showToast('Withdrawal request submitted successfully!', 'success');
            queryClient.invalidateQueries({ queryKey: ['wallet'] });
            handleClose();
        },
        onError: (error) => {
            const code = error?.response?.data?.code;
            const msg = error?.response?.data?.message ?? '';
            if (code === 'PERMISSION_DENIED' && msg.includes('BVN verification')) {
                setKycError(msg);
            } else {
                showToast(msg || 'Withdrawal failed. Please try again.', 'error');
            }
        },
    });

    const handleClose = () => { setAmount(''); setAmountError(''); setKycError(''); onClose(); };

    const handleSubmit = (e) => {
        e.preventDefault();
        const parsed = parseFloat(amount);
        if (!amount || isNaN(parsed)) { setAmountError('Please enter a valid amount.'); return; }
        if (parsed < 100) { setAmountError('Minimum withdrawal is ₦100.'); return; }
        if (parsed > parseFloat(availableBalance)) { setAmountError(`Amount exceeds available balance of ${formatNaira(availableBalance)}.`); return; }
        setAmountError('');
        mutation.mutate(parsed);
    };

    if (!show) return null;

    return (
        <div className="wallet-modal-overlay" onClick={handleClose}>
            <div className="wallet-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
                <div className="wallet-modal__header">
                    <div className="wallet-modal__header-icon wallet-modal__header-icon--amber">
                        <FiArrowDownLeft size={24} />
                    </div>
                    <h2 className="wallet-modal__title">Withdraw Funds</h2>
                    <button className="wallet-modal__close" onClick={handleClose} aria-label="Close">
                        <FiX size={18} />
                    </button>
                </div>
                {kycError ? (
                    <div className="wallet-modal__body">
                        <div className="wallet-warning-box">
                            <FiAlertCircle size={20} />
                            <div>
                                <strong>Withdrawals not available</strong>
                                <p>{kycError}</p>
                                <Link to="/kyc" className="wallet-btn wallet-btn--primary wallet-btn--sm mt-2 d-inline-flex" onClick={handleClose}>
                                    Verify Identity
                                </Link>
                            </div>
                        </div>
                        <div className="wallet-modal__footer">
                            <button className="wallet-btn wallet-btn--ghost" onClick={handleClose}>Close</button>
                        </div>
                    </div>
                ) : !hasBankDetails ? (
                    <div className="wallet-modal__body">
                        <div className="wallet-warning-box">
                            <FiAlertCircle size={20} />
                            <div>
                                <strong>No bank details found</strong>
                                <p>Please set up your bank details in your profile before withdrawing.</p>
                                <Link to="/profile" className="wallet-btn wallet-btn--primary wallet-btn--sm mt-2 d-inline-flex">Go to Profile</Link>
                            </div>
                        </div>
                        <div className="wallet-modal__footer">
                            <button className="wallet-btn wallet-btn--ghost" onClick={handleClose}>Close</button>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} noValidate>
                        <div className="wallet-modal__body">
                            <div className="wallet-bank-card">
                                <div className="wallet-bank-card__header"><FiCreditCard size={16} /> Withdrawal Account</div>
                                <div className="wallet-bank-card__details">
                                    {[
                                        { label: 'Account Name', value: bankDetails.account_name },
                                        { label: 'Account Number', value: bankDetails.account_number, mono: true },
                                        { label: 'Bank Code', value: bankDetails.bank_code },
                                    ].map((r, i) => (
                                        <div className="wallet-bank-card__row" key={i}>
                                            <span className="wallet-bank-card__field">{r.label}</span>
                                            <span className={`wallet-bank-card__value ${r.mono ? 'wallet-bank-card__value--mono' : ''}`}>{r.value}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="wallet-form-group">
                                <label className="wallet-form-label">Amount</label>
                                <div className="wallet-input-wrapper">
                                    <span className="wallet-input-prefix">₦</span>
                                    <input id="withdraw-amount" type="number" className={`wallet-input ${amountError ? 'wallet-input--error' : ''}`}
                                        placeholder="Enter amount" value={amount}
                                        onChange={(e) => { setAmount(e.target.value); if (amountError) setAmountError(''); }}
                                        min="100" max={availableBalance} step="any" disabled={mutation.isPending} />
                                </div>
                                {amountError ? <p className="wallet-form-error">{amountError}</p> : <p className="wallet-form-hint">Maximum: {formatNaira(availableBalance)}</p>}
                            </div>
                        </div>
                        <div className="wallet-modal__footer">
                            <button type="button" className="wallet-btn wallet-btn--ghost" onClick={handleClose} disabled={mutation.isPending}>Cancel</button>
                            <button type="submit" className="wallet-btn wallet-btn--amber" disabled={mutation.isPending}>
                                {mutation.isPending ? <><span className="wallet-spinner" /> Processing...</> : 'Request Withdrawal'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}

// ─── Main Wallet Page ───────────────────────────────────────────────────────
export default function WalletPage() {
    const { user: authUser } = useAuthStore();
    const { showToast } = useToast();
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();
    const [showFundModal, setShowFundModal] = useState(false);
    const [showWithdrawModal, setShowWithdrawModal] = useState(false);

    // Fetch wallet data
    const { data: wallet, isLoading, isError, error, refetch } = useQuery({
        queryKey: ['wallet'],
        queryFn: walletActions.getWallet,
        staleTime: 30_000,
        refetchOnWindowFocus: true,
    });

    // Fetch user profile with bank details
    const { data: userProfile } = useQuery({
        queryKey: ['userProfile'],
        queryFn: async () => {
            const response = await apiClient.get('/users/me');
            return response.data;
        },
        staleTime: 60_000, // Cache for 1 minute
    });

    // Fetch KYC status for upgrade banner
    const { data: kycStatus } = useQuery({
        queryKey: ['kyc-status'],
        queryFn: getKYCStatus,
        staleTime: 5 * 60_000,
    });

    useEffect(() => {
        const paymentStatus = searchParams.get('payment');
        if (paymentStatus === 'success') {
            showToast('Payment successful! Your wallet has been funded.', 'success', 6000);
            queryClient.invalidateQueries({ queryKey: ['wallet'] });
        } else if (paymentStatus === 'failed') {
            showToast('Payment failed or was cancelled. Please try again.', 'error', 6000);
        }
        if (paymentStatus) {
            setSearchParams((prev) => { const next = new URLSearchParams(prev); next.delete('payment'); return next; }, { replace: true });
        }
    }, []);

    const availableBalance = parseFloat(wallet?.available_funds ?? 0);
    const lockedBalance = parseFloat(wallet?.locked_funds ?? 0);
    const escrowBalance = parseFloat(wallet?.escrow_funds ?? 0);
    const totalBalance = availableBalance + lockedBalance + escrowBalance;

    return (
        <div className="wallet-page">
            {/* Header */}
            <div className="wallet-page__header">
                <div className="wallet-page__header-text">
                    <h1 className="wallet-page__title">My Wallet</h1>
                    <p className="wallet-page__subtitle">Manage your funds, top up, and track balances.</p>
                </div>
                <button className="wallet-refresh-btn" onClick={() => refetch()} disabled={isLoading} title="Refresh balances">
                    <FiRefreshCw size={18} className={isLoading ? 'wallet-spin' : ''} />
                </button>
            </div>

            {isError ? (
                <div className="wallet-error-box">
                    <FiAlertCircle size={24} />
                    <div>
                        <strong>Failed to load wallet data.</strong>
                        <p>{error?.response?.data?.detail || 'Please check your connection and try again.'}</p>
                        <button className="wallet-btn wallet-btn--primary wallet-btn--sm" onClick={() => refetch()}>Retry</button>
                    </div>
                </div>
            ) : (
                <>
                    <div className="wallet-cards-grid">
                        {isLoading ? (
                            <><SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
                        ) : (
                            <>
                                <BalanceCard icon={<FiDollarSign size={20} />} label="Available Balance" amount={availableBalance} subtitle="Free to use for bidding" colorClass="green" />
                                <BalanceCard icon={<FiLock size={20} />} label="Locked Balance" amount={lockedBalance} subtitle="Reserved for active bids" colorClass="amber" />
                                <BalanceCard icon={<FiShield size={20} />} label="Escrow Balance" amount={escrowBalance} subtitle="Pending delivery confirmation" colorClass="blue" />
                                <BalanceCard icon={<FiBarChart2 size={20} />} label="Total Balance" amount={totalBalance} subtitle="Sum of all balances" colorClass="dark" />
                            </>
                        )}
                    </div>

                    {/* KYC upgrade banner */}
                    {!isLoading && kycStatus?.current_tier === 'TIER_1' && (
                        <div className="wallet-kyc-banner">
                            <FiAlertCircle size={16} />
                            <span>Verify your identity to enable withdrawals and higher bid limits.</span>
                            <Link to="/kyc">Verify Now</Link>
                        </div>
                    )}

                    <div className="wallet-actions">
                        <button id="fund-wallet-btn" className="wallet-btn wallet-btn--primary wallet-btn--lg" onClick={() => setShowFundModal(true)} disabled={isLoading}>
                            <FiPlus size={20} /> Fund Wallet
                        </button>
                        <button id="withdraw-btn" className="wallet-btn wallet-btn--outline wallet-btn--lg" onClick={() => setShowWithdrawModal(true)} disabled={isLoading}>
                            <FiArrowDownLeft size={20} /> Withdraw
                        </button>
                        <Link to="/wallet/transactions" id="view-transactions-btn" className="wallet-btn wallet-btn--ghost wallet-btn--lg">
                            <FiList size={20} /> Transaction History
                        </Link>
                    </div>

                    {!isLoading && wallet && (
                        <div className="wallet-info-strip">
                            <div className="wallet-info-item">
                                <span className="wallet-info-label">Wallet ID</span>
                                <span className="wallet-info-value wallet-info-value--mono">{wallet.id ? `#${wallet.id}` : '---'}</span>
                            </div>
                            <div className="wallet-info-item">
                                <span className="wallet-info-label">Currency</span>
                                <span className="wallet-info-value">{wallet.currency || 'NGN'}</span>
                            </div>
                            <div className="wallet-info-item">
                                <span className="wallet-info-label">Last Updated</span>
                                <span className="wallet-info-value">{wallet.updated_at ? new Date(wallet.updated_at).toLocaleString('en-NG') : 'Just now'}</span>
                            </div>
                        </div>
                    )}
                </>
            )}

            <FundModal show={showFundModal} onClose={() => setShowFundModal(false)} />
            <WithdrawModal show={showWithdrawModal} onClose={() => setShowWithdrawModal(false)} availableBalance={availableBalance} user={userProfile} />
        </div>
    );
}
