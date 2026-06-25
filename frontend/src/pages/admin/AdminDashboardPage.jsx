import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { FiUsers, FiTag, FiAlertCircle, FiDollarSign } from 'react-icons/fi';
import apiClient from '../../api/client';

const fetchDisputes    = () => apiClient.get('/admin/disputes?limit=5').then(r => r.data);
const fetchPendingItems = () => apiClient.get('/admin/items/pending?limit=10').then(r => r.data);
const fetchPendingKYC  = () => apiClient.get('/admin/kyc/pending?limit=10').then(r => r.data);
const fetchUsers       = () => apiClient.get('/users?limit=10').then(r => r.data);
const fetchOrders      = () => apiClient.get('/admin/orders?limit=10').then(r => r.data);
const fetchWallet      = () => apiClient.get('/admin/wallet-summary').then(r => r.data);

const ORDER_STATUS_COLORS = {
  COMPLETED:        { bg: 'var(--success-light)', color: 'var(--success)' },
  PENDING_SHIPMENT: { bg: 'var(--warning-light)', color: 'var(--warning)' },
  DISPUTED:         { bg: 'var(--danger-light)',  color: 'var(--danger)'  },
  SHIPPED:          { bg: 'var(--info-light)',    color: 'var(--info)'    },
  CANCELLED:        { bg: '#F1F5F9',              color: 'var(--text-muted)' },
};

const DISPUTE_STATUS_COLORS = {
  OPEN:         { bg: 'var(--danger-light)',  color: 'var(--danger)'   },
  UNDER_REVIEW: { bg: 'var(--info-light)',    color: 'var(--info)'     },
  RESOLVED:     { bg: 'var(--success-light)', color: 'var(--success)'  },
  DISMISSED:    { bg: '#F1F5F9',              color: 'var(--text-muted)' },
};

function StatusBadge({ status, map }) {
  const cfg = map[status] || { bg: '#F1F5F9', color: 'var(--text-muted)' };
  return (
    <span style={{ background: cfg.bg, color: cfg.color, borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700, padding: '0.25em 0.65em', whiteSpace: 'nowrap' }}>
      {status?.replace(/_/g, ' ')}
    </span>
  );
}

