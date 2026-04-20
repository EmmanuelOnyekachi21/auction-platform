/**
 * AuctionDetailPage.jsx — Full Auction Detail View
 *
 * Route: /auctions/:auctionId  (public, under MainLayout)
 *
 * Layout:
 *  - Left 60% : image gallery + item details card (description, specs, seller)
 *  - Right 40% : live status badge, countdown timer, current bid, place bid,
 *                bid history, share button
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    FiPackage, FiTag, FiTrendingUp, FiEye, FiClock,
    FiCheckCircle, FiShare2, FiChevronDown, FiChevronUp,
    FiAlertCircle, FiCreditCard, FiArrowLeft,
} from 'react-icons/fi';

import { getAuction } from '../../api/auctions';
import { walletActions } from '../../api/wallet';
import apiClient from '../../api/client';
import { useAuthStore } from '../../store/authStore';
import { useToast } from '../../components/common/Toast';
import './AuctionDetailPage.css';

/* ══════════════════════════════════════════════════════════════════════════════
   CONSTANTS & HELPERS
══════════════════════════════════════════════════════════════════════════════ */

const CONDITION_STYLES = {
    new:      { label: 'New',      bg: '#16A34A', color: '#fff' },
    like_new: { label: 'Like New', bg: '#0D9488', color: '#fff' },
    good:     { label: 'Good',     bg: '#2563EB', color: '#fff' },
    fair:     { label: 'Fair',     bg: '#D97706', color: '#fff' },
    poor:     { label: 'Poor',     bg: '#DC2626', color: '#fff' },
};

/**
 * Format a number as Nigerian naira with thousands separators.
 */
const formatNaira = (amount) =>
    `₦${Number(amount || 0).toLocaleString('en-NG', { minimumFractionDigits: 0 })}`;

/**
 * Break an ISO timestamp into { days, hours, minutes, seconds, isExpired, isUrgent }.
 */
const calcTimeLeft = (endDateStr) => {
    const diff = new Date(endDateStr).getTime() - Date.now();
    if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0, isExpired: true, isUrgent: false };
    const totalSec = Math.floor(diff / 1000);
    return {
        days:     Math.floor(totalSec / 86400),
        hours:    Math.floor((totalSec % 86400) / 3600),
        minutes:  Math.floor((totalSec % 3600) / 60),
        seconds:  totalSec % 60,
        isExpired: false,
        isUrgent:  diff < 3_600_000, // < 1 hour
    };
};

/**
 * Human-readable "time ago" from an ISO string.
 */
const timeAgo = (isoStr) => {
    if (!isoStr) return '';
    const diff = Date.now() - new Date(isoStr).getTime();
    const sec  = Math.floor(diff / 1000);
    if (sec < 60)   return `${sec}s ago`;
    const min = Math.floor(sec / 60);
    if (min < 60)   return `${min} min ago`;
    const hr  = Math.floor(min / 60);
    if (hr  < 24)   return `${hr} hour${hr > 1 ? 's' : ''} ago`;
    const day = Math.floor(hr / 24);
    return `${day} day${day > 1 ? 's' : ''} ago`;
};

/**
 * Pad a number to always be 2 digits.
 */
const pad2 = (n) => String(n).padStart(2, '0');

/* ══════════════════════════════════════════════════════════════════════════════
   SUB-COMPONENTS
══════════════════════════════════════════════════════════════════════════════ */

