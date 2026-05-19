import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FiDollarSign, FiCreditCard, FiSearch, FiCalendar, FiAlertCircle, FiArrowUpRight, FiArrowDownLeft, FiInbox
} from 'react-icons/fi';
import apiClient from '../../api/client';

const TRANSACTION_TYPES = [
  'DEPOSIT',
  'WITHDRAWAL',
  'BID_LOCK',
  'BID_UNLOCK',
  'ESCROW_HOLD',
  'ESCROW_RELEASE',
  'REFUND'
];

const PAYMENT_STATUSES = [
  'PENDING',
  'COMPLETED',
  'FAILED'
];

const DIRECTION_STYLE = {
  CREDIT: { text: '#059669', bg: '#D1FAE5', icon: FiArrowDownLeft, label: 'Credit (+)' },
  DEBIT:  { text: '#DC2626', bg: '#FEE2E2', icon: FiArrowUpRight, label: 'Debit (-)' },
};

const PAYMENT_STATUS_STYLE = {
  PENDING:   { bg: '#FEF3C7', color: '#D97706' },
  COMPLETED: { bg: 'var(--success-light)', color: 'var(--success)' },
  FAILED:    { bg: '#FEE2E2', color: '#DC2626' },
};

const TYPE_STYLE = {
  DEPOSIT:        { bg: '#E0F2FE', color: '#0369A1' },
  WITHDRAWAL:     { bg: '#F3F4F6', color: '#4B5563' },
  BID_LOCK:       { bg: '#FEF3C7', color: '#D97706' },
  BID_UNLOCK:     { bg: '#F3F4F6', color: '#4B5563' },
  ESCROW_HOLD:    { bg: '#E0E7FF', color: '#4338CA' },
  ESCROW_RELEASE: { bg: '#D1FAE5', color: '#059669' },
  REFUND:         { bg: '#F5F3FF', color: '#7C3AED' },
};

function Badge({ label, style }) {
  return (
    <span style={{
      background: style?.bg || '#F1F5F9',
      color: style?.color || 'var(--text-muted)',
      borderRadius: 'var(--radius-full)',
      fontSize: '0.7rem',
      fontWeight: 700,
      padding: '0.25em 0.65em',
      whiteSpace: 'nowrap',
      display: 'inline-block'
    }}>
      {label?.replace(/_/g, ' ')}
    </span>
  );
}

const fmt = (n) => n != null ? `₦${Number(n).toLocaleString('en-NG', { minimumFractionDigits: 2 })}` : '—';

