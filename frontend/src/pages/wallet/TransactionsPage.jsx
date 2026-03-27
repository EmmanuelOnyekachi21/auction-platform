/**
 * TransactionsPage.jsx — Nohans Transaction History
 * Filter pills, paginated table, react-icons throughout.
 */
import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { walletActions } from '../../api/wallet';
import {
    FiArrowDown, FiArrowUp, FiLock, FiUnlock,
    FiShield, FiRefreshCw, FiChevronLeft, FiChevronRight,
    FiAlertCircle, FiPlus, FiList,
} from 'react-icons/fi';
import './TransactionsPage.css';

const LIMIT = 20;

const FILTERS = [
    { label: 'All', value: '' },
    { label: 'Deposits', value: 'DEPOSIT' },
    { label: 'Withdrawals', value: 'WITHDRAWAL' },
    { label: 'Bid Locks', value: 'BID_LOCK' },
    { label: 'Bid Unlocks', value: 'BID_UNLOCK' },
    { label: 'Escrow', value: 'ESCROW' },
    { label: 'Refunds', value: 'REFUND' },
];

const TX_ICONS = {
    DEPOSIT: <FiArrowDown size={14} />,
    WITHDRAWAL: <FiArrowUp size={14} />,
    BID_LOCK: <FiLock size={14} />,
    BID_UNLOCK: <FiUnlock size={14} />,
    ESCROW: <FiShield size={14} />,
    REFUND: <FiRefreshCw size={14} />,
};

function TxIcon({ type, direction }) {
    const isCredit = direction === 'CREDIT';
    return TX_ICONS[type] || (isCredit ? <FiArrowDown size={14} /> : <FiArrowUp size={14} />);
}