/* ─── Image Gallery ─────────────────────────────────────────────────────────── */
function ImageGallery({ images, title }) {
    const [activeIdx, setActiveIdx] = useState(0);

    const resolvedImages = Array.isArray(images) ? images : [];
    const displayImages  = resolvedImages.slice(0, 8); // max 8 thumbnails
    const activeImage    = displayImages[activeIdx] ?? null;

    return (
        <>
            {/* Main image */}
            <div className="adp__main-image-wrapper">
                {activeImage ? (
                    <img
                        className="adp__main-image"
                        src={activeImage.url ?? activeImage}
                        alt={`${title} — image ${activeIdx + 1}`}
                        key={activeIdx} /* force re-render on swap */
                    />
                ) : (
                    <div className="adp__image-placeholder">
                        <FiPackage size={52} />
                        <span>No image available</span>
                    </div>
                )}
            </div>

            {/* Thumbnails */}
            {displayImages.length > 1 && (
                <div className="adp__thumbnails" role="list" aria-label="Image thumbnails">
                    {displayImages.map((img, i) => (
                        <button
                            key={i}
                            role="listitem"
                            className={`adp__thumb ${i === activeIdx ? 'adp__thumb--active' : ''}`}
                            onClick={() => setActiveIdx(i)}
                            aria-label={`View image ${i + 1}`}
                        >
                            <img src={img.url ?? img} alt={`Thumbnail ${i + 1}`} />
                        </button>
                    ))}
                </div>
            )}
        </>
    );
}

/* ─── Countdown Timer ───────────────────────────────────────────────────────── */
function CountdownTimer({ endTime }) {
    const [timeLeft, setTimeLeft] = useState(() => calcTimeLeft(endTime));
    const intervalRef = useRef(null);

    useEffect(() => {
        // Tick immediately, then every second
        setTimeLeft(calcTimeLeft(endTime));
        intervalRef.current = setInterval(() => {
            setTimeLeft(calcTimeLeft(endTime));
        }, 1000);

        return () => clearInterval(intervalRef.current); // cleanup on unmount / endTime change
    }, [endTime]);

    if (timeLeft.isExpired) {
        return <div className="adp__countdown-ended">⏱ Auction Ended</div>;
    }

    const units = [
        { value: timeLeft.days,    label: 'Days' },
        { value: timeLeft.hours,   label: 'Hours' },
        { value: timeLeft.minutes, label: 'Mins' },
        { value: timeLeft.seconds, label: 'Secs' },
    ];

    return (
        <div className="adp__countdown" aria-label="Time remaining">
            {units.map((unit, i) => (
                <div key={unit.label} style={{ display: 'contents' }}>
                    <div className="adp__countdown-unit">
                        <span
                            className={`adp__countdown-value ${timeLeft.isUrgent ? 'adp__countdown-value--urgent' : ''}`}
                        >
                            {pad2(unit.value)}
                        </span>
                        <span className="adp__countdown-label">{unit.label}</span>
                    </div>
                    {i < units.length - 1 && (
                        <span className="adp__countdown-sep" aria-hidden="true">:</span>
                    )}
                </div>
            ))}
        </div>
    );
}

/* ─── Status Badge ──────────────────────────────────────────────────────────── */
function StatusBadge({ status }) {
    const s = (status || '').toUpperCase();

    if (s === 'ACTIVE') {
        return (
            <span className="adp__status adp__status--active">
                <span className="adp__pulse-dot" aria-hidden="true" />
                Live
            </span>
        );
    }
    if (s === 'DRAFT') {
        return <span className="adp__status adp__status--draft">Draft</span>;
    }
    if (s === 'SETTLEMENT_IN_PROGRESS') {
        return <span className="adp__status adp__status--settling">Settling…</span>;
    }
    if (s === 'SCHEDULED') {
        return (
            <span className="adp__status adp__status--draft">
                <FiClock size={11} /> Scheduled
            </span>
        );
    }
    // ENDED_NO_BIDS | SETTLED | CANCELLED | unknown
    return <span className="adp__status adp__status--ended">Ended</span>;
}

