import { useState, useEffect } from "react";
import { useForm } from 'react-hook-form';
import apiClient from "../../api/client";
import { useToast } from "../../components/common/Toast";
import BankDetailsSection from "../../components/profile/BankDetailsSection";
import {
    FiUser, FiMail, FiPhone, FiMapPin, FiCalendar,
    FiStar, FiShoppingCart, FiShoppingBag, FiEdit2,
    FiSave, FiX, FiCheckCircle, FiClock, FiXCircle,
} from 'react-icons/fi';

const formatNaira = (n) => parseFloat(n || 0).toLocaleString('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0 });

export default function MyProfilePage() {
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(false);
    const { showToast } = useToast();
    const { register, handleSubmit, reset } = useForm();

    useEffect(() => { fetchProfile(); }, []);

    const fetchProfile = async () => {
        try {
            const response = await apiClient.get('/users/me');
            setProfile(response.data);
            reset({
                first_name: response.data.first_name,
                last_name: response.data.last_name,
                bio: response.data.profile?.bio || '',
                city: response.data.profile?.city || '',
                state: response.data.profile?.state || '',
                phone_number: response.data.phone_number || '',
            });
        } catch (error) {
            console.error("Failed to fetch profile:", error);
        } finally {
            setLoading(false);
        }
    };

    const onSubmit = async (data) => {
        try {
            await apiClient.patch('/users/me', data);
            await fetchProfile();
            setEditing(false);
            showToast('Profile updated successfully!', 'success');
        } catch (error) {
            showToast('Failed to update profile', 'error');
        }
    };

    if (loading) {
        return (
            <div className="page-container" style={{ maxWidth: 800 }}>
                <div className="card" style={{ borderRadius: 'var(--radius-xl)' }}>
                    <div className="card-body p-4">
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="skeleton mb-3" style={{ height: 16, width: `${70 - i * 8}%` }} />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (!profile) return (
        <div className="page-container text-center" style={{ maxWidth: 600 }}>
            <FiUser size={40} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} />
            <h4 style={{ fontWeight: 700 }}>Profile not found</h4>
        </div>
    );

    const initials = `${(profile.first_name?.[0] || '').toUpperCase()}${(profile.last_name?.[0] || '').toUpperCase()}`;

    return (
        <div className="page-container" style={{ maxWidth: 800 }}>
            {/* Header */}
            <div className="d-flex align-items-center justify-content-between mb-4">
                <h1 style={{ fontWeight: 800, fontSize: '1.75rem', margin: 0 }}>My Profile</h1>
                {!editing && (
                    <button className="btn btn-primary btn-sm" onClick={() => setEditing(true)}>
                        <FiEdit2 size={14} /> Edit Profile
                    </button>
                )}
            </div>

            {/* Profile Card */}
            <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
                {/* Avatar Banner */}
                <div style={{ background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)', padding: '2rem 1.5rem 1rem', display: 'flex', alignItems: 'flex-end', gap: '1rem' }}>
                    <div style={{
                        width: 72, height: 72, borderRadius: 'var(--radius-full)',
                        background: '#fff', color: 'var(--primary)', display: 'flex',
                        alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem',
                        fontWeight: 800, border: '3px solid rgba(255,255,255,0.3)', flexShrink: 0,
                    }}>
                        {initials}
                    </div>
                    <div style={{ color: '#fff', paddingBottom: '0.5rem' }}>
                        <h3 style={{ fontWeight: 700, fontSize: '1.25rem', margin: 0 }}>
                            {profile.first_name} {profile.last_name}
                        </h3>
                        <div style={{ opacity: 0.8, fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <FiMail size={12} /> {profile.email}
                        </div>
                    </div>
                </div>

                <div className="card-body p-4">
                    {!editing ? (
                        <>
                            <div className="row g-4">
                                {[
                                    { icon: <FiPhone size={15} />, label: 'Phone', value: profile.phone_number || 'Not provided' },
                                    { icon: <FiMapPin size={15} />, label: 'Location', value: profile.profile?.city && profile.profile?.state ? `${profile.profile.city}, ${profile.profile.state}` : 'Not provided' },
                                    { icon: <FiCalendar size={15} />, label: 'Member Since', value: new Date(profile.created_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' }) },
                                    { icon: <FiStar size={15} />, label: 'Rating', value: profile.profile?.rating ? `${parseFloat(profile.profile.rating).toFixed(1)} / 5.0` : 'No ratings yet' },
                                ].map((item, i) => (
                                    <div className="col-md-6" key={i}>
                                        <div className="d-flex align-items-center gap-2" style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>
                                            {item.icon} {item.label}
                                        </div>
                                        <div style={{ fontWeight: 600, fontSize: '0.9375rem' }}>{item.value}</div>
                                    </div>
                                ))}
                            </div>

                            {profile.profile?.bio && (
                                <div className="mt-4 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Bio</div>
                                    <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{profile.profile.bio}</p>
                                </div>
                            )}

                            {/* Stats Row */}
                            <div className="row g-3 mt-3 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
                                <div className="col-6">
                                    <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', padding: '1rem', textAlign: 'center' }}>
                                        <FiShoppingBag size={18} style={{ color: 'var(--success)', marginBottom: '0.25rem' }} />
                                        <div style={{ fontWeight: 800, fontSize: '1.25rem' }}>{profile.profile?.total_sales || 0}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Sales</div>
                                    </div>
                                </div>
                                <div className="col-6">
                                    <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', padding: '1rem', textAlign: 'center' }}>
                                        <FiShoppingCart size={18} style={{ color: 'var(--primary)', marginBottom: '0.25rem' }} />
                                        <div style={{ fontWeight: 800, fontSize: '1.25rem' }}>{profile.profile?.total_purchases || 0}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Purchases</div>
                                    </div>
                                </div>
                            </div>

                            {/* Seller Status */}
                            {profile.seller_profile ? (
                                <div className="mt-4 p-3" style={{
                                    borderRadius: 'var(--radius)',
                                    background: profile.seller_profile.is_verified ? 'var(--success-light)' : 'var(--warning-light)',
                                    display: 'flex', alignItems: 'center', gap: '0.75rem',
                                }}>
                                    {profile.seller_profile.is_verified ? <FiCheckCircle size={20} style={{ color: 'var(--success)' }} /> : <FiClock size={20} style={{ color: 'var(--warning)' }} />}
                                    <div>
                                        <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                                            {profile.seller_profile.is_verified ? 'Verified Seller' : profile.seller_profile.verified_by_id ? 'Verification Failed' : 'Pending Verification'}
                                        </div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                            {profile.seller_profile.is_verified ? 'You can list items for auction' : 'Your seller application is being reviewed'}
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="mt-4 text-center">
                                    <a href="/become-seller" className="btn btn-outline-primary btn-sm">
                                        <FiShoppingBag size={14} /> Become a Seller
                                    </a>
                                </div>
                            )}
                        </>
                    ) : (
                        <form onSubmit={handleSubmit(onSubmit)}>
                            <div className="row g-3">
                                <div className="col-md-6">
                                    <label className="form-label">First Name</label>
                                    <input {...register('first_name')} className="form-control" />
                                </div>
                                <div className="col-md-6">
                                    <label className="form-label">Last Name</label>
                                    <input {...register('last_name')} className="form-control" />
                                </div>
                                <div className="col-12">
                                    <label className="form-label">Phone Number</label>
                                    <input {...register('phone_number')} className="form-control" />
                                </div>
                                <div className="col-md-6">
                                    <label className="form-label">City</label>
                                    <input {...register('city')} className="form-control" />
                                </div>
                                <div className="col-md-6">
                                    <label className="form-label">State</label>
                                    <input {...register('state')} className="form-control" />
                                </div>
                                <div className="col-12">
                                    <label className="form-label">Bio</label>
                                    <textarea {...register('bio')} className="form-control" rows="3" maxLength="500" />
                                </div>
                                <div className="col-12 pt-2 d-flex gap-2">
                                    <button type="submit" className="btn btn-primary">
                                        <FiSave size={14} /> Save Changes
                                    </button>
                                    <button type="button" className="btn btn-light" onClick={() => setEditing(false)}>
                                        <FiX size={14} /> Cancel
                                    </button>
                                </div>
                            </div>
                        </form>
                    )}
                </div>
            </div>

            {/* Bank Details */}
            <BankDetailsSection profile={profile} onUpdate={fetchProfile} />
        </div>
    );
}
