import { Link } from 'react-router-dom';
import {
    FiSearch, FiDollarSign, FiPackage, FiShield,
    FiCheckCircle, FiTrendingUp, FiCamera, FiClock,
    FiAward, FiArrowRight, FiLock,
} from 'react-icons/fi';
import './HowItWorksPage.css';

export default function HowItWorksPage() {
    const steps = [
        {
            num: '01',
            icon: <FiSearch size={32} />,
            title: 'Discover Items',
            desc: 'Browse hundreds of live auctions across electronics, fashion, collectibles and more.',
            color: 'var(--primary)'
        },
        {
            num: '02',
            icon: <FiLock size={32} />,
            title: 'Fund Your Wallet',
            desc: 'Top up your KaraKaja wallet securely via Paystack before you start bidding.',
            color: '#0D9488'
        },
        {
            num: '03',
            icon: <FiTrendingUp size={32} />,
            title: 'Place Your Bid',
            desc: 'Enter your bid amount. Your funds are reserved — not charged — until you win.',
            color: '#7C3AED'
        },
        {
            num: '04',
            icon: <FiAward size={32} />,
            title: 'Win the Auction',
            desc: 'Highest bidder when the timer hits zero wins. Outbid? Your funds are instantly released.',
            color: 'var(--warning)'
        },
        {
            num: '05',
            icon: <FiPackage size={32} />,
            title: 'Seller Ships',
            desc: 'The seller has 72 hours to ship your item. Funds stay in escrow until you confirm receipt.',
            color: '#DC2626'
        },
        {
            num: '06',
            icon: <FiCheckCircle size={32} />,
            title: 'Confirm & Done',
            desc: 'Confirm delivery to release payment to the seller. Dispute if anything is wrong.',
            color: 'var(--success)'
        }
    ];

    return (
        <div className="hiw">
            {/* Section 1 — Hero */}
            <section className="hiw__hero">
                <div className="container">
                    <h1 style={{ fontWeight: 800, fontSize: 'clamp(2rem, 5vw, 3rem)', letterSpacing: '-0.03em', marginBottom: '0.75rem' }}>
                        How KaraKaja Works
                    </h1>
                    <p style={{ fontSize: '1.0625rem', opacity: 0.85, margin: 0, lineHeight: 1.5 }}>
                        Nigeria&apos;s most trusted auction platform — transparent, secure, and built for everyone.
                    </p>
                </div>
            </section>

            {/* Section 2 — Comic Strip Steps */}
            <section className="hiw__section" style={{ background: 'var(--bg-color)' }}>
                <div className="container">
                    <div className="hiw__comic-strip">
                        {steps.map((step, idx) => (
                            <div key={idx} style={{ display: 'contents' }}>
                                <div className="hiw__comic-card">
                                    <div className="hiw__comic-card__step">{step.num}</div>
                                    <div className="hiw__comic-card__icon-wrap" style={{ background: `${step.color}15`, color: step.color }}>
                                        {step.icon}
                                    </div>
                                    <div className="hiw__comic-card__title">{step.title}</div>
                                    <div className="hiw__comic-card__desc">{step.desc}</div>
                                </div>
                                {idx < steps.length - 1 && (
                                    <div className="hiw__comic-arrow">
                                        <FiArrowRight size={20} />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Section 3 — Two-track section */}
            <section className="hiw__section">
                <div className="container">
                    <div className="hiw__tracks">
                        {/* Buyers Card */}
                        <div className="hiw__track-card">
                            <div className="hiw__track-header" style={{ background: 'var(--primary)', color: '#fff' }}>
                                For Buyers
                            </div>
                            <div style={{ padding: '1.5rem' }}>
                                <div className="hiw__track-item">
                                    <FiSearch size={18} color="var(--primary)" />
                                    <span>Browse live auctions anytime, anywhere</span>
                                </div>
                                <div className="hiw__track-item">
                                    <FiShield size={18} color="var(--primary)" />
                                    <span>Funds held in escrow until you confirm delivery</span>
                                </div>
                                <div className="hiw__track-item">
                                    <FiDollarSign size={18} color="var(--primary)" />
                                    <span>Only pay when you win — no upfront fees</span>
                                </div>
                                <div className="hiw__track-item">
                                    <FiClock size={18} color="var(--primary)" />
                                    <span>Real-time countdown timers on every auction</span>
                                </div>
                                <div className="hiw__track-item">
                                    <FiCheckCircle size={18} color="var(--primary)" />
                                    <span>Dispute resolution if something goes wrong</span>
                                </div>
                            </div>
                        </div>

                        {/* Sellers Card */}
                        <div className="hiw__track-card">
                            <div className="hiw__track-header" style={{ background: '#0D9488', color: '#fff' }}>
                                For Sellers
                            </div>
                            <div style={{ padding: '1.5rem' }}>
                                <div className="hiw__track-item">
                                    <FiCamera size={18} color="#0D9488" />
                                    <span>List items in minutes with photos</span>
                                </div>
                                <div className="hiw__track-item">
                                    <FiTrendingUp size={18} color="#0D9488" />
                                    <span>Competitive bidding drives up your sale price</span>
                                </div>
                                <div className="hiw__track-item">
                                    <FiLock size={18} color="#0D9488" />
                                    <span>Reserve price protects your minimum acceptable value</span>
                                </div>
                                <div className="hiw__track-item">
                                    <FiDollarSign size={18} color="#0D9488" />
                                    <span>5% commission only on successful sales</span>
                                </div>
                                <div className="hiw__track-item">
                                    <FiPackage size={18} color="#0D9488" />
                                    <span>72-hour shipping window after auction closes</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Section 4 — CTA banner */}
            <section className="hiw__section" style={{ paddingBottom: '4rem' }}>
                <div className="container">
                    <div className="hiw__cta">
                        <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--primary-dark)', marginBottom: '0.5rem' }}>
                            Ready to start?
                        </h2>
                        <p style={{ color: 'var(--primary)', marginBottom: '1.5rem' }}>
                            Join thousands of buyers and sellers on KaraKaja today.
                        </p>
                        <div className="d-flex justify-content-center gap-3 flex-wrap">
                            <Link to="/auctions" className="btn btn-primary" style={{ padding: '0.625rem 1.5rem', fontWeight: 600 }}>
                                Browse Auctions
                            </Link>
                            <Link to="/become-seller" className="btn btn-outline-primary" style={{ padding: '0.625rem 1.5rem', fontWeight: 600 }}>
                                Start Selling
                            </Link>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}