/* ─── Bid History Row ───────────────────────────────────────────────────────── */
function BidHistorySection({ bids, userBidId }) {
    const sorted = [...(Array.isArray(bids) ? bids : [])]
        .sort((a, b) => (b.amount ?? 0) - (a.amount ?? 0))
        .slice(0, 10);

    if (sorted.length === 0) {
        return (
            <div className="adp__bids-empty">
                <div className="adp__bids-empty-icon">
                    <FiTrendingUp size={22} style={{ color: 'var(--text-muted)' }} />
                </div>
                <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    No bids yet
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    Be the first to place a bid!
                </div>
            </div>
        );
    }

    return (
        <div>
            {sorted.map((bid, i) => (
                <div key={bid.id ?? i} className="adp__bid-row" style={{ borderLeft: bid.id === userBidId ? '3px solid var(--primary)' : undefined, paddingLeft: bid.id === userBidId ? '0.5rem' : undefined }}>
                    <div className="adp__bid-row-rank">#{i + 1}</div>
                    <div className="adp__bid-row-name">Bidder #{i + 1}</div>
                    <div className="adp__bid-row-amount">{formatNaira(bid.amount)}</div>
                    <div className="adp__bid-row-time">{timeAgo(bid.created_at ?? bid.placed_at)}</div>
                </div>
            ))}
        </div>
    );
}

/* ══════════════════════════════════════════════════════════════════════════════
   MAIN PAGE COMPONENT
══════════════════════════════════════════════════════════════════════════════ */

