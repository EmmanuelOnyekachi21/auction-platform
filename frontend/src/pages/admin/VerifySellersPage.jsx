import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FiShield, FiCheckCircle, FiXCircle, FiSearch,
  FiUser, FiFileText, FiExternalLink, FiChevronDown, FiChevronUp, FiX,
} from 'react-icons/fi';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';

const fetchUnverifiedSellers = () =>
  apiClient.get('/admin/verify-users?limit=50').then(r => r.data);

// Modal that embeds the document in an iframe — works for both PDFs and images
function DocViewer({ url, title, onClose }) {
  const isPdf = url?.toLowerCase().includes('.pdf');
  // Route PDFs through the backend proxy so they're served with
  // Content-Disposition: inline instead of attachment
  const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
  const displayUrl = isPdf
    ? `${API}/users/documents/proxy?url=${encodeURIComponent(url)}`
    : url;

  return (
    <div
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{ background: '#fff', borderRadius: 'var(--radius-xl)', width: '100%', maxWidth: 900, height: '85vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.875rem 1.25rem', borderBottom: '1px solid var(--border)' }}>
          <span style={{ fontWeight: 700, fontSize: '0.9375rem' }}>{title || 'Document'}</span>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <a href={displayUrl} target="_blank" rel="noopener noreferrer" className="btn btn-outline-primary btn-sm">
              <FiExternalLink size={13} /> Open in tab
            </a>
            <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '0.25rem' }}>
              <FiX size={18} />
            </button>
          </div>
        </div>
        {/* Content */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {isPdf ? (
            <iframe
              src={displayUrl}
              title={title}
              style={{ width: '100%', height: '100%', border: 'none' }}
            />
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem', background: '#f8f8f8' }}>
              <img src={url} alt={title} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: 'var(--radius)' }} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DocLink({ url, title }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
          fontSize: '0.8125rem', fontWeight: 600, color: 'var(--primary)',
          background: 'var(--primary-50)', borderRadius: 'var(--radius)',
          padding: '0.3rem 0.65rem', border: 'none', cursor: 'pointer',
        }}
      >
        <FiFileText size={13} />
        {title || 'View Document'}
      </button>
      {open && <DocViewer url={url} title={title} onClose={() => setOpen(false)} />}
    </>
  );
}

