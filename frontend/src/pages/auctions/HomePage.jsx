/**
 * HomePage.jsx — Public Auction Browse / Home Page
 *
 * Features:
 *  - Hero section with CSS-animated mock auction card
 *  - Sticky horizontal category pill filter strip
 *  - Sortable, paginated auction grid (Load More style)
 *  - Loading skeletons, empty state, React Query 30s refetch
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
    FiSearch, FiShoppingBag, FiPackage, FiZap,
    FiArrowRight, FiRefreshCw, FiChevronDown,
} from 'react-icons/fi';

import { getAuctions, getCategories } from '../../api/auctions';
import { useAuthStore } from '../../store/authStore';
import AuctionCard from '../../components/auctions/AuctionCard';
import './HomePage.css';

/* ─── Constants ────────────────────────────────────────────────────────────── */

const SORT_OPTIONS = [
    { value: 'ending_soon', label: 'Ending Soon' },
    { value: 'newest',      label: 'Newest First' },
    { value: 'most_bids',   label: 'Most Bids' },
    { value: 'lowest_price', label: 'Lowest Price' },
];

const PAGE_SIZE = 12;

/* ─── Skeleton Card ────────────────────────────────────────────────────────── */

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

/* ─── Hero Mock Card ───────────────────────────────────────────────────────── */

function HeroMockCard() {
    return (
        <div className="home-hero__mock-card" aria-hidden="true">
            <div className="home-hero__mock-img" />
            <div className="home-hero__mock-line" />
            <div className="home-hero__mock-line home-hero__mock-line--short" />
            <div className="home-hero__mock-price">₦285,000</div>
            <div className="home-hero__mock-badge">
                <FiZap size={9} /> 14 bids
            </div>
        </div>
    );
}

/* ─── Main Component ───────────────────────────────────────────────────────── */

