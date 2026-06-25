import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FiUsers, FiSearch, FiX, FiChevronRight,
} from 'react-icons/fi';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';

const ACCOUNT_STATUS_OPTIONS = ['ACTIVE', 'SUSPENDED', 'BANNED', 'DEACTIVATED'];
const KYC_TIER_OPTIONS = ['TIER_1', 'TIER_2', 'TIER_3'];

const STATUS_STYLE = {
  ACTIVE:      { bg: 'var(--success-light)', color: 'var(--success)' },
  SUSPENDED:   { bg: 'var(--warning-light)', color: 'var(--warning)' },
  BANNED:      { bg: 'var(--danger-light)',  color: 'var(--danger)'  },
  DEACTIVATED: { bg: '#F1F5F9',              color: 'var(--text-muted)' },
};

const ROLE_STYLE = {
  ADMIN:     { bg: '#EDE9FE', color: '#7C3AED' },
  SUPERUSER: { bg: '#FEE2E2', color: '#DC2626' },
  STAFF:     { bg: '#DBEAFE', color: '#2563EB' },
  USER:      { bg: '#F1F5F9', color: 'var(--text-muted)' },
};

function Badge({ label, style }) {
  return (
    <span style={{ background: style?.bg || '#F1F5F9', color: style?.color || 'var(--text-muted)', borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700, padding: '0.2em 0.65em', whiteSpace: 'nowrap' }}>
      {label}
    </span>
  );
}

