import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
    FiList, FiArrowRight, FiClock,
    FiCheckCircle, FiAlertCircle, FiXCircle,
    FiInbox
} from 'react-icons/fi';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';

const PAGE_SIZE = 20;

const STATUS_FILTERS = [
    { label: 'All', value: '' },
    { label: 'Active', value: 'ACTIVE' },
    { label: 'Outbid', value: 'OUTBID' },
    { label: 'Won', value: 'WON' },
    { label: 'Lost', value: 'LOST' },
];

const formatNaira = (amount) => `₦${Number(amount || 0).toLocaleString('en-NG', { minimumFractionDigits: 0 })}`;

const calcTimeLeft = (endDateStr) => {
    if (!endDateStr) return 'Ended';
    const diff = new Date(endDateStr).getTime() - Date.now();
    if (diff <= 0) return 'Ended';
    const totalSec = Math.floor(diff / 1000);
    const d = Math.floor(totalSec / 86400);
    const h = Math.floor((totalSec % 86400) / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    if (d > 0) return `${d}d ${h}h left`;
    if (h > 0) return `${h}h ${m}m left`;
    return `${m}m left`;
};

export default function MyBidsPage() {
    const navigate = useNavigate();
    const { showToast } = useToast();
    const [statusFilter, setStatusFilter] = useState('');
    const [page, setPage] = useState(1);
    const [allBids, setAllBids] = useState([]);

    const { data: bidPageData, isLoading, isError, isFetching, refetch } = useQuery({
        queryKey: ['my-bids', statusFilter, page],
        queryFn: async () => {
            const res = await apiClient.get('/users/me/bids', {
                params: {
                    status: statusFilter || undefined,
                    page,
                    limit: PAGE_SIZE
                }
            });
            return res.data;
        },
        refetchInterval: 30_000,
        placeholderData: (prev) => prev,
    });

    const pageItems = bidPageData?.data ?? [];
    const pagination = bidPageData?.pagination ?? {};
    const totalPages = pagination?.total_pages ?? 1;
    const totalItems = pagination?.total ?? null;
    const hasMore = page < totalPages;

    useEffect(() => {
        if (pageItems.length === 0 && page === 1) {
            setAllBids([]);
            return;
        }
        if (page === 1) {
            setAllBids(pageItems);
        } else {
            setAllBids((prev) => {
                const existingIds = new Set(prev.map((b) => b.id));
                const fresh = pageItems.filter((b) => !existingIds.has(b.id));
                return [...prev, ...fresh];
            });
        }
    }, [pageItems, page]);

    const handleFilterChange = useCallback((newStatus) => {
        setStatusFilter(newStatus);
        setPage(1);
        setAllBids([]);
    }, []);

    const handleLoadMore = useCallback(() => {
        setPage((p) => p + 1);
    }, []);

    // Empty state messages per tab
    const getEmptyStateMessage = () => {
        switch(statusFilter) {
            case 'ACTIVE': return "No active bids";
            case 'OUTBID': return "No outbid auctions";
            case 'WON': return "No won auctions yet";
            case 'LOST': return "No ended bids";
            default: return "You haven't placed any bids yet";
        }
    };

    // Render helper for status badge
    // Active → green "Highest Bidder", Outbid → red "Outbid", Won → primary "Won", Lost → grey "Ended"
    const renderStatusBadge = (bidStatus) => {
        const s = (bidStatus || '').toUpperCase();
        if (s === 'ACTIVE') return <span className="badge" style={{ backgroundColor: '#16A34A', color: '#fff' }}><FiCheckCircle size={12} className="me-1"/>Highest Bidder</span>;
        if (s === 'OUTBID') return <span className="badge" style={{ backgroundColor: '#DC2626', color: '#fff' }}><FiAlertCircle size={12} className="me-1"/>Outbid</span>;
        if (s === 'WON') return <span className="badge" style={{ backgroundColor: 'var(--primary)', color: '#fff' }}><FiCheckCircle size={12} className="me-1"/>Won</span>;
        if (s === 'LOST' || s === 'RELEASED') return <span className="badge" style={{ backgroundColor: '#6B7280', color: '#fff' }}><FiXCircle size={12} className="me-1"/>Ended</span>;
        return <span className="badge bg-secondary">{s}</span>;
    };

    return (
        <div style={{ backgroundColor: 'var(--bg-color)', minHeight: 'calc(100vh - 70px)', padding: '2rem 0' }}>
            <div className="container" style={{ maxWidth: 900 }}>
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ width: 44, height: 44, borderRadius: 'var(--radius)', backgroundColor: 'var(--primary-50)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <FiList size={20} />
                        </div>
                        <div>
                            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>My Bids</h1>
                            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Track and manage your auction bids</p>
                        </div>
                    </div>
                    {totalItems != null && (
                        <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--primary)', backgroundColor: 'var(--primary-50)', padding: '0.375rem 0.75rem', borderRadius: 'var(--radius-full)' }}>
                            {totalItems} Total Bids
                        </div>
                    )}
                </div>

                {/* Filter Tabs */}
                <div className="d-flex overflow-auto mb-4" style={{ gap: '0.5rem', paddingBottom: '0.5rem' }}>
                    {STATUS_FILTERS.map(f => {
                        const isActive = statusFilter === f.value;
                        return (
                            <button
                                key={f.label}
                                onClick={() => handleFilterChange(f.value)}
                                style={{
                                    whiteSpace: 'nowrap',
                                    padding: '0.5rem 1rem',
                                    borderRadius: 'var(--radius-full)',
                                    fontWeight: isActive ? 600 : 500,
                                    fontSize: '0.875rem',
                                    border: `1px solid ${isActive ? 'var(--primary)' : 'var(--border)'}`,
                                    backgroundColor: isActive ? 'var(--primary)' : 'var(--card-bg)',
                                    color: isActive ? '#fff' : 'var(--text-secondary)',
                                    transition: 'var(--transition-fast)'
                                }}
                            >
                                {f.label}
                            </button>
                        );
                    })}
                </div>

                {/* Error State */}
                {isError && (
                    <div className="card text-center p-5 mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
                        <FiAlertCircle size={32} style={{ color: 'var(--danger)', margin: '0 auto 1rem' }} />
                        <h4 style={{ fontWeight: 700 }}>Failed to load bids</h4>
                        <p style={{ color: 'var(--text-secondary)' }}>There was an error retrieving your bids.</p>
                        <button className="btn btn-primary mx-auto" onClick={() => refetch()}>Try Again</button>
                    </div>
                )}

                {/* Empty State */}
                {!isLoading && !isError && allBids.length === 0 && (
                    <div className="card text-center p-5 mb-4" style={{ borderRadius: 'var(--radius-xl)', borderStyle: 'dashed' }}>
                        <FiInbox size={32} style={{ color: 'var(--text-muted)', margin: '0 auto 1rem' }} />
                        <h4 style={{ fontWeight: 700, fontSize: '1.125rem' }}>{getEmptyStateMessage()}</h4>
                        {statusFilter === '' && (
                            <button className="btn btn-primary mx-auto mt-3" onClick={() => navigate('/auctions')}>
                                Browse Auctions
                            </button>
                        )}
                    </div>
                )}

                {/* Bids List */}
                {!isError && allBids.length > 0 && (
                    <div className="d-flex flex-column gap-3 mb-4">
                        {allBids.map(bid => {
                            const auction = bid.auction || {};
                            const auctionActive = (auction.status || '').toUpperCase() === 'ACTIVE';
                            const bidStatus = (bid.status || '').toUpperCase();

                            // Determine button action
                            let btnText = "View Auction";
                            if (auctionActive && (bidStatus === 'ACTIVE' || bidStatus === 'OUTBID')) {
                                btnText = "Bid Again";
                            }

                            return (
                                <div key={bid.id} className="card" style={{ borderRadius: 'var(--radius-lg)', padding: '1.25rem' }}>
                                    <div className="d-flex justify-content-between align-items-start align-items-sm-center flex-column flex-sm-row gap-3">
                                        <div>
                                            {renderStatusBadge(bidStatus)}
                                            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--primary)', marginTop: '0.5rem' }}>
                                                {formatNaira(bid.amount)}
                                            </div>
                                            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.25rem' }}>
                                                <FiClock size={12} />
                                                {auctionActive ? calcTimeLeft(auction.ends_at) : 'Ended'}
                                            </div>
                                        </div>

                                        <button
                                            className={`btn ${btnText === 'Bid Again' ? 'btn-primary' : 'btn-outline-primary'}`}
                                            onClick={() => navigate(`/auctions/${auction.id}`)}
                                        >
                                            {btnText} <FiArrowRight size={14} className="ms-1" />
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Skeleton Loader */}
                {isLoading && (
                    <div className="d-flex flex-column gap-3 mb-4">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="card p-3" style={{ borderRadius: 'var(--radius-lg)' }}>
                                <div className="skeleton" style={{ height: 20, width: 80, borderRadius: 4, marginBottom: 8 }} />
                                <div className="skeleton" style={{ height: 32, width: 140, borderRadius: 4, marginBottom: 8 }} />
                                <div className="skeleton" style={{ height: 16, width: 100, borderRadius: 4 }} />
                            </div>
                        ))}
                    </div>
                )}

                {/* Load More */}
                {!isLoading && !isError && hasMore && (
                    <div className="text-center">
                        <button
                            className="btn btn-outline-primary"
                            style={{ borderRadius: 'var(--radius-full)', padding: '0.5rem 1.5rem', fontWeight: 600 }}
                            onClick={handleLoadMore}
                            disabled={isFetching}
                        >
                            {isFetching ? 'Loading...' : 'Load More Bids'}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
