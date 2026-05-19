import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FiLayers, FiSearch, FiX, FiCalendar, FiAlertCircle, FiUser, FiDollarSign, FiClock, FiShield, FiTruck, FiCornerDownRight
} from 'react-icons/fi';
import { Link } from 'react-router-dom';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';

const STATUS_OPTIONS = [
  'PENDING_SHIPMENT',
  'SHIPPED',
  'DELIVERED',
  'DISPUTED',
  'COMPLETED',
  'CANCELLED',
  'REFUNDED'
];

const ORDER_STATUS_STYLE = {
  PENDING_SHIPMENT: { bg: '#FEF3C7', color: '#D97706' }, // Soft amber
  SHIPPED:          { bg: '#E0F2FE', color: '#0369A1' }, // Soft blue
  DELIVERED:        { bg: '#D1FAE5', color: '#059669' }, // Soft emerald
  DISPUTED:         { bg: '#FEE2E2', color: '#DC2626' }, // Soft red
  COMPLETED:        { bg: 'var(--success-light)', color: 'var(--success)' }, // Rich success green
  CANCELLED:        { bg: '#F3F4F6', color: '#4B5563' }, // Soft gray
  REFUNDED:         { bg: '#F5F3FF', color: '#7C3AED' }, // Soft purple
};