function SellerCard({ user, onApprove, onReject, isPending }) {
  const [expanded, setExpanded] = useState(false);
  const [rejectMode, setRejectMode] = useState(false);
  const [reason, setReason] = useState('');
  const { showToast } = useToast();

  const docs = user.seller_profile?.verification_docs || [];

  const handleReject = () => {
    if (!reason.trim()) { showToast('Please enter a rejection reason', 'error'); return; }
    onReject(user.id, reason);
    setRejectMode(false);
    setReason('');
  };

  return (
    <div className="card" style={{ borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
      {/* Main row */}
      <div style={{ padding: '1.25rem', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: '1rem' }}>{user.first_name} {user.last_name}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', marginBottom: '0.4rem' }}>{user.email}</div>
          <div className="d-flex align-items-center gap-2 flex-wrap">
            {user.seller_profile?.seller_type && (
              <span style={{ background: 'var(--primary-50)', color: 'var(--primary)', borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700, padding: '0.2em 0.65em' }}>
                {user.seller_profile.seller_type === 'INDIVIDUAL' ? 'Individual' : user.seller_profile.seller_type === 'BUSINESS' ? 'Business' : user.seller_profile.seller_type}
              </span>
            )}
            {docs.length > 0 && (
              <span style={{ background: 'var(--success-light)', color: 'var(--success)', borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700, padding: '0.2em 0.65em' }}>
                {docs.length} document{docs.length > 1 ? 's' : ''} attached
              </span>
            )}
            {docs.length === 0 && (
              <span style={{ background: 'var(--warning-light)', color: 'var(--warning)', borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700, padding: '0.2em 0.65em' }}>
                No documents
              </span>
            )}
          </div>
        </div>

        <div className="d-flex align-items-center gap-2 flex-wrap">
          {docs.length > 0 && (
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={() => setExpanded(e => !e)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
            >
              {expanded ? <FiChevronUp size={14} /> : <FiChevronDown size={14} />}
              {expanded ? 'Hide docs' : 'View docs'}
            </button>
          )}
          {!rejectMode && (
            <>
              <button
                className="btn btn-success btn-sm"
                onClick={() => onApprove(user.id)}
                disabled={isPending}
              >
                <FiCheckCircle size={14} /> Approve
              </button>
              <button
                className="btn btn-outline-danger btn-sm"
                onClick={() => setRejectMode(true)}
                disabled={isPending}
              >
                <FiXCircle size={14} /> Reject
              </button>
            </>
          )}
        </div>
      </div>

      {/* Documents panel */}
      {expanded && docs.length > 0 && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '1rem 1.25rem', background: 'var(--surface)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
            Verification Documents
          </div>
          <div className="d-flex flex-wrap gap-2">
            {docs.map(doc => (
              <DocLink key={doc.id} url={doc.url} title={doc.title} />
            ))}
          </div>
        </div>
      )}

      {/* Reject form */}
      {rejectMode && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '1rem 1.25rem', background: '#FFF5F5' }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--danger)', marginBottom: '0.5rem' }}>
            Rejection reason (required)
          </div>
          <textarea
            className="form-control mb-2"
            rows={2}
            placeholder="Explain why this application is being rejected…"
            value={reason}
            onChange={e => setReason(e.target.value)}
          />
          <div className="d-flex gap-2">
            <button className="btn btn-danger btn-sm" onClick={handleReject} disabled={isPending}>
              <FiXCircle size={14} /> Confirm Reject
            </button>
            <button className="btn btn-outline-secondary btn-sm" onClick={() => { setRejectMode(false); setReason(''); }}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function VerifySellersPage() {
  const [search, setSearch] = useState('');
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['unverified-sellers'],
    queryFn: fetchUnverifiedSellers,
    staleTime: 0,
  });

  const sellers = (Array.isArray(data) ? data : data?.data || []).filter(u =>
    !search ||
    u.email?.toLowerCase().includes(search.toLowerCase()) ||
    u.first_name?.toLowerCase().includes(search.toLowerCase()) ||
    u.last_name?.toLowerCase().includes(search.toLowerCase())
  );

  const verifyMutation = useMutation({
    mutationFn: ({ userId, isVerified, reason }) =>
      apiClient.patch(`/users/${userId}/seller-profile/verify`, {
        is_verified: isVerified,
        rejection_reason: reason || null,
      }),
    onSuccess: (_, { isVerified }) => {
      showToast(isVerified ? 'Seller verified!' : 'Seller rejected', isVerified ? 'success' : 'info');
      queryClient.invalidateQueries({ queryKey: ['unverified-sellers'] });
    },
    onError: (err) => showToast(err.response?.data?.detail || 'Action failed', 'error'),
  });

  return (
    <div style={{ padding: '2rem', minHeight: '100vh' }}>
      <div className="d-flex align-items-center gap-3 mb-4">
        <div style={{ width: 44, height: 44, borderRadius: 'var(--radius)', background: 'var(--primary-50)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <FiShield size={22} />
        </div>
        <div>
          <h1 style={{ fontWeight: 800, fontSize: '1.5rem', margin: 0 }}>Seller Verification</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
            Review pending seller applications and their documents
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="card-body p-3">
          <div style={{ position: 'relative' }}>
            <FiSearch size={16} style={{ position: 'absolute', left: '0.875rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              className="form-control"
              style={{ paddingLeft: '2.25rem' }}
              placeholder="Search by name or email…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="d-flex flex-column gap-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="card p-3" style={{ borderRadius: 'var(--radius-lg)' }}>
              <div className="skeleton" style={{ height: 20, width: '40%', marginBottom: 8 }} />
              <div className="skeleton" style={{ height: 14, width: '25%' }} />
            </div>
          ))}
        </div>
      )}

      {isError && (
        <div className="card text-center p-5" style={{ borderRadius: 'var(--radius-lg)' }}>
          <p style={{ color: 'var(--danger)' }}>Failed to load sellers</p>
          <button className="btn btn-primary mx-auto" onClick={() => refetch()}>Retry</button>
        </div>
      )}

      {!isLoading && !isError && sellers.length === 0 && (
        <div className="card text-center p-5" style={{ borderRadius: 'var(--radius-lg)', borderStyle: 'dashed', background: 'transparent' }}>
          <FiUser size={40} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} className="mx-auto" />
          <h5 style={{ fontWeight: 700 }}>No pending applications</h5>
          <p style={{ color: 'var(--text-muted)' }}>All seller applications have been reviewed.</p>
        </div>
      )}

      <div className="d-flex flex-column gap-3">
        {sellers.map(user => (
          <SellerCard
            key={user.id}
            user={user}
            isPending={verifyMutation.isPending}
            onApprove={(userId) => verifyMutation.mutate({ userId, isVerified: true })}
            onReject={(userId, reason) => verifyMutation.mutate({ userId, isVerified: false, reason })}
          />
        ))}
      </div>
    </div>
  );
}
