/**
 * SellerDashboardPage.jsx — Seller's personal auction dashboard
 *
 * Shows stats (total, sold, earnings), a "Create New Auction" CTA,
 * and tabbed auction lists (Active / Draft / Ended) using the existing
 * AuctionCard component with seller-specific action buttons injected.
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    FiPlus, FiPackage, FiTrendingUp, FiDollarSign,
    FiEdit2, FiXCircle, FiShoppingBag, FiRefreshCw,
    FiCheckCircle, FiClock, FiAlertCircle,
} from 'react-icons/fi';

import apiClient from '../../api/client';
import { walletActions } from '../../api/wallet';
import AuctionCard from '../../components/auctions/AuctionCard';
import { useToast } from '../../components/common/Toast';
import './SellerDashboardPage.css';

/* ─── API helpers ──────────────────────────────────────────────────────────── */

const fetchMyAuctions = async (status) => {
    const res = await apiClient.get(`/users/me/auctions?status=${status}&limit=50`);
    // Backend returns PaginatedResponse: { data: [...], pagination: {...} }
    const payload = res.data?.data ?? res.data;
    return Array.isArray(payload) ? payload : [];
};

/* ─── Helpers ──────────────────────────────────────────────────────────────── */

const formatNaira = (amount) =>
    `₦${Number(amount || 0).toLocaleString('en-NG', { minimumFractionDigits: 0 })}`;

const TABS = [
    { key: 'active', label: 'Active',  icon: <FiCheckCircle size={14} /> },
    { key: 'draft',  label: 'Drafts',  icon: <FiClock size={14} /> },
    { key: 'ended',  label: 'Ended',   icon: <FiPackage size={14} /> },
];

/* ─── Stat card ────────────────────────────────────────────────────────────── */

function StatCard({ icon, label, value, accent }) {
    return (
        <div className="sdp__stat">
            <div className="sdp__stat-icon" style={{ background: accent + '22', color: accent }}>
                {icon}
            </div>
            <div>
                <div className="sdp__stat-value">{value}</div>
                <div className="sdp__stat-label">{label}</div>
            </div>
        </div>
    );
}

/* ─── Skeleton ─────────────────────────────────────────────────────────────── */

function SkeletonCard() {
    return (
        <div className="skeleton-card">
            <div className="skeleton skeleton-card__image" />
            <div className="skeleton-card__body">
                <div className="skeleton" style={{ height: 14, width: '80%' }} />
                <div className="skeleton" style={{ height: 12, width: '50%' }} />
                <div className="skeleton" style={{ height: 22, width: '60%', marginTop: 4 }} />
                <div className="skeleton" style={{ height: 36, width: '100%', marginTop: 8, borderRadius: 8 }} />
            </div>
        </div>
    );
}

/* ─── Main component ───────────────────────────────────────────────────────── */