const ESCROW_STATUS_STYLE = {
  HELD:     { bg: '#FEF3C7', color: '#D97706', label: 'Held in Escrow' },
  RELEASED: { bg: 'var(--success-light)', color: 'var(--success)', label: 'Released to Seller' },
  REFUNDED: { bg: '#F5F3FF', color: '#7C3AED', label: 'Refunded to Buyer' },
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

// ── Detail Drawer ──────────────────────────────────────────────────────────────
function OrderDetailDrawer({ orderId, onClose }) {
  // Secondary fetch for admin to see full dispute and escrow details
  const { data: order, isLoading, isError } = useQuery({
    queryKey: ['admin-order-detail', orderId],
    queryFn: () => apiClient.get(`/admin/orders/${orderId}`).then(r => r.data),
    staleTime: 10_000,
  });

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 200, display: 'flex' }}>
      {/* Backdrop */}
      <div onClick={onClose} style={{ flex: 1, background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(2px)' }} />
      {/* Panel */}
      <div style={{
        width: 520, maxWidth: '95vw', background: '#fff', height: '100%',
        overflowY: 'auto', boxShadow: 'var(--shadow-lg)', display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <div style={{
          padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          position: 'sticky', top: 0, background: '#fff', zIndex: 1
        }}>
          <div>
            <h2 style={{ fontWeight: 800, fontSize: '1.125rem', margin: 0 }}>Order Audit Details</h2>
            <span style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: 'var(--text-muted)' }}>
              ID: {orderId}
            </span>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}>
            <FiX size={20} />
          </button>
        </div>

        {/* Loading Spinner */}
        {isLoading && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem' }}>
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading details...</span>
            </div>
          </div>
        )}

        {/* Error State */}
        {isError && (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--danger)', flex: 1 }}>
            <FiAlertCircle size={32} className="mb-2" />
            <h5>Failed to load order audit data</h5>
            <p style={{ fontSize: '0.8125rem' }}>Verify network configuration or backend service state.</p>
          </div>
        )}

        {/* Content */}
        {!isLoading && !isError && order && (
          <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

            {/* Identity & Status */}
            <section style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '1.25rem' }}>
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>ORDER STATUS</div>
                <div style={{ marginTop: '0.25rem' }}>
                  <Badge label={order.status} style={ORDER_STATUS_STYLE[order.status]} />
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>TOTAL VALUE</div>
                <div style={{ fontWeight: 800, fontSize: '1.25rem', color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                  {fmt(order.amount)}
                </div>
              </div>
            </section>

            {/* Escrow Status & Finances */}
            <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '1.25rem' }}>
              <div className="d-flex align-items-center gap-2 mb-3">
                <FiShield size={18} style={{ color: 'var(--primary)' }} />
                <span style={{ fontWeight: 800, fontSize: '0.875rem', color: 'var(--text-primary)' }}>Escrow & Ledger Audit</span>
              </div>

              {order.escrow ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Escrow Status:</span>
                    <Badge label={order.escrow.status} style={ESCROW_STATUS_STYLE[order.escrow.status]} />
                  </div>
                  <hr style={{ margin: '0.5rem 0', borderColor: 'var(--border)' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Gross Amount:</span>
                    <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{fmt(order.escrow.amount)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Platform Commission (5%):</span>
                    <span style={{ fontWeight: 700, color: 'var(--danger)' }}>{fmt(order.commission_amount)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0.75rem', background: '#F1F5F9', borderRadius: 'var(--radius)', marginTop: '0.25rem' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Seller Payout:</span>
                    <span style={{ fontWeight: 800, color: 'var(--success)' }}>{fmt(order.seller_payout)}</span>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  No active escrow contract linked to this order.
                </div>
              )}
            </section>

            {/* Dispute Resolution Link */}
            {order.dispute && (
              <section style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: 'var(--radius-lg)', padding: '1.25rem' }}>
                <div className="d-flex align-items-center gap-2 mb-2" style={{ color: 'var(--danger)' }}>
                  <FiAlertCircle size={18} />
                  <span style={{ fontWeight: 800, fontSize: '0.875rem' }}>Active Order Dispute</span>
                </div>
                <p style={{ fontSize: '0.8125rem', color: '#991B1B', margin: '0 0 0.75rem' }}>
                  This order has an open dispute raised by the buyer due to fulfillment or delivery discrepancies.
                </p>
                <div className="d-flex justify-content-between align-items-center" style={{ background: '#fff', padding: '0.75rem', borderRadius: 'var(--radius)', border: '1px solid #FECACA' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>DISPUTE STATUS</div>
                    <div style={{ fontWeight: 700, fontSize: '0.8125rem', color: '#991B1B' }}>{order.dispute.status}</div>
                  </div>
                  <Link to="/admin/disputes" className="btn btn-danger btn-sm" style={{ fontWeight: 600, fontSize: '0.75rem' }}>
                    Resolve Dispute
                  </Link>
                </div>
              </section>
            )}

            {/* Shipping & Delivery Information */}
            <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '1.25rem' }}>
              <div className="d-flex align-items-center gap-2 mb-3">
                <FiTruck size={18} style={{ color: 'var(--primary)' }} />
                <span style={{ fontWeight: 800, fontSize: '0.875rem', color: 'var(--text-primary)' }}>Shipping & Logistics</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.8125rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Tracking Number:</span>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'monospace' }}>
                    {order.tracking_number || 'Not provided yet'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Shipping Deadline:</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {formatDateTime(order.shipping_deadline_at)}
                  </span>
                </div>
                {order.shipped_at && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Shipped At:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {formatDateTime(order.shipped_at)}
                    </span>
                  </div>
                )}
                {order.delivered_at && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Delivered At:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {formatDateTime(order.delivered_at)}
                    </span>
                  </div>
                )}
              </div>
            </section>

            {/* Buyer & Seller Parties */}
            <section style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>
                Involved Parties
              </div>

              {/* Buyer */}
              <div className="d-flex align-items-center gap-3" style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '0.75rem 1rem' }}>
                <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-full)', background: 'var(--primary-50)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.8125rem' }}>
                  BY
                </div>
                <div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>BUYER (WINNER)</div>
                  <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {order.buyer?.first_name} {order.buyer?.last_name}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {order.buyer?.email}
                  </div>
                </div>
              </div>

              {/* Seller */}
              <div className="d-flex align-items-center gap-3" style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '0.75rem 1rem' }}>
                <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-full)', background: '#E0F2FE', color: '#0369A1', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.8125rem' }}>
                  SL
                </div>
                <div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>SELLER (LISTER)</div>
                  <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {order.seller?.first_name} {order.seller?.last_name}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {order.seller?.email}
                  </div>
                </div>
              </div>
            </section>

            {/* Product Item info */}
            {order.item && (
              <section>
                <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                  Purchased Item
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '0.75rem' }}>
                  <div style={{ width: 64, height: 64, borderRadius: 'var(--radius)', overflow: 'hidden', background: '#eef2f6', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    {order.item.primary_image_url ? (
                      <img src={order.item.primary_image_url} alt={order.item.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <FiLayers size={20} style={{ color: 'var(--text-muted)' }} />
                    )}
                  </div>
                  <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {order.item.title}
                    </div>
                    <div className="d-flex align-items-center gap-2 mt-1">
                      <span style={{ background: '#E0F2FE', color: '#0369A1', borderRadius: 'var(--radius-full)', fontSize: '0.65rem', fontWeight: 700, padding: '0.15em 0.5em' }}>
                        {order.item.condition}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        Item ID: {order.item.id.slice(0, 8)}…
                      </span>
                    </div>
                  </div>
                </div>
              </section>
            )}

          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Orders Page ──────────────────────────────────────────────────────────
export default function AdminOrdersPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedOrderId, setSelectedOrderId] = useState(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-orders-list', statusFilter, search, page],
    queryFn: () => {
      const params = new URLSearchParams({ page, limit: 15 });
      if (statusFilter) params.set('status', statusFilter);
      if (search) params.set('search', search);
      return apiClient.get(`/admin/orders?${params}`).then(r => r.data);
    },
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });

  const orders = data?.data || [];
  const pagination = data?.pagination;

  return (
    <div style={{ padding: '2rem', minHeight: '100vh' }}>

      {/* Header */}
      <div className="d-flex align-items-center gap-3 mb-4">
        <div style={{
          width: 44, height: 44, borderRadius: 'var(--radius)',
          background: 'var(--primary-50)', color: 'var(--primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <FiLayers size={22} />
        </div>
        <div>
          <h1 style={{ fontWeight: 800, fontSize: '1.5rem', margin: 0 }}>Order Ledger Management</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
            {pagination ? `${pagination.total} total orders audited` : 'Audit physical delivery and escrow balances'}
          </p>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="card-body p-3">
          <div className="row g-2 align-items-center">

            {/* Search Filter */}
            <div className="col-md-7">
              <div style={{ position: 'relative' }}>
                <FiSearch size={15} style={{
                  position: 'absolute', left: '0.875rem', top: '50%',
                  transform: 'translateY(-50%)', color: 'var(--text-muted)'
                }} />
                <input
                  className="form-control form-control-sm"
                  style={{ paddingLeft: '2.25rem' }}
                  placeholder="Search by buyer/seller email or tracking number…"
                  value={search}
                  onChange={e => { setSearch(e.target.value); setPage(1); }}
                />
              </div>
            </div>

            {/* Status Filter */}
            <div className="col-md-4">
              <select
                className="form-select form-select-sm"
                value={statusFilter}
                onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
              >
                <option value="">All statuses</option>
                {STATUS_OPTIONS.map(s => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            {/* Clear Filters */}
            <div className="col-md-1">
              <button
                className="btn btn-outline-secondary btn-sm w-100"
                onClick={() => { setSearch(''); setStatusFilter(''); setPage(1); }}
              >
                Clear
              </button>
            </div>

          </div>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="card" style={{ borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>

        {/* Loading Skeleton state */}
        {isLoading && (
          <div style={{ padding: '3rem' }}>
            <div className="skeleton mb-3" style={{ height: 24, width: '100%' }} />
            <div className="skeleton mb-2" style={{ height: 16, width: '90%' }} />
            <div className="skeleton mb-2" style={{ height: 16, width: '95%' }} />
            <div className="skeleton" style={{ height: 16, width: '60%' }} />
          </div>
        )}

        {/* Error state */}
        {isError && (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--danger)' }}>
            <FiAlertCircle size={32} className="mb-2" />
            <h5>Failed to load audited orders</h5>
            <p style={{ fontSize: '0.875rem' }}>Verify server or docker-compose active status.</p>
          </div>
        )}

        {/* Table View */}
        {!isLoading && !isError && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
                  {[
                    'Order ID', 'Buyer Info', 'Seller Info',
                    'Amount', 'Status Badge', 'Created At'
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
                {orders.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <FiLayers size={40} className="mb-2 mx-auto d-block" />
                      <h5 style={{ fontWeight: 700, margin: '0 0 0.25rem' }}>No orders located</h5>
                      <p style={{ fontSize: '0.8125rem', margin: 0 }}>Try clearing filters or queries.</p>
                    </td>
                  </tr>
                ) : (
                  orders.map(order => (
                    <tr
                      key={order.id}
                      onClick={() => setSelectedOrderId(order.id)}
                      style={{
                        borderBottom: '1px solid var(--border)', cursor: 'pointer',
                        transition: 'background 0.1s'
                      }}
                      onMouseOver={e => e.currentTarget.style.background = 'var(--surface)'}
                      onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                    >
                      {/* ID */}
                      <td style={{ padding: '0.75rem 1rem', fontWeight: 700, fontFamily: 'monospace', color: 'var(--text-primary)' }}>
                        #{order.id.slice(0, 8)}
                      </td>

                      {/* Buyer */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {order.buyer?.first_name} {order.buyer?.last_name}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {order.buyer?.email}
                        </div>
                      </td>

                      {/* Seller */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {order.seller?.first_name} {order.seller?.last_name}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {order.seller?.email}
                        </div>
                      </td>

                      {/* Amount */}
                      <td style={{ padding: '0.75rem 1rem', fontWeight: 800, color: 'var(--text-primary)', fontSize: '0.875rem' }}>
                        {fmt(order.amount)}
                      </td>

                      {/* Status */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <Badge label={order.status} style={ORDER_STATUS_STYLE[order.status]} />
                      </td>

                      {/* Created At */}
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--text-secondary)' }}>
                        {formatDateTime(order.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination controls */}
        {pagination && pagination.total_pages > 1 && (
          <div className="d-flex align-items-center justify-content-between p-3" style={{ borderTop: '1px solid var(--border)' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              Page {pagination.page} of {pagination.total_pages} — {pagination.total} orders audited
            </span>
            <div className="d-flex gap-2">
              <button
                className="btn btn-outline-secondary btn-sm"
                disabled={!pagination.has_previous}
                onClick={() => setPage(p => p - 1)}
              >
                Previous
              </button>
              <button
                className="btn btn-outline-secondary btn-sm"
                disabled={!pagination.has_next}
                onClick={() => setPage(p => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}

      </div>

      {/* Slide-over Detailed Audit Drawer */}
      {selectedOrderId && (
        <OrderDetailDrawer
          orderId={selectedOrderId}
          onClose={() => setSelectedOrderId(null)}
        />
      )}

    </div>
  );
}