export default function AuctionDetailPage() {
    const { auctionId } = useParams();
    const navigate = useNavigate();
    const { showToast } = useToast();
    const { user, isAuthenticated } = useAuthStore();

    /* ── Description expand state ── */
    const [descExpanded, setDescExpanded] = useState(false);
    const DESC_THRESHOLD = 300;

    /* ── Bid states ── */
    const [bidAmount, setBidAmount] = useState('');
    const [bidError, setBidError] = useState('');
    const [bidSuccess, setBidSuccess] = useState(false);
    const bidHistoryRef = useRef(null);
    const qc = useQueryClient();

    /* ── Fetch auction ── */
    const {
        data: auction,
        isLoading,
        isError,
        error,
    } = useQuery({
        queryKey: ['auction', auctionId],
        queryFn: () => getAuction(auctionId),
        enabled: !!auctionId,
        refetchInterval: 30_000,
        retry: 2,
    });

    /* ── Fetch wallet balance when authenticated ── */
    const { data: walletData } = useQuery({
        queryKey: ['wallet'],
        queryFn: walletActions.getWallet,
        enabled: isAuthenticated,
        staleTime: 30_000,
    });

    /* ── Live bid state polling ── */
    const { data: bidState, dataUpdatedAt } = useQuery({
        queryKey: ['bid-state', auctionId],
        queryFn: () => apiClient.get(`/auctions/${auctionId}/bid-state`).then(r => r.data?.data ?? r.data),
        refetchInterval: 10_000,
        enabled: !!auctionId,
    });

    /* ── Bid history ── */
    const { data: bidHistoryData } = useQuery({
        queryKey: ['auction-bids', auctionId],
        queryFn: () => apiClient.get(`/auctions/${auctionId}/bids?limit=10`).then(r => r.data?.data ?? []),
        refetchInterval: 10_000,
        enabled: !!auctionId,
    });
    const liveBids = Array.isArray(bidHistoryData) ? bidHistoryData : [];

    /* ── Place bid mutation ── */
    const placeBidMutation = useMutation({
        mutationFn: (amount) => apiClient.post(`/auctions/${auctionId}/bids`, { amount }),
        onSuccess: (res) => {
            const data = res.data?.data ?? res.data;
            setBidSuccess(true);
            setBidError('');
            setBidAmount('');
            showToast(`Your bid of ${formatNaira(data?.bid?.amount)} has been placed`, 'success');
            qc.invalidateQueries({ queryKey: ['bid-state', auctionId] });
            qc.invalidateQueries({ queryKey: ['auction-bids', auctionId] });
            qc.invalidateQueries({ queryKey: ['wallet'] });
            setTimeout(() => setBidSuccess(false), 2000);
            bidHistoryRef.current?.scrollIntoView({ behavior: 'smooth' });
        },
        onError: (err) => {
            const code = err?.response?.data?.code;
            const msg = err?.response?.data?.message ?? '';
            if (code === 'INSUFFICIENT_FUNDS') setBidError('Insufficient wallet balance. Fund your wallet to continue.');
            else if (code === 'ALREADY_HIGHEST_BIDDER') setBidError('You are already the highest bidder.');
            else if (code === 'INVALID_BID_AMOUNT') setBidError(msg || 'Bid amount is too low.');
            else if (code === 'AUCTION_NOT_ACTIVE') setBidError('This auction has ended.');
            else if (
                code === 'KYC_LIMIT_EXCEEDED' ||
                (code === 'PERMISSION_DENIED' && msg.includes('KYC tier'))
            ) {
                setBidError(
                    <span>
                        Your bid exceeds your current limit.{' '}
                        <Link to="/kyc" style={{ fontWeight: 600 }}>Verify your identity</Link>{' '}
                        to bid higher.
                    </span>
                );
            }
            else setBidError(msg || 'Failed to place bid. Please try again.');
        },
    });

    /* ── Share handler ── */
    const handleShare = useCallback(async () => {
        try {
            await navigator.clipboard.writeText(window.location.href);
            showToast('Link copied!', 'success');
        } catch {
            showToast('Could not copy link. Please copy it manually.', 'error');
        }
    }, [showToast]);

    /* ── Loading ── */
    if (isLoading) {
        return (
            <div className="adp__loading" role="status" aria-label="Loading auction">
                <div className="adp__spinner" />
                <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Loading auction…</span>
            </div>
        );
    }

    /* ── Error / Not found ── */
    if (isError || !auction) {
        const is404 = error?.response?.status === 404;
        return (
            <div className="adp">
                <div className="container" style={{ maxWidth: 900 }}>
                    <div className="adp__error">
                        <div className="adp__error-icon">
                            <FiAlertCircle size={28} />
                        </div>
                        <div className="adp__error-title">
                            {is404 ? 'Auction Not Found' : 'Failed to Load Auction'}
                        </div>
                        <p className="adp__error-sub">
                            {is404
                                ? 'This auction may have been removed or the link is incorrect.'
                                : 'Something went wrong while loading the auction. Please try again.'}
                        </p>
                        <button className="btn btn-primary" onClick={() => navigate('/auctions')}>
                            <FiArrowLeft size={15} /> Browse Auctions
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    /* ── Destructure auction data ── */
    const {
        id,
        title: auctionTitle,
        status,
        ends_at,
        starts_at,
        highest_bid,
        bid_count      = 0,
        bid_increment  = 0,
        reserve_price_met,
        reserve_progress_percent,
        bids           = [],
        seller,
    } = auction;

    // Items are nested: auction.items[0].item
    const firstAuctionItem = auction.items?.[0];
    const item = firstAuctionItem?.item ?? null;
    const starting_price = firstAuctionItem?.starting_price ?? 0;

    // Title: auction title or fall back to item title
    const title = auctionTitle || item?.title || 'Untitled Auction';

    /* Resolve image list from item */
    const images = item?.images ?? [];

    /* Condition */
    const conditionKey = (item?.condition ?? 'good').toLowerCase().replace(/\s+/g, '_');
    const condStyle    = CONDITION_STYLES[conditionKey] ?? CONDITION_STYLES.good;

    /* Category */
    const categoryName = item?.category?.name ?? auction.category?.name ?? null;

    /* Current bid display */
    const currentBidAmount = bidState?.highest_bid_amount ?? highest_bid?.amount ?? null;
    const liveBidCount = bidState?.bid_count ?? bid_count ?? 0;
    const hasBids = liveBidCount > 0 && currentBidAmount !== null;

    /* Minimum next bid */
    const minBid = bidState?.minimum_next_bid ?? (hasBids
        ? (Number(currentBidAmount) + Number(bid_increment || 0))
        : Number(starting_price ?? 0));

    /* User current bid */
    const userCurrentBid = bidState?.user_current_bid ?? null;

    /* Seller meta */
    const sellerName = seller
        ? `${seller.first_name ?? ''} ${seller.last_name ?? ''}`.trim()
        : 'Unknown Seller';
    const sellerInitial = sellerName?.[0]?.toUpperCase() ?? 'S';
    const isVerified    = seller?.is_verified_seller ?? false;
    const memberYear    = seller?.member_since
        ? new Date(seller.member_since).getFullYear()
        : null;
    const totalSales    = seller?.total_sales ?? null;

    /* Description */
    const description     = item?.description ?? auction.description ?? '';
    const longDescription = description.length > DESC_THRESHOLD;

    /* Wallet balance */
    const walletBalance = walletData?.available_funds ?? walletData?.main_balance ?? null;

    /* Is auction active */
    const isActive = (status ?? '').toUpperCase() === 'ACTIVE';
    const isScheduled = (status ?? '').toUpperCase() === 'SCHEDULED';

    /* Short title for breadcrumb */
    const shortTitle = title?.length > 40 ? title.slice(0, 40) + '…' : (title ?? 'Auction');

    /* ── Render ── */
    return (
        <div className="adp">
            <div className="container" style={{ maxWidth: 1100 }}>

                {/* ── Breadcrumb ── */}
                <nav className="adp__breadcrumb" aria-label="Breadcrumb">
                    <Link to="/">Home</Link>
                    <span className="adp__breadcrumb-sep">›</span>
                    <Link to="/auctions">Auctions</Link>
                    <span className="adp__breadcrumb-sep">›</span>
                    <span className="adp__breadcrumb-current">{shortTitle}</span>
                </nav>

                {/* ── Page title row ── */}
                <div style={{ marginBottom: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <h1 style={{ fontSize: 'clamp(1.25rem, 3vw, 1.75rem)', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.03em', margin: '0 0 0.4rem' }}>
                                {title}
                            </h1>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                                <StatusBadge status={status} />
                                {categoryName && (
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8125rem', color: 'var(--text-muted)', fontWeight: 500 }}>
                                        <FiTag size={12} /> {categoryName}
                                    </div>
                                )}
                            </div>
                        </div>
                        {/* Share button */}
                        <button
                            id="share-auction-btn"
                            className="adp__share-btn"
                            onClick={handleShare}
                            title="Copy link to clipboard"
                        >
                            <FiShare2 size={14} /> Share
                        </button>
                    </div>
                </div>

                {/* ══════════════ TWO-COLUMN GRID ══════════════ */}
                <div className="adp__grid">

                    {/* ══════════ LEFT COLUMN ══════════ */}
                    <div>

                        {/* ── Image Gallery ── */}
                        <div className="adp__card" id="auction-image-gallery">
                            <ImageGallery images={images} title={title} />
                        </div>

                        {/* ── Item Details ── */}
                        <div className="adp__card" id="auction-item-details">
                            <div className="adp__card-header">
                                <FiPackage size={14} /> Item Details
                            </div>
                            <div className="adp__card-body">

                                {/* Description */}
                                {description ? (
                                    <div style={{ marginBottom: '1rem' }}>
                                        <div
                                            className={`adp__description ${!descExpanded && longDescription ? 'adp__description--clamped' : ''}`}
                                        >
                                            {description}
                                        </div>
                                        {longDescription && (
                                            <button
                                                className="adp__read-more"
                                                onClick={() => setDescExpanded((p) => !p)}
                                                aria-expanded={descExpanded}
                                            >
                                                {descExpanded
                                                    ? <><FiChevronUp size={13} /> Show less</>
                                                    : <><FiChevronDown size={13} /> Show more</>}
                                            </button>
                                        )}
                                    </div>
                                ) : null}

                                {/* Spec rows */}
                                <div>
                                    {/* Condition */}
                                    <div className="adp__detail-row">
                                        <span className="adp__detail-label">Condition</span>
                                        <span className="adp__detail-value">
                                            <span
                                                className="adp__condition-badge"
                                                style={{ background: condStyle.bg, color: condStyle.color }}
                                            >
                                                {condStyle.label}
                                            </span>
                                        </span>
                                    </div>

                                    {/* Category */}
                                    {categoryName && (
                                        <div className="adp__detail-row">
                                            <span className="adp__detail-label">Category</span>
                                            <span className="adp__detail-value" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                <FiTag size={12} style={{ color: 'var(--primary)' }} />
                                                {categoryName}
                                            </span>
                                        </div>
                                    )}

                                    {/* Weight */}
                                    {item?.weight_kg != null && (
                                        <div className="adp__detail-row">
                                            <span className="adp__detail-label">Weight</span>
                                            <span className="adp__detail-value">{item.weight_kg} kg</span>
                                        </div>
                                    )}

                                    {/* Dimensions */}
                                    {item?.dimensions != null && (
                                        <div className="adp__detail-row">
                                            <span className="adp__detail-label">Dimensions</span>
                                            <span className="adp__detail-value">{item.dimensions}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* ── Seller info ── */}
                            {sellerName && (
                                <>
                                    <div style={{ borderTop: '1px solid var(--border)', padding: '0.75rem 1.25rem', fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>
                                        Listed by
                                    </div>
                                    <div className="adp__seller">
                                        <div className="adp__seller-avatar">{sellerInitial}</div>
                                        <div style={{ flex: 1 }}>
                                            <div className="adp__seller-name">
                                                {sellerName}
                                                {isVerified && (
                                                    <FiCheckCircle
                                                        size={14}
                                                        style={{ color: 'var(--primary)' }}
                                                        title="Verified seller"
                                                    />
                                                )}
                                            </div>
                                            <div className="adp__seller-meta">
                                                {memberYear && `Member since ${memberYear}`}
                                                {memberYear && totalSales !== null && ' · '}
                                                {totalSales !== null && `${totalSales} sales`}
                                            </div>
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    {/* ══════════ RIGHT COLUMN ══════════ */}
                    <div>

                        {/* ── Countdown + Bid card ── */}
                        <div className="adp__card" id="auction-bid-panel">
                            {/* Countdown */}
                            {!isScheduled && ends_at && <CountdownTimer endTime={ends_at} />}

                            {/* Current bid */}
                            <div className="adp__bid-card">
                                <div className="adp__bid-header">
                                    <span className="adp__bid-label">
                                        {hasBids ? 'Current Bid' : 'Starting Bid'}
                                    </span>
                                    {reserve_price_met === false && (
                                        <span className="adp__reserve adp__reserve--not-met">
                                            <FiAlertCircle size={11} /> Reserve Not Met
                                        </span>
                                    )}
                                    {reserve_price_met === true && (
                                        <span className="adp__reserve adp__reserve--met">
                                            <FiCheckCircle size={11} /> Reserve Met
                                        </span>
                                    )}
                                </div>

                                {hasBids ? (
                                    <div className="adp__bid-amount">{formatNaira(currentBidAmount)}</div>
                                ) : (
                                    <>
                                        <div className="adp__bid-amount">{formatNaira(starting_price)}</div>
                                        <div className="adp__bid-no-bids">
                                            No bids yet — starting at {formatNaira(starting_price)}
                                        </div>
                                    </>
                                )}

                                <div className="adp__bid-meta">
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <div className="adp__bid-meta-item">
                                            <FiTrendingUp size={14} style={{ color: 'var(--primary)' }} />
                                            <span><strong>{liveBidCount}</strong> {liveBidCount === 1 ? 'bid' : 'bids'}</span>
                                        </div>
                                        {dataUpdatedAt ? (
                                            <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                                Updated {timeAgo(new Date(dataUpdatedAt).toISOString())}
                                            </div>
                                        ) : null}
                                    </div>
                                    <div className="adp__bid-meta-item">
                                        <FiEye size={14} />
                                        <span>0 watching</span>
                                    </div>
                                    {ends_at && (
                                        <div className="adp__bid-meta-item" style={{ marginLeft: 'auto' }}>
                                            <FiClock size={14} />
                                            <StatusBadge status={status} />
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* ── Reserve Price Progress Bar ── */}
                            {reserve_progress_percent !== null && reserve_progress_percent !== undefined && (
                                <div style={{
                                    margin: '0.75rem 1.25rem',
                                    padding: '0.875rem 1rem',
                                    borderRadius: 'var(--radius)',
                                    background: 'var(--surface)',
                                    border: '1px solid var(--border)',
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
                                            Reserve Price
                                        </span>
                                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', fontWeight: 700, color: reserve_price_met ? 'var(--success)' : 'var(--warning)' }}>
                                            {reserve_price_met
                                                ? <><FiCheckCircle size={12} /> Met</>
                                                : <><FiAlertCircle size={12} /> Not Met</>
                                            }
                                        </span>
                                    </div>
                                    <div style={{ height: 8, background: 'var(--border)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                                        <div style={{
                                            height: '100%',
                                            width: `${reserve_progress_percent}%`,
                                            background: reserve_price_met ? 'var(--success)' : 'var(--warning)',
                                            borderRadius: 'var(--radius-full)',
                                            transition: 'width 0.6s ease',
                                        }} />
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.375rem', fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                                        <span>{reserve_progress_percent}% of reserve reached</span>
                                        {!reserve_price_met && (
                                            <span style={{ color: 'var(--text-muted)', fontSize: '0.6875rem' }}>
                                                Item only sells if reserve is met
                                            </span>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* ── Place bid section ── */}
                            {isScheduled ? (
                                <div style={{
                                    padding: '1rem',
                                    borderRadius: 'var(--radius)',
                                    background: 'var(--primary-50)',
                                    border: '1px solid var(--primary-light)',
                                    fontSize: '0.8125rem',
                                    color: 'var(--primary)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                }}>
                                    <FiClock size={14} />
                                    <span>
                                        Bidding opens at{' '}
                                        <strong>{starts_at ? new Date(starts_at).toLocaleString('en-NG') : '—'}</strong>
                                    </span>
                                </div>
                            ) : isActive && (
                                isAuthenticated ? (
                                    <div className="adp__place-bid" id="place-bid-section">
                                        <div className="adp__place-bid-title">Place Your Bid</div>

                                        {/* Seller cannot bid on their own auction */}
                                        {user?.id === seller?.id ? (
                                            <div style={{
                                                padding: '0.75rem 1rem',
                                                borderRadius: 'var(--radius)',
                                                background: 'var(--warning-50, #fffbeb)',
                                                border: '1px solid var(--warning, #d97706)',
                                                fontSize: '0.8125rem',
                                                color: 'var(--warning, #d97706)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                            }}>
                                                <FiAlertCircle size={14} />
                                                You listed this auction and cannot place a bid on it.
                                            </div>
                                        ) : userCurrentBid?.status === 'WINNING' ? (
                                            /* Already highest bidder — no point showing the form */
                                            <div style={{
                                                padding: '0.75rem 1rem',
                                                borderRadius: 'var(--radius)',
                                                background: 'var(--primary-50)',
                                                border: '1px solid var(--primary-light)',
                                                fontSize: '0.8125rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                color: 'var(--primary)',
                                            }}>
                                                <FiCheckCircle size={14} />
                                                You are currently the highest bidder at {formatNaira(userCurrentBid.amount)}. You're winning!
                                            </div>
                                        ) : (
                                            <>
                                        {/* User's current bid indicator */}
                                        {userCurrentBid && (
                                            <div style={{
                                                padding: '0.625rem 0.875rem',
                                                borderRadius: 'var(--radius)',
                                                marginBottom: '0.75rem',
                                                background: userCurrentBid.status === 'OUTBID' ? 'var(--warning-50, #fffbeb)' : 'var(--primary-50)',
                                                border: `1px solid ${userCurrentBid.status === 'OUTBID' ? 'var(--warning, #d97706)' : 'var(--primary-light)'}`,
                                                fontSize: '0.8125rem',
                                            }}>
                                                {userCurrentBid.status === 'OUTBID'
                                                    ? <><FiAlertCircle size={13} style={{ color: 'var(--warning, #d97706)' }} /> You have been outbid. Place a higher bid.</>
                                                    : <><FiCheckCircle size={13} style={{ color: 'var(--primary)' }} /> Your current bid: {formatNaira(userCurrentBid.amount)}</>
                                                }
                                            </div>
                                        )}

                                        {/* Wallet balance */}
                                        <div className="adp__wallet-row">
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                                <FiCreditCard size={13} /> Available Balance
                                            </span>
                                            <span className="adp__wallet-balance" style={{ color: walletBalance !== null && walletBalance < minBid ? 'var(--danger)' : undefined }}>
                                                {walletBalance !== null ? formatNaira(walletBalance) : '—'}
                                                {walletBalance !== null && walletBalance < minBid && (
                                                    <Link to="/wallet" style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--primary)' }}>Fund Wallet</Link>
                                                )}
                                            </span>
                                        </div>

                                        {/* Min bid helper */}
                                        <div className="adp__min-bid">
                                            Minimum bid: <strong>{formatNaira(minBid)}</strong>
                                        </div>

                                        {/* Bid input */}
                                        <div className="adp__bid-input-wrapper">
                                            <span className="adp__bid-prefix">₦</span>
                                            <input
                                                id="bid-amount-input"
                                                type="number"
                                                className="adp__bid-input"
                                                placeholder={String(minBid)}
                                                min={minBid}
                                                step={bid_increment || 1}
                                                value={bidAmount}
                                                onChange={(e) => { setBidAmount(e.target.value); setBidError(''); }}
                                                aria-label="Bid amount in Naira"
                                            />
                                        </div>

                                        {/* Inline error */}
                                        {bidError && (
                                            <div style={{ fontSize: '0.8125rem', color: 'var(--danger)', marginTop: '0.375rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                <FiAlertCircle size={13} />
                                                {bidError}
                                                {typeof bidError === 'string' && bidError.includes('Fund your wallet') && (
                                                    <Link to="/wallet" style={{ marginLeft: '0.25rem', fontWeight: 600 }}>Fund Wallet</Link>
                                                )}
                                            </div>
                                        )}

                                        {/* Place bid button */}
                                        <button
                                            id="place-bid-btn"
                                            className="adp__bid-btn"
                                            disabled={
                                                placeBidMutation.isPending ||
                                                !bidAmount ||
                                                Number(bidAmount) < minBid ||
                                                (walletBalance !== null && walletBalance < Number(bidAmount))
                                            }
                                            onClick={() => placeBidMutation.mutate(Number(bidAmount))}
                                            style={{ marginTop: '0.75rem' }}
                                        >
                                            {placeBidMutation.isPending ? 'Placing Bid…' : bidSuccess ? 'Bid Placed! ✓' : 'Place Bid'}
                                        </button>
                                            </>
                                        )}
                                    </div>
                                ) : (
                                    <div className="adp__login-prompt" id="login-to-bid">
                                        <p>You must be logged in to place a bid on this auction.</p>
                                        <button className="btn btn-primary w-100" onClick={() => navigate('/login')} id="login-to-bid-btn">
                                            Login to Place a Bid
                                        </button>
                                    </div>
                                )
                            )}

                        </div>

                        {/* ── Bid History ── */}
                        <div className="adp__card" id="auction-bid-history" ref={bidHistoryRef}>
                            <div className="adp__card-header">
                                <FiTrendingUp size={14} /> Bid History
                                {liveBidCount > 0 && (
                                    <span style={{ marginLeft: 'auto', fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary)' }}>
                                        {liveBidCount} total
                                    </span>
                                )}
                            </div>
                            <div className="adp__card-body" style={{ padding: liveBidCount > 0 ? '0 1.25rem' : undefined }}>
                                <BidHistorySection bids={liveBids} userBidId={userCurrentBid?.id} />
                            </div>
                        </div>

                    </div>
                    {/* end right column */}
                </div>
                {/* end grid */}
            </div>
        </div>
    );
}
