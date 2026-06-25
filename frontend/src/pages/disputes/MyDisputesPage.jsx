import { useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
    FiAlertCircle, FiArrowRight, FiInbox, FiClock,
    FiPackage, FiShield
} from 'react-icons/fi';
import { getMyDisputes } from '../../api/orders';
import { useAuthStore } from '../../store/authStore';
import { useToast } from '../../components/common/Toast';

const DISPUTE_STATUS = {
    OPEN:         { label: 'Open',         bg: '#FEF3C7',              color: '#D97706' },
    UNDER_REVIEW: { label: 'Under Review', bg: 'var(--info-light)',    color: 'var(--info)' },
    RESOLVED:     { label: 'Resolved',     bg: 'var(--success-light)', color: 'var(--success)' },
    DISMISSED:    { label: 'Dismissed',    bg: '#F1F5F9',              color: 'var(--text-muted)' },
};

export default function MyDisputesPage() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const { showToast } = useToast();

    const { data: disputesData, isLoading, isError, refetch } = useQuery({
        queryKey: ['my-disputes'],
        queryFn: getMyDisputes,
        staleTime: 30_000,
    });

    const disputes = Array.isArray(disputesData) ? disputesData : (disputesData?.data ?? []);

    if (isError) {
        showToast('Failed to load disputes', 'error');
    }

    return (
        <div style={{ backgroundColor: 'var(--bg-color)', minHeight: 'calc(100vh - 72px)', padding: '2rem 0' }}>
            <div className="container" style={{ maxWidth: 800 }}>
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
                    <div style={{
                        width: 44, height: 44, borderRadius: 'var(--radius)',
                        backgroundColor: 'var(--primary-50)', color: 'var(--primary)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                        <FiAlertCircle size={20} />
                    </div>
                    <div>
                        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>My Disputes</h1>
                        <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Track disputes raised on your orders</p>
                    </div>
                </div>

                {/* Loading State */}
                {isLoading && (
                    <div className="d-flex flex-column gap-3">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="card p-3" style={{ borderRadius: 'var(--radius-lg)' }}>
                                <div className="d-flex gap-3 align-items-center">
                                    <div className="skeleton" style={{ width: 80, height: 24, borderRadius: 'var(--radius-full)' }} />
                                    <div className="flex-grow-1">
                                        <div className="skeleton" style={{ height: 18, width: '60%', marginBottom: 8 }} />
                                        <div className="skeleton" style={{ height: 14, width: '40%' }} />
                                    </div>
                                    <div className="skeleton" style={{ width: 100, height: 32, borderRadius: 'var(--radius)' }} />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Error State */}
                {isError && (
                    <div className="card text-center p-5" style={{ borderRadius: 'var(--radius-lg)' }}>
                        <FiAlertCircle size={40} className="text-danger mb-3 mx-auto" />
                        <h5 style={{ fontWeight: 700 }}>Something went wrong</h5>
                        <p className="text-muted">We couldn't retrieve your disputes at this time.</p>
                        <button className="btn btn-primary mx-auto" onClick={() => refetch()}>Try Again</button>
                    </div>
                )}

                {/* Empty State */}
                {!isLoading && !isError && (disputes || []).length === 0 && (
                    <div className="card text-center p-5" style={{ borderRadius: 'var(--radius-lg)', borderStyle: 'dashed', backgroundColor: 'transparent' }}>
                        <FiInbox size={48} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} className="mx-auto" />
                        <h5 style={{ fontWeight: 700 }}>No disputes found</h5>
                        <p className="text-muted" style={{ fontSize: '0.9375rem' }}>Disputes you raise or are involved in will appear here.</p>
                    </div>
                )}

                {/* Disputes List */}
                {!isLoading && !isError && (disputes || []).length > 0 && (
                    <div className="d-flex flex-column gap-3">
                        {disputes.map(dispute => {
                            const statusConfig = DISPUTE_STATUS[dispute.status] || DISPUTE_STATUS.OPEN;
                            return (
                                <div key={dispute.id} className="card" style={{ borderRadius: 'var(--radius-lg)', padding: '1.25rem', border: '1px solid var(--border)' }}>
                                    <div className="d-flex align-items-center gap-3 flex-wrap flex-sm-nowrap">
                                        {/* Status Badge */}
                                        <div style={{ minWidth: 100 }}>
                                            <span className="badge" style={{
                                                backgroundColor: statusConfig.bg,
                                                color: statusConfig.color,
                                                borderRadius: 'var(--radius-full)',
                                                fontSize: '0.75rem',
                                                fontWeight: 700,
                                                padding: '0.4em 0.8em'
                                            }}>
                                                {statusConfig.label}
                                            </span>
                                        </div>

                                        {/* Info */}
                                        <div className="flex-grow-1 min-w-0">
                                            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.25rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {dispute.title}
                                            </div>
                                            {dispute.order_item && (
                                                <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                    <FiPackage size={12} /> {dispute.order_item.title}
                                                </div>
                                            )}
                                            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.125rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                <FiClock size={12} /> Raised {new Date(dispute.created_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short', year: 'numeric' })}
                                            </div>
                                        </div>

                                        {/* Action */}
                                        <div>
                                            <Link to={`/disputes/${dispute.id}`} className="btn btn-outline-primary btn-sm" style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', whiteSpace: 'nowrap' }}>
                                                View Dispute <FiArrowRight size={14} />
                                            </Link>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
