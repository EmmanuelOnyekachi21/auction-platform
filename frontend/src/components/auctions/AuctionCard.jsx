/**
 * AuctionCard.jsx — Reusable auction listing card
 *
 * Displays item image, condition badge, name, category, current bid,
 * bid count, time remaining, and a "Bid Now" / "Auction Ended" CTA.
 */

import { useNavigate } from 'react-router-dom';
import { FiPackage, FiTag, FiUsers, FiClock } from 'react-icons/fi';
import './AuctionCard.css';

/* ─── Helpers ──────────────────────────────────────────────────────────────── */

const CONDITION_STYLES = {
    new:      { label: 'New',       bg: '#16A34A', color: '#fff' },
    like_new: { label: 'Like New',  bg: '#0D9488', color: '#fff' },
    good:     { label: 'Good',      bg: '#2563EB', color: '#fff' },
    fair:     { label: 'Fair',      bg: '#D97706', color: '#fff' },
    poor:     { label: 'Poor',      bg: '#DC2626', color: '#fff' },
};

/**
 * Format a Naira amount with locale thousands separators.
 * @param {number} amount
 */
const formatNaira = (amount) =>
    `₦${Number(amount || 0).toLocaleString('en-NG', { minimumFractionDigits: 0 })}`;

/**
 * Derive a time-remaining string from an ISO end-date string.
 * Returns { text, isExpired, isUrgent }
 * @param {string} endDateStr
 */
const getTimeRemaining = (endDateStr) => {
    const now = Date.now();
    const end = new Date(endDateStr).getTime();
    const diff = end - now;

    if (diff <= 0) return { text: 'Ended', isExpired: true, isUrgent: false };

    const totalSeconds = Math.floor(diff / 1000);
    const days    = Math.floor(totalSeconds / 86400);
    const hours   = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const isUrgent = diff < 3600_000; // under 1 hour

    if (days > 0)      return { text: `${days}d ${hours}h`,   isExpired: false, isUrgent };
    if (hours > 0)     return { text: `${hours}h ${minutes}m`, isExpired: false, isUrgent };
    return { text: `${minutes}m ${seconds}s`, isExpired: false, isUrgent };
};

/* ─── Component ────────────────────────────────────────────────────────────── */

export default function AuctionCard({ auction }) {
    const navigate = useNavigate();

    if (!auction) return null;

    // API returns items as array of {item, starting_price, quantity}
    const firstAuctionItem = auction.items?.[0];
    const item = firstAuctionItem?.item ?? null;

    const {
        id,
        ends_at,
        bid_count = 0,
        highest_bid,
    } = auction;

    // Title: use auction title if set, otherwise fall back to item title
    const title = auction.title || item?.title || 'Untitled Auction';

    // Starting price from the first attached item
    const starting_price = firstAuctionItem?.starting_price ?? 0;

    // Current bid from highest_bid
    const current_bid = highest_bid?.amount ?? null;

    // Resolve image — use primary image or first in list
    const imageUrl =
        item?.images?.find((img) => img.is_primary)?.url ||
        item?.images?.[0]?.url ||
        null;

    // Bid info
    const hasBids = bid_count > 0;
    const displayAmount = current_bid ?? starting_price ?? 0;

    // Time — API returns ends_at
    const { text: timeText, isExpired, isUrgent } = getTimeRemaining(ends_at);

    // Category and condition from the first item
    const categoryName = item?.category?.name ?? null;
    const conditionKey = (item?.condition || 'good').toLowerCase().replace(/\s+/g, '_');
    const condStyle = CONDITION_STYLES[conditionKey] || CONDITION_STYLES.good;

    const handleBidNow = () => {
        if (!isExpired) navigate(`/auctions/${id}`);
    };

    return (
        <div className="auction-card" onClick={handleBidNow}>
            {/* ── Image ── */}
            <div className="auction-card__image-wrapper">
                {imageUrl ? (
                    <img className="auction-card__image" src={imageUrl} alt={title} />
                ) : (
                    <div className="auction-card__image-placeholder">
                        <FiPackage size={40} />
                    </div>
                )}

                {/* Condition badge */}
                <span
                    className="auction-card__condition"
                    style={{ background: condStyle.bg, color: condStyle.color }}
                >
                    {condStyle.label}
                </span>
            </div>

            {/* ── Body ── */}
            <div className="auction-card__body">
                {/* Title */}
                <h3 className="auction-card__title">{title}</h3>

                {/* Category */}
                {categoryName && (
                    <div className="auction-card__category">
                        <FiTag size={11} />
                        {categoryName}
                    </div>
                )}

                {/* Bid amount */}
                <div className="auction-card__bid-section">
                    <span className="auction-card__bid-label">
                        {hasBids ? 'Current Bid' : 'Starting Bid'}
                    </span>
                    <span className="auction-card__bid-amount">{formatNaira(displayAmount)}</span>
                </div>

                {/* Footer row */}
                <div className="auction-card__footer">
                    <div className="auction-card__meta">
                        <FiUsers size={13} />
                        <span>{bid_count} {bid_count === 1 ? 'bid' : 'bids'}</span>
                    </div>
                    <div
                        className="auction-card__meta"
                        style={{ color: isUrgent || isExpired ? 'var(--danger)' : undefined }}
                    >
                        <FiClock size={13} />
                        <span>{timeText}</span>
                    </div>
                </div>

                {/* CTA */}
                <button
                    className={`btn w-100 auction-card__cta ${isExpired ? 'auction-card__cta--ended' : 'btn-primary'}`}
                    onClick={(e) => { e.stopPropagation(); handleBidNow(); }}
                    disabled={isExpired}
                >
                    {isExpired ? 'Auction Ended' : 'Bid Now'}
                </button>
            </div>
        </div>
    );
}