const formatDateTime = (dtStr) => {
  if (!dtStr) return '—';
  const d = new Date(dtStr);
  return d.toLocaleString('en-NG', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
};

export default function AdminFinancialPage() {
  const [activeTab, setActiveTab] = useState('transactions'); // 'transactions' | 'payments'

  // Transactions Filter States
  const [txType, setTxType] = useState('');
  const [txDirection, setTxDirection] = useState('');
  const [txSearch, setTxSearch] = useState('');
  const [txPage, setTxPage] = useState(1);

  // Payments Filter States
  const [payStatus, setPayStatus] = useState('');
  const [paySearch, setPaySearch] = useState('');
  const [payPage, setPayPage] = useState(1);

  // Query Transactions
  const {
    data: txData,
    isLoading: txLoading,
    isError: txError
  } = useQuery({
    queryKey: ['admin-tx-list', txType, txDirection, txSearch, txPage],
    queryFn: () => {
      const params = new URLSearchParams({ page: txPage, limit: 15 });
      if (txType) params.set('transaction_type', txType);
      if (txDirection) params.set('direction', txDirection);
      if (txSearch) params.set('search', txSearch);
      return apiClient.get(`/admin/wallet-transactions?${params}`).then(r => r.data);
    },
    enabled: activeTab === 'transactions',
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });

  // Query Payments
  const {
    data: payData,
    isLoading: payLoading,
    isError: payError
  } = useQuery({
    queryKey: ['admin-pay-list', payStatus, paySearch, payPage],
    queryFn: () => {
      const params = new URLSearchParams({ page: payPage, limit: 15 });
      if (payStatus) params.set('status', payStatus);
      if (paySearch) params.set('search', paySearch);
      return apiClient.get(`/admin/payments?${params}`).then(r => r.data);
    },
    enabled: activeTab === 'payments',
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });

  const transactions = txData?.data || [];
  const txPagination = txData?.pagination;

  const payments = payData?.data || [];
  const payPagination = payData?.pagination;

  return (
    <div style={{ padding: '2rem', minHeight: '100vh' }}>

      {/* Header */}
      <div className="d-flex align-items-center gap-3 mb-4">
        <div style={{
          width: 44, height: 44, borderRadius: 'var(--radius)',
          background: 'var(--primary-50)', color: 'var(--primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <FiDollarSign size={22} />
        </div>
        <div>
          <h1 style={{ fontWeight: 800, fontSize: '1.5rem', margin: 0 }}>Financial Ledger Audit</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
            Audit platform-wide wallet ledger entries and payment provider invoices (Read-only)
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{
        display: 'flex', borderBottom: '2px solid var(--border)',
        marginBottom: '1.5rem', gap: '1.5rem'
      }}>
        <button
          onClick={() => setActiveTab('transactions')}
          style={{
            background: 'none', border: 'none', padding: '0.75rem 0',
            fontWeight: 800, fontSize: '0.9rem', cursor: 'pointer',
            color: activeTab === 'transactions' ? 'var(--primary)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'transactions' ? '2px solid var(--primary)' : '2px solid transparent',
            marginBottom: -2, transition: 'all 0.15s ease'
          }}
        >
          Wallet Transactions
        </button>
        <button
          onClick={() => setActiveTab('payments')}
          style={{
            background: 'none', border: 'none', padding: '0.75rem 0',
            fontWeight: 800, fontSize: '0.9rem', cursor: 'pointer',
            color: activeTab === 'payments' ? 'var(--primary)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'payments' ? '2px solid var(--primary)' : '2px solid transparent',
            marginBottom: -2, transition: 'all 0.15s ease'
          }}
        >
          Payment Invoices
        </button>
      </div>

      {/* ── WORKSPACE 1: Wallet Transactions ─────────────────────────────────── */}
      {activeTab === 'transactions' && (
        <>
          {/* Filters Card */}
          <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
            <div className="card-body p-3">
              <div className="row g-2 align-items-center">

                {/* Search keyword */}
                <div className="col-md-4">
                  <div className="input-group input-group-sm">
                    <span className="input-group-text bg-light border-end-0">
                      <FiSearch className="text-muted" />
                    </span>
                    <input
                      type="text"
                      className="form-control border-start-0"
                      placeholder="Search name or email..."
                      value={txSearch}
                      onChange={e => { setTxSearch(e.target.value); setTxPage(1); }}
                    />
                  </div>
                </div>

                {/* Transaction Type Filter */}
                <div className="col-md-3">
                  <div className="d-flex align-items-center gap-2">
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>TYPE:</span>
                    <select
                      className="form-select form-select-sm"
                      value={txType}
                      onChange={e => { setTxType(e.target.value); setTxPage(1); }}
                    >
                      <option value="">All Types</option>
                      {TRANSACTION_TYPES.map(t => (
                        <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Direction Filter */}
                <div className="col-md-3">
                  <div className="d-flex align-items-center gap-2">
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>DIRECTION:</span>
                    <select
                      className="form-select form-select-sm"
                      value={txDirection}
                      onChange={e => { setTxDirection(e.target.value); setTxPage(1); }}
                    >
                      <option value="">All Directions</option>
                      <option value="CREDIT">Credit (+)</option>
                      <option value="DEBIT">Debit (-)</option>
                    </select>
                  </div>
                </div>

                {/* Clear */}
                <div className="col-md-2">
                  <button
                    className="btn btn-outline-secondary btn-sm w-100"
                    onClick={() => { setTxType(''); setTxDirection(''); setTxSearch(''); setTxPage(1); }}
                  >
                    Clear Filters
                  </button>
                </div>

              </div>
            </div>
          </div>

          {/* Ledger Table Card */}
          <div className="card" style={{ borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
            {txLoading && (
              <div style={{ padding: '3rem' }}>
                <div className="skeleton mb-3" style={{ height: 24, width: '100%' }} />
                <div className="skeleton mb-2" style={{ height: 16, width: '90%' }} />
                <div className="skeleton mb-2" style={{ height: 16, width: '95%' }} />
              </div>
            )}

            {txError && (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--danger)' }}>
                <FiAlertCircle size={32} className="mb-2" />
                <h5>Failed to retrieve ledger logs</h5>
                <p style={{ fontSize: '0.875rem' }}>Check backend server status.</p>
              </div>
            )}

            {!txLoading && !txError && (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
                      {[
                        'Wallet ID', 'Amount', 'Type',
                        'Direction', 'Bucket', 'Description', 'Timestamp'
                      ].map(h => (
                        <th
                          key={h}
                          style={{
                            padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 700,
                            color: 'var(--text-muted)', fontSize: '0.75rem',
                            textTransform: 'uppercase', letterSpacing: '0.04em', whiteSpace: 'nowrap'
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.length === 0 ? (
                      <tr>
                        <td colSpan={7} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                          <FiInbox size={40} className="mb-2 mx-auto d-block" />
                          <h5 style={{ fontWeight: 700, margin: '0 0 0.25rem' }}>No transaction records found</h5>
                          <p style={{ fontSize: '0.8125rem', margin: 0 }}>Ledger is currently empty or filtered out.</p>
                        </td>
                      </tr>
                    ) : (
                      transactions.map(tx => {
                        const styleInfo = DIRECTION_STYLE[tx.direction];
                        const DirectionIcon = styleInfo?.icon;
                        return (
                          <tr key={tx.id} style={{ borderBottom: '1px solid var(--border)' }}>

                            {/* Wallet ID */}
                            <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', fontWeight: 600 }}>
                              {tx.wallet_id ? tx.wallet_id.slice(0, 8) + '…' : '—'}
                            </td>

                            {/* Amount */}
                            <td style={{
                              padding: '0.75rem 1rem', fontWeight: 800,
                              color: styleInfo?.text || 'var(--text-primary)', fontSize: '0.875rem'
                            }}>
                              {tx.direction === 'CREDIT' ? '+' : '-'}{fmt(tx.amount)}
                            </td>

                            {/* Type */}
                            <td style={{ padding: '0.75rem 1rem' }}>
                              <Badge label={tx.transaction_type} style={TYPE_STYLE[tx.transaction_type]} />
                            </td>

                            {/* Direction */}
                            <td style={{ padding: '0.75rem 1rem' }}>
                              <div style={{
                                display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
                                color: styleInfo?.text, fontWeight: 700, fontSize: '0.75rem'
                              }}>
                                {DirectionIcon && <DirectionIcon size={12} />}
                                {styleInfo?.label || tx.direction}
                              </div>
                            </td>

                            {/* Bucket */}
                            <td style={{ padding: '0.75rem 1rem' }}>
                              <Badge label={tx.balance_type} style={{
                                bg: tx.balance_type === 'AVAILABLE' ? '#D1FAE5' : tx.balance_type === 'ESCROW' ? '#E0E7FF' : '#FEF3C7',
                                color: tx.balance_type === 'AVAILABLE' ? '#059669' : tx.balance_type === 'ESCROW' ? '#4338CA' : '#D97706'
                              }} />
                            </td>

                            {/* Description */}
                            <td style={{ padding: '0.75rem 1rem', color: 'var(--text-secondary)', max_width: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {tx.description}
                            </td>

                            {/* Created At */}
                            <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)' }}>
                              {formatDateTime(tx.created_at)}
                            </td>

                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {txPagination && txPagination.total_pages > 1 && (
              <div className="d-flex align-items-center justify-content-between p-3" style={{ borderTop: '1px solid var(--border)' }}>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                  Page {txPagination.page} of {txPagination.total_pages} — {txPagination.total} audit entries
                </span>
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    disabled={!txPagination.has_previous}
                    onClick={() => setTxPage(p => p - 1)}
                  >
                    Previous
                  </button>
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    disabled={!txPagination.has_next}
                    onClick={() => setTxPage(p => p + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* ── WORKSPACE 2: Payment Receipts ────────────────────────────────────── */}
      {activeTab === 'payments' && (
        <>
          {/* Filters Card */}
          <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
            <div className="card-body p-3">
              <div className="row g-2 align-items-center">

                {/* Search keyword */}
                <div className="col-md-5">
                  <div className="input-group input-group-sm">
                    <span className="input-group-text bg-light border-end-0">
                      <FiSearch className="text-muted" />
                    </span>
                    <input
                      type="text"
                      className="form-control border-start-0"
                      placeholder="Search ref, name or email..."
                      value={paySearch}
                      onChange={e => { setPaySearch(e.target.value); setPayPage(1); }}
                    />
                  </div>
                </div>

                {/* Status Filter */}
                <div className="col-md-5">
                  <div className="d-flex align-items-center gap-2">
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>STATUS:</span>
                    <select
                      className="form-select form-select-sm"
                      value={payStatus}
                      onChange={e => { setPayStatus(e.target.value); setPayPage(1); }}
                    >
                      <option value="">All Statuses</option>
                      {PAYMENT_STATUSES.map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Clear */}
                <div className="col-md-2">
                  <button
                    className="btn btn-outline-secondary btn-sm w-100"
                    onClick={() => { setPayStatus(''); setPaySearch(''); setPayPage(1); }}
                  >
                    Clear Filters
                  </button>
                </div>

              </div>
            </div>
          </div>

          {/* Payments Table Card */}
          <div className="card" style={{ borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
            {payLoading && (
              <div style={{ padding: '3rem' }}>
                <div className="skeleton mb-3" style={{ height: 24, width: '100%' }} />
                <div className="skeleton mb-2" style={{ height: 16, width: '90%' }} />
                <div className="skeleton mb-2" style={{ height: 16, width: '95%' }} />
              </div>
            )}

            {payError && (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--danger)' }}>
                <FiAlertCircle size={32} className="mb-2" />
                <h5>Failed to retrieve payment invoices</h5>
                <p style={{ fontSize: '0.875rem' }}>Verify network configurations.</p>
              </div>
            )}

            {!payLoading && !payError && (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
                      {[
                        'Reference ID', 'Gateway Provider', 'Amount',
                        'Status Badge', 'Logged Timestamp'
                      ].map(h => (
                        <th
                          key={h}
                          style={{
                            padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 700,
                            color: 'var(--text-muted)', fontSize: '0.75rem',
                            textTransform: 'uppercase', letterSpacing: '0.04em', whiteSpace: 'nowrap'
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {payments.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                          <FiCreditCard size={40} className="mb-2 mx-auto d-block" />
                          <h5 style={{ fontWeight: 700, margin: '0 0 0.25rem' }}>No payment receipts located</h5>
                          <p style={{ fontSize: '0.8125rem', margin: 0 }}>No invoices matched the chosen filters.</p>
                        </td>
                      </tr>
                    ) : (
                      payments.map(pay => (
                        <tr key={pay.id} style={{ borderBottom: '1px solid var(--border)' }}>

                          {/* Reference */}
                          <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', fontWeight: 700, color: 'var(--text-primary)' }}>
                            {pay.transaction_reference}
                          </td>

                          {/* Provider */}
                          <td style={{ padding: '0.75rem 1rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                            {pay.provider}
                          </td>

                          {/* Amount */}
                          <td style={{ padding: '0.75rem 1rem', fontWeight: 800, color: 'var(--text-primary)', fontSize: '0.875rem' }}>
                            {fmt(pay.amount)}
                          </td>

                          {/* Status Badge */}
                          <td style={{ padding: '0.75rem 1rem' }}>
                            <Badge label={pay.status} style={PAYMENT_STATUS_STYLE[pay.status]} />
                          </td>

                          {/* Created At */}
                          <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)' }}>
                            {formatDateTime(pay.created_at)}
                          </td>

                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {payPagination && payPagination.total_pages > 1 && (
              <div className="d-flex align-items-center justify-content-between p-3" style={{ borderTop: '1px solid var(--border)' }}>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                  Page {payPagination.page} of {payPagination.total_pages} — {payPagination.total} payment receipts
                </span>
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    disabled={!payPagination.has_previous}
                    onClick={() => setPayPage(p => p - 1)}
                  >
                    Previous
                  </button>
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    disabled={!payPagination.has_next}
                    onClick={() => setPayPage(p => p + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}

    </div>
  );
}