const formatNaira = (amount) => {
    const num = parseFloat(amount) || 0;
    return num.toLocaleString('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const formatDate = (iso) => {
    if (!iso) return '---';
    const d = new Date(iso);
    return `${d.toLocaleDateString('en-NG', { day: 'numeric', month: 'short', year: 'numeric' })}, ${d.toLocaleTimeString('en-NG', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
};

const typeLabel = (type) => ({
    DEPOSIT: 'Deposit', WITHDRAWAL: 'Withdrawal', BID_LOCK: 'Bid Lock',
    BID_UNLOCK: 'Bid Unlock', ESCROW: 'Escrow Hold', REFUND: 'Refund',
}[type] || type || 'Transaction');

function SkeletonRow() {
    return (
        <tr className="tx-skeleton-row">
            <td>
                <div className="tx-icon-cell">
                    <div className="skeleton" style={{ width: 38, height: 38, borderRadius: 10 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="skeleton" style={{ width: '80%', height: 13, marginBottom: 5 }} />
                        <div className="skeleton" style={{ width: '40%', height: 11 }} />
                    </div>
                </div>
            </td>
            <td><div className="skeleton" style={{ width: 140, height: 12 }} /></td>
            <td className="tx-amount-cell"><div className="skeleton" style={{ width: 100, height: 14, marginLeft: 'auto' }} /></td>
            <td className="tx-amount-cell"><div className="skeleton" style={{ width: 100, height: 12, marginLeft: 'auto' }} /></td>
        </tr>
    );
}

function TransactionRow({ tx }) {
    // API might return 'type' or 'transaction_type'
    const type = tx.type || tx.transaction_type;
    const isCredit = tx.direction === 'CREDIT';
    const amount = parseFloat(tx.amount) || 0;

    return (
        <tr className="tx-row">
            <td>
                <div className="tx-icon-cell">
                    <div className={`tx-icon-wrap tx-icon-wrap--${isCredit ? 'credit' : 'debit'}`}>
                        <TxIcon type={type} direction={tx.direction} />
                    </div>
                    <div className="tx-desc-block">
                        <span className="tx-desc-primary" title={tx.description || typeLabel(type)}>
                            {tx.description || typeLabel(type)}
                        </span>
                        <span className="tx-type-badge">{typeLabel(type)}</span>
                    </div>
                </div>
            </td>
            <td><span className="tx-date">{formatDate(tx.created_at)}</span></td>
            <td className="tx-amount-cell">
                <span className={`tx-amount tx-amount--${isCredit ? 'credit' : 'debit'}`}>
                    {isCredit ? '+' : '-'}{formatNaira(amount)}
                </span>
                <span className={`tx-direction-badge tx-direction-badge--${isCredit ? 'credit' : 'debit'}`}>
                    {isCredit ? 'Credit' : 'Debit'}
                </span>
            </td>
            <td className="tx-amount-cell">
                <span className="tx-balance-after">
                    {tx.balance_after != null ? formatNaira(tx.balance_after) : '---'}
                </span>
            </td>
        </tr>
    );
}

function EmptyState({ activeFilter }) {
    return (
        <div className="tx-empty">
            <FiList size={48} className="tx-empty__icon" />
            <h3 className="tx-empty__title">No transactions yet</h3>
            <p className="tx-empty__body">
                {activeFilter
                    ? `No "${FILTERS.find(f => f.value === activeFilter)?.label}" transactions found.`
                    : 'Your transaction history will appear here once you start using your wallet.'}
            </p>
            {!activeFilter && (
                <Link to="/wallet" className="tx-btn tx-btn--primary">
                    <FiPlus size={16} /> Fund Wallet
                </Link>
            )}
        </div>
    );
}

export default function TransactionsPage() {
    const [activeType, setActiveType] = useState('');
    const [page, setPage] = useState(1);

    const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
        queryKey: ['transactions', activeType, page],
        queryFn: () => walletActions.getTransactions({ type: activeType, page, limit: LIMIT }),
        staleTime: 30_000,
        keepPreviousData: true,
    });

    // Handle different API formats: { data, pagination: { total, total_pages } } OR { items, total, pages }
    const transactions = useMemo(() => data?.data || data?.items || [], [data]);
    const total = useMemo(() => data?.pagination?.total ?? data?.total ?? 0, [data]);
    const totalPages = useMemo(() => data?.pagination?.total_pages ?? data?.pages ?? 1, [data]);

    const from = total === 0 ? 0 : (page - 1) * LIMIT + 1;
    const to = Math.min(page * LIMIT, total);

    const handleFilterChange = (value) => { setActiveType(value); setPage(1); };

    return (
        <div className="tx-page">
            <div className="tx-page__header">
                <div className="tx-back-row">
                    <Link to="/wallet" className="tx-back-btn" id="back-to-wallet-btn">
                        <FiChevronLeft size={16} /> Back to Wallet
                    </Link>
                </div>
                <div className="tx-page__title-row">
                    <div>
                        <h1 className="tx-page__title">Transaction History</h1>
                        <p className="tx-page__subtitle">A full record of all credits and debits on your wallet.</p>
                    </div>
                    {isFetching && !isLoading && (
                        <div className="tx-fetching-indicator" title="Refreshing...">
                            <FiRefreshCw size={16} className="tx-spin" />
                        </div>
                    )}
                </div>
            </div>

            <div className="tx-filters" role="group" aria-label="Filter transactions by type">
                {FILTERS.map((f) => (
                    <button key={f.value} id={`filter-${f.value || 'all'}`}
                        className={`tx-pill ${activeType === f.value ? 'tx-pill--active' : ''}`}
                        onClick={() => handleFilterChange(f.value)} aria-pressed={activeType === f.value}>
                        {f.label}
                    </button>
                ))}
            </div>

            {isError && (
                <div className="tx-error-box">
                    <FiAlertCircle size={22} />
                    <div>
                        <strong>Failed to load transactions</strong>
                        <p>{error?.response?.data?.detail || 'Please check your connection and try again.'}</p>
                        <button className="tx-btn tx-btn--primary" onClick={() => refetch()}>Retry</button>
                    </div>
                </div>
            )}

            {!isError && (
                <div className="tx-table-wrap">
                    <table className="tx-table" aria-label="Transaction history">
                        <thead>
                            <tr>
                                <th className="tx-th">Description</th>
                                <th className="tx-th">Date &amp; Time</th>
                                <th className="tx-th tx-th--right">Amount</th>
                                <th className="tx-th tx-th--right">Balance After</th>
                            </tr>
                        </thead>
                        <tbody>
                            {isLoading && !transactions.length
                                ? Array.from({ length: 10 }, (_, i) => <SkeletonRow key={i} />)
                                : transactions.length === 0
                                    ? (<tr><td colSpan="4" className="tx-empty-cell"><EmptyState activeFilter={activeType} /></td></tr>)
                                    : transactions.map((tx) => <TransactionRow key={tx.id || tx.tx_ref} tx={tx} />)
                            }
                        </tbody>
                    </table>
                </div>
            )}

            {!isLoading && !isError && total > 0 && (
                <div className="tx-pagination">
                    <span className="tx-pagination__info">
                        Showing <strong>{from}</strong>-<strong>{to}</strong> of <strong>{total}</strong> transaction{total !== 1 ? 's' : ''}
                    </span>
                    <div className="tx-pagination__controls">
                        <button className="tx-btn tx-btn--ghost" onClick={() => setPage((p) => Math.max(1, p - 1))}
                            disabled={page <= 1 || isFetching}>
                            <FiChevronLeft size={16} /> Previous
                        </button>
                        <span className="tx-pagination__pages">Page <strong>{page}</strong> of <strong>{totalPages}</strong></span>
                        <button className="tx-btn tx-btn--ghost" onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages || isFetching}>
                            Next <FiChevronRight size={16} />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