export default function HomePage() {
    const navigate = useNavigate();
    const { user, isAuthenticated } = useAuthStore();
    const auctionGridRef = useRef(null);

    const [selectedCategory, setSelectedCategory] = useState(null); // null = All
    const [sortBy, setSortBy] = useState('ending_soon');
    const [view, setView] = useState('active'); // 'active' | 'scheduled' | 'all'
    const [page, setPage] = useState(1);
    const [allAuctions, setAllAuctions] = useState([]);

    /* ── Categories query ─────────────────────────────────────────────────── */
    const { data: categoriesData } = useQuery({
        queryKey: ['categories'],
        queryFn: getCategories,
        staleTime: 5 * 60 * 1000,
    });

    const categories = Array.isArray(categoriesData)
        ? categoriesData
        : (categoriesData?.data ?? []);

    /* ── Auctions query ───────────────────────────────────────────────────── */
    const {
        data: auctionPage,
        isLoading,
        isFetching,
        isError,
        refetch,
    } = useQuery({
        queryKey: ['auctions', { category_id: selectedCategory, sort_by: sortBy, view, page }],
        queryFn: () => getAuctions({
            category_id: selectedCategory,
            sort_by: sortBy,
            view,
            page,
            limit: PAGE_SIZE,
        }),
        refetchInterval: 30_000,
        placeholderData: (prev) => prev, // replaces keepPreviousData in RQ v5
    });

    // Backend returns { data: [...], total, page, pages, limit }
    const pageItems = auctionPage?.data ?? [];
    const totalPages = auctionPage?.pages ?? auctionPage?.total_pages ?? 1;
    const hasMore = page < totalPages;

    // Accumulate pages for "Load More" — sync allAuctions when pageItems changes
    useEffect(() => {
        if (pageItems.length === 0 && page === 1) {
            setAllAuctions([]);
            return;
        }
        if (page === 1) {
            setAllAuctions(pageItems);
        } else {
            setAllAuctions((prev) => {
                const existingIds = new Set(prev.map((a) => a.id));
                const fresh = pageItems.filter((a) => !existingIds.has(a.id));
                return [...prev, ...fresh];
            });
        }
    }, [pageItems, page]);

    const currentItems = allAuctions;

    /* ── Handlers ─────────────────────────────────────────────────────────── */

    const handleCategorySelect = useCallback((catId) => {
        setSelectedCategory(catId);
        setPage(1);
        setAllAuctions([]);
    }, []);

    const handleSortChange = useCallback((e) => {
        setSortBy(e.target.value);
        setPage(1);
        setAllAuctions([]);
    }, []);

    const handleViewChange = useCallback((newView) => {
        setView(newView);
        setPage(1);
        setAllAuctions([]);
    }, []);

    const handleLoadMore = useCallback(() => {
        setPage((p) => p + 1);
    }, []);

    const handleClearFilters = useCallback(() => {
        setSelectedCategory(null);
        setSortBy('ending_soon');
        setView('active');
        setPage(1);
        setAllAuctions([]);
    }, []);

    const scrollToGrid = () => {
        auctionGridRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    /** Smart routing for "Start Selling" based on seller status */
    const handleStartSelling = useCallback(() => {
        if (!isAuthenticated)                           { navigate('/login');            return; }
        if (!user?.seller_profile)                      { navigate('/become-seller');    return; }
        if (!user.seller_profile.is_verified)           { navigate('/seller/pending');   return; }
        navigate('/seller/dashboard');
    }, [isAuthenticated, user, navigate]);

    /* ── Render ───────────────────────────────────────────────────────────── */

    const showSkeleton = isLoading && currentItems.length === 0;
    const showEmpty = !isLoading && !isError && currentItems.length === 0;

    return (
        <>
            {/* ══════════════ HERO ══════════════ */}
            <section className="home-hero">
                <div className="container">
                    <div className="home-hero__content">
                        <div className="home-hero__eyebrow">
                            <FiZap size={11} />
                            Nigeria&apos;s Premier Live Auction Marketplace
                        </div>
                        <h1 className="home-hero__headline">
                            Discover.<br />
                            <span>Bid. Win.</span>
                        </h1>
                        <p className="home-hero__subline">
                            Thousands of unique items up for auction every day.
                            Place your bids, win at unbeatable prices, and sell with zero hassle.
                        </p>
                        <div className="home-hero__actions">
                            <button
                                className="home-hero__btn-primary"
                                onClick={scrollToGrid}
                                id="hero-browse-btn"
                            >
                                <FiSearch size={16} />
                                Browse Auctions
                            </button>
                            <button
                                className="home-hero__btn-ghost"
                                id="hero-sell-btn"
                                onClick={handleStartSelling}
                            >
                                <FiShoppingBag size={16} />
                                Start Selling
                            </button>
                        </div>
                    </div>
                </div>
                <HeroMockCard />
            </section>

            {/* ══════════════ STATS BAR ══════════════ */}
            <section className="home-stats">
                <div className="container">
                    <div className="row text-center g-0">
                        {[
                            { value: '2,450+', label: 'Active Auctions' },
                            { value: '18,000+', label: 'Items Sold' },
                            { value: '45,000+', label: 'Registered Users' },
                        ].map((stat, i) => (
                            <div className="col-4" key={i}>
                                <div className="home-stats__item">
                                    <div className="home-stats__value">{stat.value}</div>
                                    <div className="home-stats__label">{stat.label}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════════ CATEGORY PILLS ══════════════ */}
            <nav className="home-categories" aria-label="Filter by category">
                <div className="home-categories__scroll">
                    {/* "All" pill */}
                    <button
                        id="category-pill-all"
                        className={`home-category-pill ${selectedCategory === null ? 'home-category-pill--active' : ''}`}
                        onClick={() => handleCategorySelect(null)}
                    >
                        All
                    </button>

                    {categories.map((cat) => (
                        <button
                            key={cat.id}
                            id={`category-pill-${cat.id}`}
                            className={`home-category-pill ${selectedCategory === cat.id ? 'home-category-pill--active' : ''}`}
                            onClick={() => handleCategorySelect(cat.id)}
                        >
                            {cat.name}
                        </button>
                    ))}
                </div>
            </nav>

            {/* ══════════════ VIEW FILTER PILLS ══════════════ */}
            <div className="home-view-filter">
                <div className="container">
                    <div className="home-view-pills">
                        {[
                            { value: 'active',    label: 'Live Now' },
                            { value: 'scheduled', label: 'Coming Soon' },
                            { value: 'all',       label: 'All' },
                        ].map(({ value, label }) => (
                            <button
                                key={value}
                                className={`home-view-pill ${view === value ? 'home-view-pill--active' : ''}`}
                                onClick={() => handleViewChange(value)}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* ══════════════ AUCTION GRID ══════════════ */}
            <section className="home-auctions" ref={auctionGridRef} id="auction-grid">
                <div className="container">

                    {/* Header row: title + sort */}
                    <div className="home-auctions__header">
                        <h2 className="home-auctions__title">
                            {selectedCategory
                                ? `${categories.find((c) => c.id === selectedCategory)?.name ?? ''} Auctions`
                                : view === 'scheduled' ? 'Coming Soon'
                                : view === 'all' ? 'All Auctions'
                                : 'Live Auctions'}
                            {!isLoading && auctionPage?.total != null && (
                                <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                                    ({auctionPage.total.toLocaleString()})
                                </span>
                            )}
                        </h2>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            {/* Refetch indicator */}
                            {isFetching && !isLoading && (
                                <FiRefreshCw size={14} style={{ color: 'var(--text-muted)', animation: 'spin 0.8s linear infinite' }} />
                            )}

                            <div style={{ position: 'relative' }}>
                                <select
                                    id="auction-sort-select"
                                    className="form-select home-sort-select"
                                    value={sortBy}
                                    onChange={handleSortChange}
                                    aria-label="Sort auctions"
                                >
                                    {SORT_OPTIONS.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* ── Loading skeletons ── */}
                    {showSkeleton && (
                        <div className="row g-3">
                            {Array.from({ length: PAGE_SIZE }).map((_, i) => (
                                <div key={i} className="col-12 col-sm-6 col-md-4 col-xl-3">
                                    <SkeletonCard />
                                </div>
                            ))}
                        </div>
                    )}

                    {/* ── Error ── */}
                    {isError && (
                        <div className="home-empty">
                            <div className="home-empty__icon">
                                <FiPackage size={28} />
                            </div>
                            <div className="home-empty__title">Failed to load auctions</div>
                            <p className="home-empty__sub">Something went wrong. Please try again.</p>
                            <button className="btn btn-primary" onClick={() => refetch()}>
                                <FiRefreshCw size={14} /> Retry
                            </button>
                        </div>
                    )}

                    {/* ── Empty state ── */}
                    {showEmpty && (
                        <div className="home-empty" id="auction-empty-state">
                            <div className="home-empty__icon">
                                <FiPackage size={28} />
                            </div>
                            <div className="home-empty__title">No auctions found</div>
                            <p className="home-empty__sub">
                                {view === 'scheduled'
                                    ? 'No upcoming auctions scheduled right now.'
                                    : view === 'all'
                                    ? 'No auctions found matching your filters.'
                                    : 'There are no live auctions matching your filters right now.'}
                            </p>
                            <button
                                id="clear-filters-btn"
                                className="btn btn-outline-primary"
                                onClick={handleClearFilters}
                            >
                                Clear Filters
                            </button>
                        </div>
                    )}

                    {/* ── Auction grid ── */}
                    {!showSkeleton && !isError && currentItems.length > 0 && (
                        <div className="row g-3">
                            {currentItems.map((auction) => (
                                <div key={auction.id} className="col-12 col-sm-6 col-md-4 col-xl-3">
                                    <AuctionCard auction={auction} />
                                </div>
                            ))}

                            {/* Inline skeleton rows while loading next page */}
                            {isFetching && page > 1 && (
                                Array.from({ length: 4 }).map((_, i) => (
                                    <div key={`sk-${i}`} className="col-12 col-sm-6 col-md-4 col-xl-3">
                                        <SkeletonCard />
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {/* ── Load More ── */}
                    {!isError && !showSkeleton && hasMore && currentItems.length > 0 && (
                        <div className="home-load-more">
                            <button
                                id="load-more-btn"
                                className="home-load-more__btn"
                                onClick={handleLoadMore}
                                disabled={isFetching}
                            >
                                {isFetching
                                    ? <><span className="spinner-sm" style={{ borderTopColor: 'var(--primary)', borderColor: 'var(--primary-light)' }} /> Loading...</>
                                    : <><FiArrowRight size={16} /> Load More Auctions</>
                                }
                            </button>
                        </div>
                    )}
                </div>
            </section>
        </>
    );
}