function StatCard({ icon: Icon, label, value, color, isLoading }) {
  return (
    <div className="card" style={{ borderRadius: 'var(--radius-xl)', padding: '1.25rem 1.5rem' }}>
      <div className="d-flex align-items-center justify-content-between mb-2">
        <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
        <div style={{ width: 36, height: 36, borderRadius: 'var(--radius)', background: `${color}18`, color, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={18} />
        </div>
      </div>
      {isLoading
        ? <div className="skeleton" style={{ height: 32, width: '60%' }} />
        : <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>{value ?? '—'}</div>
      }
    </div>
  );
}

const fmt = (n) => n != null ? `₦${Number(n).toLocaleString('en-NG', { minimumFractionDigits: 2 })}` : '—';

export default function AdminDashboardPage() {
  const { data: disputesData,  isLoading: loadingDisputes  } = useQuery({ queryKey: ['admin-disputes'],      queryFn: fetchDisputes,     staleTime: 30_000 });
  const { data: itemsData,     isLoading: loadingItems     } = useQuery({ queryKey: ['admin-pending-items'], queryFn: fetchPendingItems, staleTime: 30_000 });
  const { data: kycData,       isLoading: loadingKYC       } = useQuery({ queryKey: ['admin-pending-kyc'],  queryFn: fetchPendingKYC,   staleTime: 30_000 });
  const { data: usersData,     isLoading: loadingUsers     } = useQuery({ queryKey: ['admin-users'],         queryFn: fetchUsers,        staleTime: 30_000 });
  const { data: ordersData,    isLoading: loadingOrders    } = useQuery({ queryKey: ['admin-orders'],        queryFn: fetchOrders,       staleTime: 30_000 });
  const { data: walletData,    isLoading: loadingWallet    } = useQuery({ queryKey: ['admin-wallet'],        queryFn: fetchWallet,       staleTime: 30_000 });

  const disputes     = disputesData?.data  || (Array.isArray(disputesData) ? disputesData : []);
  const pendingItems = itemsData?.data     || (Array.isArray(itemsData)    ? itemsData    : []);
  const pendingKYC   = kycData?.data       || (Array.isArray(kycData)      ? kycData      : []);
  const orders       = ordersData?.data    || (Array.isArray(ordersData)   ? ordersData   : []);
  const wallet       = walletData || {};

  const openDisputeCount  = disputesData?.pagination?.total ?? disputes.filter(d => d.status === 'OPEN').length;
  const totalUsers        = usersData?.pagination?.total || usersData?.total || (usersData?.data?.length ?? 0);
  const pendingItemsCount = itemsData?.pagination?.total ?? pendingItems.length;
  const pendingKYCCount   = kycData?.pagination?.total ?? pendingKYC.length;

  return (
    <div style={{ padding: '2rem', minHeight: '100vh' }}>
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontWeight: 800, fontSize: '1.5rem', margin: 0 }}>Admin Dashboard</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>Platform overview</p>
      </div>

      {/* Stats row */}
      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-3">
          <StatCard icon={FiUsers}       label="Total Users"      value={totalUsers}             color="var(--primary)" isLoading={loadingUsers} />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard icon={FiTag}         label="Pending Items"    value={pendingItemsCount}      color="var(--success)" isLoading={loadingItems} />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard icon={FiAlertCircle} label="Open Disputes"    value={openDisputeCount}       color="var(--danger)"  isLoading={loadingDisputes} />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard icon={FiDollarSign}  label="Available Balance" value={fmt(wallet.available_funds)} color="var(--warning)" isLoading={loadingWallet} />
        </div>
      </div>

      {/* Moderation Queue */}
      <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="card-header">
          <h5 style={{ fontWeight: 700, margin: 0 }}>Moderation Queue</h5>
        </div>
        <div className="card-body">
          <div className="row g-3">
            {[
              { label: 'Pending Item Approvals', count: pendingItemsCount, loading: loadingItems,    to: '/admin/verify-sellers', color: 'var(--warning)' },
              { label: 'Pending KYC Documents',  count: pendingKYCCount,   loading: loadingKYC,     to: '/admin/kyc',            color: 'var(--info)'    },
              { label: 'Open Disputes',          count: openDisputeCount,    loading: loadingDisputes, to: '/admin/disputes',       color: 'var(--danger)'  },
            ].map(({ label, count, loading, to, color }) => (
              <div className="col-md-4" key={label}>
                <Link to={to} style={{ textDecoration: 'none' }}>
                  <div className="card h-100" style={{ borderRadius: 'var(--radius-lg)', border: count > 0 ? `1.5px solid ${color}` : '1px solid var(--border)' }}>
                     <div className="card-body d-flex align-items-center justify-content-between p-3">
                      <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{label}</span>
                      {loading
                        ? <div className="skeleton" style={{ width: 32, height: 24, borderRadius: 'var(--radius-full)' }} />
                        : <span style={{ background: count > 0 ? color : 'var(--border)', color: count > 0 ? '#fff' : 'var(--text-muted)', borderRadius: 'var(--radius-full)', fontWeight: 800, fontSize: '0.875rem', padding: '0.2em 0.7em', minWidth: 28, textAlign: 'center' }}>
                            {count}
                          </span>
                      }
                    </div>
                  </div>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Financial Summary */}
      <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="card-header">
          <h5 style={{ fontWeight: 700, margin: 0 }}>Financial Summary</h5>
        </div>
        <div className="card-body">
          <div className="row g-3">
            {[
              { label: 'Available Balance', value: fmt(wallet.available_funds) },
              { label: 'Locked Funds',      value: fmt(wallet.locked_funds)    },
              { label: 'Escrow Funds',      value: fmt(wallet.escrow_funds)    },
            ].map(({ label, value }) => (
              <div className="col-md-4" key={label}>
                <div style={{ padding: '1rem', background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>{label}</div>
                  {loadingWallet
                    ? <div className="skeleton" style={{ height: 24, width: '70%' }} />
                    : <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>{value}</div>
                  }
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="row g-4">
        {/* Recent Orders */}
        <div className="col-lg-7">
          <div className="card" style={{ borderRadius: 'var(--radius-xl)' }}>
            <div className="card-header d-flex align-items-center justify-content-between">
              <h5 style={{ fontWeight: 700, margin: 0 }}>Recent Orders</h5>
              <Link to="/admin/orders" style={{ fontSize: '0.8125rem', fontWeight: 600 }}>View all</Link>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Order ID', 'Amount', 'Status', 'Date'].map(h => (
                      <th key={h} style={{ padding: '0.625rem 1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loadingOrders
                    ? [1,2,3].map(i => <tr key={i}><td colSpan={4} style={{ padding: '0.75rem 1rem' }}><div className="skeleton" style={{ height: 16 }} /></td></tr>)
                    : orders.length === 0
                      ? <tr><td colSpan={4} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>No orders yet</td></tr>
                      : orders.slice(0, 10).map(order => (
                          <tr key={order.id} style={{ borderBottom: '1px solid var(--border)' }}>
                            <td style={{ padding: '0.625rem 1rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{String(order.id).slice(0, 8)}…</td>
                            <td style={{ padding: '0.625rem 1rem', fontWeight: 700 }}>{fmt(order.amount)}</td>
                            <td style={{ padding: '0.625rem 1rem' }}><StatusBadge status={order.status} map={ORDER_STATUS_COLORS} /></td>
                            <td style={{ padding: '0.625rem 1rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{new Date(order.created_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short' })}</td>
                          </tr>
                        ))
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Recent Disputes */}
        <div className="col-lg-5">
          <div className="card" style={{ borderRadius: 'var(--radius-xl)' }}>
            <div className="card-header d-flex align-items-center justify-content-between">
              <h5 style={{ fontWeight: 700, margin: 0 }}>Recent Disputes</h5>
              <Link to="/admin/disputes" style={{ fontSize: '0.8125rem', fontWeight: 600 }}>View all</Link>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Title', 'Status', 'Date'].map(h => (
                      <th key={h} style={{ padding: '0.625rem 1rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loadingDisputes
                    ? [1,2,3].map(i => <tr key={i}><td colSpan={3} style={{ padding: '0.75rem 1rem' }}><div className="skeleton" style={{ height: 16 }} /></td></tr>)
                    : disputes.length === 0
                      ? <tr><td colSpan={3} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>No disputes</td></tr>
                      : disputes.slice(0, 5).map(d => (
                          <tr key={d.id} style={{ borderBottom: '1px solid var(--border)', background: d.status === 'OPEN' ? '#FFF5F5' : 'transparent' }}>
                            <td style={{ padding: '0.625rem 1rem', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }}>{d.title}</td>
                            <td style={{ padding: '0.625rem 1rem' }}><StatusBadge status={d.status} map={DISPUTE_STATUS_COLORS} /></td>
                            <td style={{ padding: '0.625rem 1rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{new Date(d.created_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short' })}</td>
                          </tr>
                        ))
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
