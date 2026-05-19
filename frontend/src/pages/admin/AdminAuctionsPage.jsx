import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FiTag, FiSearch, FiX, FiChevronRight, FiCalendar, FiAlertCircle, FiUser, FiActivity, FiDollarSign, FiClock, FiLayers
} from 'react-icons/fi';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';

const STATUS_OPTIONS = [
  'DRAFT',
  'ACTIVE',
  'SCHEDULED',
  'CANCELLED',
  'ENDED_WITH_WINNER',
  'ENDED_NO_BIDS',
  'ENDED_RESERVE_NOT_MET',
  'SETTLEMENT_IN_PROGRESS',
  'SETTLED',
  'SETTLEMENT_FAILED'
];

const AUCTION_STATUS_STYLE = {
  DRAFT:                  { bg: '#F1F5F9',              color: 'var(--text-muted)' },
  ACTIVE:                 { bg: 'var(--success-light)', color: 'var(--success)' },
  SCHEDULED:              { bg: 'var(--info-light)',    color: 'var(--info)' },
  CANCELLED:              { bg: 'var(--danger-light)',  color: 'var(--danger)' },
  ENDED_WITH_WINNER:      { bg: '#E0F2FE',              color: '#0369A1' },
  ENDED_NO_BIDS:          { bg: '#F3F4F6',              color: '#4B5563' },
  ENDED_RESERVE_NOT_MET:  { bg: '#FEF3C7',              color: '#D97706' },
  SETTLED:                { bg: '#D1FAE5',              color: '#059669' },
  SETTLEMENT_IN_PROGRESS: { bg: '#F5F3FF',              color: '#7C3AED' },
  SETTLEMENT_FAILED:      { bg: '#FEE2E2',              color: '#DC2626' },
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
function AuctionDetailDrawer({ auction, onClose, onCancelClick }) {
  const isCancellable = auction.status === 'ACTIVE' || auction.status === 'SCHEDULED';

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
          <h2 style={{ fontWeight: 800, fontSize: '1.125rem', margin: 0 }}>Auction Details</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}>
            <FiX size={20} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* Identity & Status */}
          <section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ fontWeight: 800, fontSize: '1.25rem', color: 'var(--text-primary)', margin: '0 0 0.25rem' }}>
                  {auction.title || `Auction #${auction.id.slice(0, 8)}`}
                </h3>
                <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-muted)' }}>
                  ID: {auction.id}
                </span>
              </div>
              <Badge label={auction.status} style={AUCTION_STATUS_STYLE[auction.status]} />
            </div>
            {auction.description && (
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, background: 'var(--surface)', padding: '0.75rem 1rem', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                {auction.description}
              </p>
            )}
          </section>

          {/* Schedule */}
          <section>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              Schedule
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '1rem' }}>
              <div className="d-flex align-items-center gap-3">
                <FiCalendar size={18} style={{ color: 'var(--primary)' }} />
                <div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>STARTS AT</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>{formatDateTime(auction.starts_at)}</div>
                </div>
              </div>
              <hr style={{ margin: '0.75rem 0', borderColor: 'var(--border)' }} />
              <div className="d-flex align-items-center gap-3">
                <FiClock size={18} style={{ color: 'var(--danger)' }} />
                <div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>ENDS AT</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>{formatDateTime(auction.ends_at)}</div>
                </div>
              </div>
            </div>
          </section>

          {/* Financials & Bidding */}
          <section>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              Financials & Bids
            </div>
            <div className="row g-2">
              <div className="col-6">
                <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', padding: '0.75rem 1rem', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.25rem' }}>RESERVE PRICE</div>
                  <div style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--text-primary)' }}>
                    {auction.reserve_price != null ? fmt(auction.reserve_price) : 'No Reserve'}
                  </div>
                </div>
              </div>
              <div className="col-6">
                <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', padding: '0.75rem 1rem', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.25rem' }}>BID COUNT</div>
                  <div style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--text-primary)' }}>
                    {auction.bid_count} bid{auction.bid_count !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>
              <div className="col-12">
                <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', padding: '0.75rem 1rem', border: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.1rem' }}>CURRENT HIGHEST BID</div>
                    <div style={{ fontWeight: 800, fontSize: '1.125rem', color: 'var(--primary)' }}>
                      {auction.highest_bid ? fmt(auction.highest_bid.amount) : 'No bids placed yet'}
                    </div>
                  </div>
                  {auction.highest_bid && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      by bidder {String(auction.highest_bid.bidder_id).slice(0, 8)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </section>

          {/* Seller Information */}
          <section>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              Seller Profile
            </div>
            <div className="d-flex align-items-center gap-3" style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '1rem' }}>
              <div style={{ width: 40, height: 40, borderRadius: 'var(--radius-full)', background: 'var(--primary-50)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>
                <FiUser size={20} />
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {auction.seller?.first_name} {auction.seller?.last_name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {auction.seller?.email}
                </div>
              </div>
            </div>
          </section>

          {/* Attached Items lot */}
          {auction.items && auction.items.length > 0 && (
            <section>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                {(() => {
                  const totalPhotos = auction.items.reduce((sum, ai) => sum + (ai.item.images?.length || 0), 0);
                  const itemCount = auction.items.length;
                  return `Attached Items Lot (${itemCount} item${itemCount !== 1 ? 's' : ''}, ${totalPhotos} photo${totalPhotos !== 1 ? 's' : ''})`;
                })()}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {auction.items.map((ai) => {
                  const item = ai.item;
                  const images = item.images || [];
                  const primaryImg = images.find(img => img.is_primary) || images[0];
                  const extraImages = images.filter(img => img !== primaryImg);

                  return (
                    <div key={item.id} style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '0.75rem' }}>
                      {/* Top row: primary image + details */}
                      <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <div style={{ width: 64, height: 64, borderRadius: 'var(--radius)', overflow: 'hidden', background: '#eef2f6', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          {primaryImg ? (
                            <img src={primaryImg.url} alt={item.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          ) : (
                            <FiTag size={20} style={{ color: 'var(--text-muted)' }} />
                          )}
                        </div>
                        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {item.title}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {item.description}
                            </div>
                          </div>
                          <div className="d-flex align-items-center justify-content-between mt-1">
                            <span style={{ background: '#E0F2FE', color: '#0369A1', borderRadius: 'var(--radius-full)', fontSize: '0.65rem', fontWeight: 700, padding: '0.15em 0.5em' }}>
                              {item.condition}
                            </span>
                            <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                              Start: {fmt(ai.starting_price)}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Extra images strip */}
                      {extraImages.length > 0 && (
                        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.625rem', flexWrap: 'wrap' }}>
                          {extraImages.map((img) => (
                            <div key={img.id} style={{ width: 48, height: 48, borderRadius: 'var(--radius)', overflow: 'hidden', border: '1px solid var(--border)', flexShrink: 0 }}>
                              <img src={img.url} alt={item.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                            </div>
                          ))}
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', alignSelf: 'center', marginLeft: '0.25rem' }}>
                            {images.length} photo{images.length !== 1 ? 's' : ''} total
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Admin cancel controls inside drawer */}
          {isCancellable && (
            <section style={{ marginTop: '1rem', borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }}>
              <button
                className="btn btn-danger w-100"
                onClick={() => onCancelClick(auction)}
                style={{ fontWeight: 600, padding: '0.625rem' }}
              >
                Cancel Auction Listing
              </button>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page Component ─────────────────────────────────────────────────────────
export default function AdminAuctionsPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedAuction, setSelectedAuction] = useState(null);
  const [cancellingAuction, setCancellingAuction] = useState(null);

  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-auctions-list', statusFilter, page],
    queryFn: () => {
      const params = new URLSearchParams({ page, limit: 15 });
      if (statusFilter) params.set('status', statusFilter);
      return apiClient.get(`/admin/auctions?${params}`).then(r => r.data);
    },
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });

  const cancelMutation = useMutation({
    mutationFn: (auctionId) =>
      apiClient.patch(`/admin/auctions/${auctionId}/cancel`),
    onSuccess: (res) => {
      showToast(res.data?.message || 'Auction cancelled successfully', 'success');
      setCancellingAuction(null);
      queryClient.invalidateQueries({ queryKey: ['admin-auctions-list'] });
    },
    onError: (err) => {
      showToast(err.response?.data?.detail || 'Failed to cancel auction', 'error');
    }
  });

  const auctions = data?.data || [];
  const pagination = data?.pagination;

  // Client-side search matching title or seller email/name
  const filteredAuctions = auctions.filter(a => {
    if (!search) return true;
    const term = search.toLowerCase();

    // Check main auction title or attached items' titles
    const titleMatch = a.title?.toLowerCase().includes(term) ||
                       a.items?.some(ai => ai.item?.title?.toLowerCase().includes(term));

    const sellerName = `${a.seller?.first_name || ''} ${a.seller?.last_name || ''}`.toLowerCase();
    const sellerEmail = a.seller?.email?.toLowerCase() || '';

    return titleMatch || sellerName.includes(term) || sellerEmail.includes(term);
  });

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
          <h1 style={{ fontWeight: 800, fontSize: '1.5rem', margin: 0 }}>Auction Management</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
            {pagination ? `${pagination.total} platform auctions` : 'Review and moderate platform auctions'}
          </p>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="card-body p-3">
          <div className="row g-2 align-items-center">

            {/* Search filter */}
            <div className="col-md-7">
              <div style={{ position: 'relative' }}>
                <FiSearch size={15} style={{
                  position: 'absolute', left: '0.875rem', top: '50%',
                  transform: 'translateY(-50%)', color: 'var(--text-muted)'
                }} />
                <input
                  className="form-control form-control-sm"
                  style={{ paddingLeft: '2.25rem' }}
                  placeholder="Search by title, seller name or email…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
              </div>
            </div>

            {/* Status filter */}
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

            {/* Clear filter */}
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
            <h5>Failed to load auctions</h5>
            <p style={{ fontSize: '0.875rem' }}>Please verify your network connection or backend services.</p>
          </div>
        )}

        {/* Loaded Data Table */}
        {!isLoading && !isError && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
                  {[
                    'Title / Info', 'Seller', 'Status', 'Reserve Price',
                    'Bids', 'Schedule', 'Actions'
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
                {filteredAuctions.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <FiTag size={40} className="mb-2 mx-auto d-block" />
                      <h5 style={{ fontWeight: 700, margin: '0 0 0.25rem' }}>No auctions found</h5>
                      <p style={{ fontSize: '0.8125rem', margin: 0 }}>Try adjusting your filters or search terms.</p>
                    </td>
                  </tr>
                ) : (
                  filteredAuctions.map(auction => {
                    const isCancellable = auction.status === 'ACTIVE' || auction.status === 'SCHEDULED';

                    return (
                      <tr
                        key={auction.id}
                        onClick={() => setSelectedAuction(auction)}
                        style={{
                          borderBottom: '1px solid var(--border)', cursor: 'pointer',
                          transition: 'background 0.1s'
                        }}
                        onMouseOver={e => e.currentTarget.style.background = 'var(--surface)'}
                        onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                      >
                        {/* Title Info */}
                        <td style={{ padding: '0.75rem 1rem', fontWeight: 600, maxWidth: 220 }}>
                          <div style={{ color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {auction.title || `Auction #${auction.id.slice(0, 8)}`}
                          </div>
                          {auction.items && auction.items.length > 0 && (
                            <span style={{ fontSize: '0.7rem', color: 'var(--primary)', fontWeight: 600 }}>
                              {auction.items.length} item{auction.items.length > 1 ? 's' : ''} inside
                            </span>
                          )}
                        </td>

                        {/* Seller */}
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {auction.seller?.first_name} {auction.seller?.last_name}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {auction.seller?.email}
                          </div>
                        </td>

                        {/* Status badge */}
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <Badge label={auction.status} style={AUCTION_STATUS_STYLE[auction.status]} />
                        </td>

                        {/* Reserve Price */}
                        <td style={{ padding: '0.75rem 1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                          {auction.reserve_price ? fmt(auction.reserve_price) : (
                            <span style={{ fontStyle: 'italic', fontWeight: 500, color: 'var(--text-muted)' }}>
                              No Reserve
                            </span>
                          )}
                        </td>

                        {/* Bids */}
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                            {auction.bid_count} bid{auction.bid_count !== 1 ? 's' : ''}
                          </div>
                          {auction.highest_bid && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--primary)', fontWeight: 600 }}>
                              Top: {fmt(auction.highest_bid.amount)}
                            </div>
                          )}
                        </td>

                        {/* Schedule dates */}
                        <td style={{ padding: '0.75rem 1rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          <div>
                            <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>Starts:</span> {formatDateTime(auction.starts_at)}
                          </div>
                          <div style={{ marginTop: '0.25rem' }}>
                            <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>Ends:</span> {formatDateTime(auction.ends_at)}
                          </div>
                        </td>

                        {/* Actions column */}
                        <td style={{ padding: '0.75rem 1rem' }} onClick={e => e.stopPropagation()}>
                          {isCancellable ? (
                            <button
                              className="btn btn-outline-danger btn-sm"
                              onClick={() => setCancellingAuction(auction)}
                              style={{ fontWeight: 600 }}
                            >
                              Cancel
                            </button>
                          ) : (
                            <span style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>
                              —
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        {pagination && pagination.total_pages > 1 && (
          <div className="d-flex align-items-center justify-content-between p-3" style={{ borderTop: '1px solid var(--border)' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              Page {pagination.page} of {pagination.total_pages} — {pagination.total} total auctions
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

      {/* Custom Premium Cancel Warning Modal */}
      {cancellingAuction && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem',
          backdropFilter: 'blur(2px)'
        }}>
          <div style={{
            background: '#fff', borderRadius: 'var(--radius-xl)', width: '100%', maxWidth: 480,
            padding: '2rem', textAlign: 'center', boxShadow: 'var(--shadow-lg)'
          }}>
            <div style={{
              width: 56, height: 56, borderRadius: 'var(--radius-full)',
              background: 'var(--danger-light)', color: 'var(--danger)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 1.25rem'
            }}>
              <FiAlertCircle size={28} />
            </div>
            <h3 style={{ fontWeight: 800, fontSize: '1.25rem', marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
              Cancel Auction?
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.75rem', lineHeight: 1.6 }}>
              Are you sure you want to cancel the auction <strong>{cancellingAuction.title || `Auction #${cancellingAuction.id.slice(0, 8)}`}</strong>?<br />
              This will close active bidding immediately and release all attached items back to the <strong>APPROVED</strong> status for the seller. This action cannot be undone.
            </p>
            <div className="d-flex gap-2 justify-content-center">
              <button
                className="btn btn-danger"
                disabled={cancelMutation.isPending}
                onClick={() => cancelMutation.mutate(cancellingAuction.id)}
                style={{ fontWeight: 600, padding: '0.5rem 1.5rem' }}
              >
                {cancelMutation.isPending ? 'Cancelling...' : 'Yes, Cancel Auction'}
              </button>
              <button
                className="btn btn-outline-secondary"
                disabled={cancelMutation.isPending}
                onClick={() => setCancellingAuction(null)}
                style={{ fontWeight: 600, padding: '0.5rem 1.5rem' }}
              >
                No, Keep Active
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Detailed Auction Slide-over Drawer */}
      {selectedAuction && (
        <AuctionDetailDrawer
          auction={selectedAuction}
          onClose={() => setSelectedAuction(null)}
          onCancelClick={(a) => {
            setSelectedAuction(null);
            setCancellingAuction(a);
          }}
        />
      )}

    </div>
  );
}
