import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiAlertCircle, FiArrowRight, FiInbox, FiClock, FiPackage, FiShield } from 'react-icons/fi';
import apiClient from '../../api/client';
import { useAuthStore } from '../../store/authStore';

const DISPUTE_STATUS = {
    OPEN:         { label: 'Open',         bg: '#FEF3C7',              color: '#D97706' },
    UNDER_REVIEW: { label: 'Under Review', bg: 'var(--info-light)',    color: 'var(--info)' },
    RESOLVED:     { label: 'Resolved',     bg: 'var(--success-light)', color: 'var(--success)' },
    DISMISSED:    { label: 'Dismissed',    bg: '#F1F5F9',              color: 'var(--text-muted)' },
};

const getAdminDisputes = async ({ page = 1, limit = 20 } = {}) => {
    const res = await apiClient.get(`/admin/disputes?page=${page}&limit=${limit}`);
    return res.data;
};

export default function AdminDisputesPage() {
    const navigate = useNavigate();
    const { user } = useAuthStore();

    const { data, isLoading, isError, refetch } = useQuery({
        queryKey: ['admin-disputes'],
        queryFn: getAdminDisputes,
        staleTime: 0,
    });

    const disputes = data?.data || [];

    return (
        <div style={{ backgroundColor: 'var(--bg-color)', minHeight: 'calc(100vh - 72px)', padding: '2rem 0' }}>
            <div className="container" style={{ maxWidth: 900 }}>
                {/* Header */}
                <div className="d-flex align-items-center gap-3 mb-4">
                    <div style={{ width: 44, height: 44, borderRadius: 'var(--radius)', backgroundColor: 'var(--warning-50)', color: 'var(--warning)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <FiShield size={22} />
                    </div>
                    <div>
                        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0 }}>Dispute Management</h1>
                        <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-muted)' }}>Open and under-review disputes requiring admin action</p>
                    </div>
                </div>

                {isLoading && (
                    <div className="d-flex flex-column gap-3">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="card p-3" style={{ borderRadius: 'var(--radius-lg)' }}>
                                <div className="d-flex gap-3 align-items-center">
                                    <div className="skeleton" style={{ width: 80, height: 24, borderRadius: 'var(--radius-full)' }} />
                                    <div className="flex-grow-1">
                                        <div className="skeleton" style={{ height: 18, width: '55%', marginBottom: 8 }} />
                                        <div className="skeleton" style={{ height: 13, width: '35%' }} />
                                    </div>
                                    <div className="skeleton" style={{ width: 100, height: 32, borderRadius: 'var(--radius)' }} />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {isError && (
                    <div className="card text-center p-5" style={{ borderRadius: 'var(--radius-lg)' }}>
                        <FiAlertCircle size={40} className="text-danger mb-3 mx-auto" />
                        <h5 style={{ fontWeight: 700 }}>Failed to load disputes</h5>
                        <button className="btn btn-primary mx-auto mt-2" onClick={() => refetch()}>Retry</button>
                    </div>
                )}

                {!isLoading && !isError && disputes.length === 0 && (
                    <div className="card text-center p-5" style={{ borderRadius: 'var(--radius-lg)', borderStyle: 'dashed', backgroundColor: 'transparent' }}>
                        <FiInbox size={48} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} className="mx-auto" />
                        <h5 style={{ fontWeight: 700 }}>No open disputes</h5>
                        <p className="text-muted">All disputes have been resolved.</p>
                    </div>
                )}

                {!isLoading && !isError && disputes.length > 0 && (
                    <div className="d-flex flex-column gap-3">
                        {disputes.map(dispute => {
                            const statusConfig = DISPUTE_STATUS[dispute.status] || DISPUTE_STATUS.OPEN;
                            return (
                                <div key={dispute.id} className="card" style={{ borderRadius: 'var(--radius-lg)', padding: '1.25rem', border: '1px solid var(--border)' }}>
                                    <div className="d-flex align-items-center gap-3 flex-wrap flex-sm-nowrap">
                                        <span className="badge" style={{ backgroundColor: statusConfig.bg, color: statusConfig.color, borderRadius: 'var(--radius-full)', fontSize: '0.75rem', fontWeight: 700, padding: '0.4em 0.8em', minWidth: 90, textAlign: 'center' }}>
                                            {statusConfig.label}
                                        </span>

                                        <div className="flex-grow-1 min-w-0">
                                            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.2rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {dispute.title}
                                            </div>
                                            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                    <FiClock size={12} /> {new Date(dispute.created_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short', year: 'numeric' })}
                                                </span>
                                                {dispute.raised_by && (
                                                    <span>Buyer: {dispute.raised_by.first_name} {dispute.raised_by.last_name}</span>
                                                )}
                                                {dispute.against && (
                                                    <span>Seller: {dispute.against.first_name} {dispute.against.last_name}</span>
                                                )}
                                            </div>
                                        </div>

                                        <button
                                            className="btn btn-warning btn-sm"
                                            style={{ fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '0.4rem', whiteSpace: 'nowrap' }}
                                            onClick={() => navigate(`/disputes/${dispute.id}`)}
                                        >
                                            Review <FiArrowRight size={14} />
                                        </button>
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