export default function SellerDashboardPage() {
    const navigate = useNavigate();
    const qc = useQueryClient();
    const { showToast } = useToast();
    const [activeTab, setActiveTab] = useState('active');

    /* ── Data fetching ── */
    const { data: activeAuctions = [], isLoading: loadingActive } = useQuery({
        queryKey: ['myAuctions', 'active'],
        queryFn: () => fetchMyAuctions('active'),
        refetchInterval: 30_000,
    });

    const { data: draftAuctions = [], isLoading: loadingDraft } = useQuery({
        queryKey: ['myAuctions', 'draft'],
        queryFn: () => fetchMyAuctions('draft'),
    });

    const { data: endedAuctions = [], isLoading: loadingEnded } = useQuery({
        queryKey: ['myAuctions', 'ended'],
        queryFn: () => fetchMyAuctions('ended'),
    });

    /* Earnings: sum credit transactions of type 'sale' */
    const { data: txData } = useQuery({
        queryKey: ['wallet-transactions-seller'],
        queryFn: () => walletActions.getTransactions({ direction: 'credit', limit: 200 }),
    });

    const totalEarnings = (txData?.data ?? txData?.items ?? [])
        .filter((t) => t.type === 'sale' || t.type === 'auction_sale')
        .reduce((sum, t) => sum + Number(t.amount ?? 0), 0);

    const totalSold = endedAuctions.filter(
        (a) => (a.status ?? '').toUpperCase() === 'SETTLED'
    ).length;

    /* ── Cancel mutation ── */
    const cancelMutation = useMutation({
        mutationFn: (auctionId) => apiClient.delete(`/auctions/${auctionId}`),
        onSuccess: () => {
            showToast('Auction cancelled.', 'success');
            qc.invalidateQueries({ queryKey: ['myAuctions'] });
        },
        onError: () => showToast('Failed to cancel auction. Please try again.', 'error'),
    });

    /* ── Resolved list for current tab ── */
    const tabAuctions = {
        active: activeAuctions,
        draft:  draftAuctions,
        ended:  endedAuctions,
    }[activeTab] ?? [];

    const isLoading = { active: loadingActive, draft: loadingDraft, ended: loadingEnded }[activeTab];

    /* ── Action buttons for each auction (injected below AuctionCard) ── */
    const renderActions = (auction) => {
        const status     = (auction.status ?? '').toUpperCase();
        const hasBids    = (auction.bid_count ?? 0) > 0;
        const canCancel  = (status === 'DRAFT' || status === 'ACTIVE') && !hasBids;
        const isSettled  = status === 'SETTLED' || status === 'ENDED_NO_BIDS';

        return (
            <div className="sdp__card-actions">
                {status === 'DRAFT' && (
                    <button
                        className="btn btn-outline-primary sdp__action-btn"
                        onClick={(e) => { e.stopPropagation(); navigate(`/seller/edit-auction/${auction.id}`); }}
                        title="Edit draft"
                    >
                        <FiEdit2 size={13} /> Edit
                    </button>
                )}
                {canCancel && (
                    <button
                        className="btn sdp__action-btn sdp__action-btn--danger"
                        onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm('Cancel this auction? This cannot be undone.')) {
                                cancelMutation.mutate(auction.id);
                            }
                        }}
                        disabled={cancelMutation.isPending}
                        title="Cancel auction"
                    >
                        <FiXCircle size={13} /> Cancel
                    </button>
                )}
                {isSettled && (
                    <button
                        className="btn btn-outline-primary sdp__action-btn"
                        onClick={(e) => { e.stopPropagation(); navigate(`/auctions/${auction.id}`); }}
                        title="View auction & orders"
                    >
                        <FiShoppingBag size={13} /> View Orders
                    </button>
                )}
            </div>
        );
    };

    return (
        <div className="sdp page-container">

            {/* ─── Header ─────────────────────────────────────────────────── */}
            <div className="sdp__header">
                <div>
                    <h1 className="sdp__title">Seller Dashboard</h1>
                    <p className="sdp__subtitle">Manage your auctions and track your earnings</p>
                </div>
                <button
                    id="create-auction-btn"
                    className="btn btn-primary sdp__create-btn"
                    onClick={() => navigate('/seller/create-auction')}
                >
                    <FiPlus size={16} /> Create New Auction
                </button>
            </div>

            {/* ─── Stats ──────────────────────────────────────────────────── */}
            <div className="sdp__stats-grid">
                <StatCard
                    icon={<FiPackage size={20} />}
                    label="Total Auctions"
                    value={activeAuctions.length + draftAuctions.length + endedAuctions.length}
                    accent="var(--primary)"
                />
                <StatCard
                    icon={<FiCheckCircle size={20} />}
                    label="Total Sold"
                    value={totalSold}
                    accent="var(--success)"
                />
                <StatCard
                    icon={<FiTrendingUp size={20} />}
                    label="Active Now"
                    value={activeAuctions.length}
                    accent="#0D9488"
                />
                <StatCard
                    icon={<FiDollarSign size={20} />}
                    label="Total Earnings"
                    value={formatNaira(totalEarnings)}
                    accent="var(--warning)"
                />
            </div>

            {/* ─── Tabs ───────────────────────────────────────────────────── */}
            <div className="sdp__tabs">
                {TABS.map((tab) => {
                    const count = { active: activeAuctions, draft: draftAuctions, ended: endedAuctions }[tab.key].length;
                    return (
                        <button
                            key={tab.key}
                            id={`seller-tab-${tab.key}`}
                            className={`sdp__tab ${activeTab === tab.key ? 'sdp__tab--active' : ''}`}
                            onClick={() => setActiveTab(tab.key)}
                        >
                            {tab.icon}
                            {tab.label}
                            {count > 0 && (
                                <span className={`sdp__tab-badge ${activeTab === tab.key ? 'sdp__tab-badge--active' : ''}`}>
                                    {count}
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>

            {/* ─── Auction grid ───────────────────────────────────────────── */}
            {isLoading ? (
                <div className="row g-3">
                    {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="col-12 col-sm-6 col-md-4 col-xl-3">
                            <SkeletonCard />
                        </div>
                    ))}
                </div>
            ) : tabAuctions.length === 0 ? (
                <div className="sdp__empty">
                    <div className="sdp__empty-icon">
                        <FiPackage size={28} />
                    </div>
                    <div className="sdp__empty-title">
                        {activeTab === 'active' && 'No active auctions'}
                        {activeTab === 'draft'  && 'No draft auctions'}
                        {activeTab === 'ended'  && 'No ended auctions'}
                    </div>
                    <p className="sdp__empty-sub">
                        {activeTab === 'active' && 'Publish a draft to start accepting bids.'}
                        {activeTab === 'draft'  && "You haven't created any auctions yet."}
                        {activeTab === 'ended'  && 'Completed auctions will appear here.'}
                    </p>
                    {activeTab !== 'ended' && (
                        <button
                            className="btn btn-primary"
                            onClick={() => navigate('/seller/create-auction')}
                        >
                            <FiPlus size={14} /> Create Auction
                        </button>
                    )}
                </div>
            ) : (
                <div className="row g-3">
                    {tabAuctions.map((auction) => (
                        <div key={auction.id} className="col-12 col-sm-6 col-md-4 col-xl-3">
                            <div className="sdp__card-wrapper">
                                <AuctionCard auction={auction} />
                                {renderActions(auction)}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