function ActionMenu({ user, onAction, isPending }) {
  const [open, setOpen] = useState(false);
  const status = user.account_status;
  const actions = [
    status !== 'ACTIVE'    && { label: 'Reactivate', value: 'ACTIVE',    color: 'var(--success)' },
    status !== 'SUSPENDED' && { label: 'Suspend',    value: 'SUSPENDED', color: 'var(--warning)' },
    status !== 'BANNED'    && { label: 'Ban',         value: 'BANNED',    color: 'var(--danger)'  },
  ].filter(Boolean);

  return (
    <div style={{ position: 'relative' }} onClick={e => e.stopPropagation()}>
      <button className="btn btn-outline-secondary btn-sm" onClick={() => setOpen(o => !o)} disabled={isPending}>
        Actions
      </button>
      {open && (
        <div onMouseLeave={() => setOpen(false)} style={{ position: 'absolute', right: 0, top: '110%', background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-md)', zIndex: 50, minWidth: 140 }}>
          {actions.map(a => (
            <button key={a.value} onClick={() => { onAction(user.id, a.value); setOpen(false); }}
              style={{ display: 'block', width: '100%', padding: '0.625rem 1rem', background: 'none', border: 'none', textAlign: 'left', fontSize: '0.8125rem', fontWeight: 600, color: a.color, cursor: 'pointer' }}>
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Detail Drawer ──────────────────────────────────────────────────────────────
function UserDetailDrawer({ userId, onClose, onStatusChange, isPending }) {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-user-detail', userId],
    queryFn: () => apiClient.get(`/admin/users/${userId}`).then(r => r.data),
    enabled: !!userId,
  });

  const u = data;

  const fmt = (n) => n != null ? `₦${Number(n).toLocaleString('en-NG', { minimumFractionDigits: 2 })}` : '—';

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 200, display: 'flex' }}>
      {/* Backdrop */}
      <div onClick={onClose} style={{ flex: 1, background: 'rgba(0,0,0,0.4)' }} />
      {/* Panel */}
      <div style={{ width: 480, maxWidth: '95vw', background: '#fff', height: '100%', overflowY: 'auto', boxShadow: 'var(--shadow-lg)', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, background: '#fff', zIndex: 1 }}>
          <h2 style={{ fontWeight: 800, fontSize: '1.125rem', margin: 0 }}>User Detail</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}><FiX size={20} /></button>
        </div>

        {isLoading && <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>}

        {u && (
          <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

            {/* Identity */}
            <section>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>Identity</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {[
                  ['Name', `${u.first_name || ''} ${u.last_name || ''}`.trim() || '—'],
                  ['Email', u.email],
                  ['Phone', u.phone_number || '—'],
                  ['Role', <Badge label={u.role} style={ROLE_STYLE[u.role]} />],
                  ['Status', <Badge label={u.account_status} style={STATUS_STYLE[u.account_status]} />],
                  ['KYC Tier', u.kyc_tier?.replace('_', ' ')],
                  ['Email Verified', u.is_email_verified ? '✓ Yes' : '✗ No'],
                  ['Joined', u.created_at ? new Date(u.created_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'],
                  ['Last Login', u.last_login_at ? new Date(u.last_login_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Never'],
                ].map(([label, value]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8125rem', padding: '0.375rem 0', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{label}</span>
                    <span style={{ fontWeight: 600, textAlign: 'right' }}>{value}</span>
                  </div>
                ))}
              </div>
            </section>

            {/* Actions */}
            <section>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>Actions</div>
              <div className="d-flex gap-2 flex-wrap">
                {u.account_status !== 'ACTIVE'    && <button className="btn btn-success btn-sm" disabled={isPending} onClick={() => onStatusChange(u.id, 'ACTIVE')}>Reactivate</button>}
                {u.account_status !== 'SUSPENDED' && <button className="btn btn-warning btn-sm" disabled={isPending} onClick={() => onStatusChange(u.id, 'SUSPENDED')}>Suspend</button>}
                {u.account_status !== 'BANNED'    && <button className="btn btn-danger btn-sm"  disabled={isPending} onClick={() => onStatusChange(u.id, 'BANNED')}>Ban</button>}
              </div>
            </section>

            {/* Wallet */}
            {u.wallet && (
              <section>
                <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>Wallet</div>
                <div className="row g-2">
                  {[
                    ['Available', fmt(u.wallet.available_funds)],
                    ['Locked', fmt(u.wallet.locked_funds)],
                    ['Escrow', fmt(u.wallet.escrow_funds)],
                  ].map(([label, value]) => (
                    <div className="col-4" key={label}>
                      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', padding: '0.75rem', textAlign: 'center', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.25rem' }}>{label}</div>
                        <div style={{ fontWeight: 800, fontSize: '0.9375rem' }}>{value}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Seller Profile */}
            {u.seller_profile && (
              <section>
                <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>Seller Profile</div>
                {[
                  ['Type', u.seller_profile.seller_type],
                  ['Verification', u.seller_profile.verification_status],
                  ['Verified At', u.seller_profile.verified_at ? new Date(u.seller_profile.verified_at).toLocaleDateString('en-NG') : '—'],
                ].map(([label, value]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', padding: '0.375rem 0', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{label}</span>
                    <span style={{ fontWeight: 600 }}>{value}</span>
                  </div>
                ))}
              </section>
            )}

            {/* KYC */}
            {u.kyc_profile && (
              <section>
                <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>KYC</div>
                {[
                  ['Tier', u.kyc_profile.current_tier?.replace('_', ' ')],
                  ['Email Verified', u.kyc_profile.email_verified ? '✓' : '✗'],
                  ['Phone Verified', u.kyc_profile.phone_verified ? '✓' : '✗'],
                  ['BVN Verified', u.kyc_profile.bvn_verified ? '✓' : '✗'],
                  ['BVN Attempts', u.kyc_profile.bvn_attempt_count],
                ].map(([label, value]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', padding: '0.375rem 0', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{label}</span>
                    <span style={{ fontWeight: 600 }}>{value}</span>
                  </div>
                ))}
              </section>
            )}

            {/* Recent Bids */}
            {u.bids?.length > 0 && (
              <section>
                <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                  Recent Bids ({u.bids.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                  {u.bids.slice(0, 10).map(bid => (
                    <div key={bid.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', padding: '0.375rem 0', borderBottom: '1px solid var(--border)' }}>
                      <span style={{ color: 'var(--text-muted)' }}>{new Date(bid.placed_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short' })}</span>
                      <span style={{ fontWeight: 700 }}>{fmt(bid.amount)}</span>
                      <Badge label={bid.status} style={bid.status === 'WON' ? STATUS_STYLE.ACTIVE : { bg: '#F1F5F9', color: 'var(--text-muted)' }} />
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function AdminUsersPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [kycFilter, setKycFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-users-list', search, statusFilter, kycFilter, page],
    queryFn: () => {
      const params = new URLSearchParams({ page, limit: 20 });
      if (search)       params.set('search', search);
      if (statusFilter) params.set('account_status', statusFilter);
      if (kycFilter)    params.set('kyc_tier', kycFilter);
      return apiClient.get(`/admin/users?${params}`).then(r => r.data);
    },
    staleTime: 30_000,
    keepPreviousData: true,
  });

  const statusMutation = useMutation({
    mutationFn: ({ userId, account_status }) =>
      apiClient.patch(`/admin/users/${userId}/status`, { account_status }),
    onSuccess: (_, { account_status }) => {
      showToast(`User ${account_status.toLowerCase()}`, account_status === 'ACTIVE' ? 'success' : 'info');
      queryClient.invalidateQueries({ queryKey: ['admin-users-list'] });
      queryClient.invalidateQueries({ queryKey: ['admin-user-detail', _.data?.id] });
    },
    onError: err => showToast(err.response?.data?.detail || 'Action failed', 'error'),
  });

  const users = data?.data || [];
  const pagination = data?.pagination;

  return (
    <div style={{ padding: '2rem', minHeight: '100vh' }}>
      {/* Header */}
      <div className="d-flex align-items-center gap-3 mb-4">
        <div style={{ width: 44, height: 44, borderRadius: 'var(--radius)', background: 'var(--primary-50)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <FiUsers size={22} />
        </div>
        <div>
          <h1 style={{ fontWeight: 800, fontSize: '1.5rem', margin: 0 }}>User Management</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
            {pagination ? `${pagination.total} total users` : 'All registered users'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="card-body p-3">
          <div className="row g-2 align-items-center">
            <div className="col-md-5">
              <div style={{ position: 'relative' }}>
                <FiSearch size={15} style={{ position: 'absolute', left: '0.875rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input className="form-control form-control-sm" style={{ paddingLeft: '2.25rem' }} placeholder="Search by name or email…"
                  value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
              </div>
            </div>
            <div className="col-md-3">
              <select className="form-select form-select-sm" value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
                <option value="">All statuses</option>
                {ACCOUNT_STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="col-md-3">
              <select className="form-select form-select-sm" value={kycFilter} onChange={e => { setKycFilter(e.target.value); setPage(1); }}>
                <option value="">All KYC tiers</option>
                {KYC_TIER_OPTIONS.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
              </select>
            </div>
            <div className="col-md-1">
              <button className="btn btn-outline-secondary btn-sm w-100" onClick={() => { setSearch(''); setStatusFilter(''); setKycFilter(''); setPage(1); }}>Clear</button>
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card" style={{ borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
        {isLoading && <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>}
        {isError  && <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--danger)' }}>Failed to load users</div>}
        {!isLoading && !isError && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
                  {['Name', 'Email', 'Role', 'Status', 'KYC Tier', 'Joined', 'Actions'].map(h => (
                    <th key={h} style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 700, color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.length === 0
                  ? <tr><td colSpan={7} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>No users found</td></tr>
                  : users.map(user => (
                    <tr key={user.id}
                      onClick={() => setSelectedUserId(user.id)}
                      style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.1s' }}
                      onMouseOver={e => e.currentTarget.style.background = 'var(--surface)'}
                      onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <td style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>{user.first_name} {user.last_name}</td>
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--text-secondary)' }}>{user.email}</td>
                      <td style={{ padding: '0.75rem 1rem' }}><Badge label={user.role} style={ROLE_STYLE[user.role] || ROLE_STYLE.USER} /></td>
                      <td style={{ padding: '0.75rem 1rem' }}><Badge label={user.account_status} style={STATUS_STYLE[user.account_status] || STATUS_STYLE.ACTIVE} /></td>
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--text-secondary)' }}>{user.kyc_tier?.replace('_', ' ')}</td>
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{new Date(user.created_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short', year: 'numeric' })}</td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <ActionMenu user={user} isPending={statusMutation.isPending}
                          onAction={(userId, account_status) => statusMutation.mutate({ userId, account_status })} />
                      </td>
                    </tr>
                  ))
                }
              </tbody>
            </table>
          </div>
        )}

        {pagination && pagination.total_pages > 1 && (
          <div className="d-flex align-items-center justify-content-between p-3" style={{ borderTop: '1px solid var(--border)' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              Page {pagination.page} of {pagination.total_pages} — {pagination.total} users
            </span>
            <div className="d-flex gap-2">
              <button className="btn btn-outline-secondary btn-sm" disabled={!pagination.has_previous} onClick={() => setPage(p => p - 1)}>Previous</button>
              <button className="btn btn-outline-secondary btn-sm" disabled={!pagination.has_next} onClick={() => setPage(p => p + 1)}>Next</button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedUserId && (
        <UserDetailDrawer
          userId={selectedUserId}
          onClose={() => setSelectedUserId(null)}
          isPending={statusMutation.isPending}
          onStatusChange={(userId, account_status) => statusMutation.mutate({ userId, account_status })}
        />
      )}
    </div>
  );
}
