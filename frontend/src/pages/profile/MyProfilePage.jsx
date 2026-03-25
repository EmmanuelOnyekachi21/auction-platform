import { useState, useEffect } from "react";
import { useForm } from 'react-hook-form';
import apiClient from "../../api/client"

export default function MyProfilePage() {
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(false);
    const { register, handleSubmit, reset } = useForm();

    useEffect(() => {
        fetchProfile();
    }, [])

    const fetchProfile = async () => {
        try {
            const response = await apiClient.get('/users/me');
            setProfile(response.data);
            // Pre-fill form with current values
            reset({
                first_name: response.data.first_name,
                last_name: response.data.last_name,
                bio: response.data.profile?.bio || '',
                city: response.data.profile?.city || '',
                state: response.data.profile?.state || '',
                profile_picture_url: response.data.profile?.profile_picture_url || ''
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
            alert('Profile updated successfully!');
        } catch (error) {
            console.error('Failed to update profile:', error);
            alert('Failed to update profile');
        }
    };

    if (loading) return <div className="container mt-5">Loading...</div>;
    if (!profile) return <div className="container mt-5">Profile not found</div>;

    return (
        <div className="container mt-5">
            <div className="row">
                <div className="col-md-8 mx-auto">
                    <div className="card">
                        <div className="card-header d-flex justify-content-between align-items-center">
                            <h3>My Profile</h3>
                            {
                                !editing && (
                                    <button className="btn btn-primary" onClick={() => setEditing(true)}>
                                        Edit Profile
                                    </button>
                                )
                            }
                        </div>
                        <div className="card-body">
                            {!editing ? (
                                <div>
                                    <p><strong>Name:</strong> {profile.first_name} {profile.last_name}</p>
                                    <p><strong>Email:</strong> {profile.email}</p>
                                    <p><strong>Phone:</strong> {profile.phone_number || 'Not provided'}</p>
                                    <p><strong>Bio:</strong> {profile.profile?.bio || 'No bio yet'}</p>
                                    <p><strong>City:</strong> {profile.profile?.city || 'Not provided'}</p>
                                    <p><strong>State:</strong> {profile.profile?.state || 'Not provided'}</p>
                                    <p><strong>Member Since:</strong> {new Date(profile.created_at).toLocaleDateString()}</p>
                                    <p><strong>Rating:</strong> {profile.profile?.rating || 'No ratings yet'}</p>
                                    <p><strong>Total Sales:</strong> {profile.profile?.total_sales || 0}</p>
                                    <p><strong>Total Purchases:</strong> {profile.profile?.total_purchases || 0}</p>

                                    {profile.seller_profile ? (
                                        <div className="mt-3">
                                            <strong>Seller Status:</strong>{' '}
                                            {profile.seller_profile.is_verified ? (
                                                <span className="badge bg-success">Verified ✓</span>
                                            ) : profile.seller_profile.verified_by_id ? (
                                                <span className="badge bg-danger">Verification Failed</span>
                                            ) : (
                                                <span className="badge bg-warning text-dark">Pending Verification</span>
                                            )}
                                        </div>
                                    ) : (
                                        <a href="/become-seller" className="btn btn-success mt-3">
                                            Become a Seller
                                        </a>
                                    )}
                                </div>
                            ) : (
                                <form onSubmit={handleSubmit(onSubmit)}>
                                    <div className="mb-3">
                                        <label className="form-label">First Name</label>
                                        <input {...register('first_name')} className="form-control" />
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">Last Name</label>
                                        <input {...register('last_name')} className="form-control" />
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">Bio</label>
                                        <textarea {...register('bio')} className="form-control" rows="3" maxLength="500" />
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">City</label>
                                        <input {...register('city')} className="form-control" maxLength="100" />
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">State</label>
                                        <input {...register('state')} className="form-control" maxLength="100" />
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">Profile Picture URL</label>
                                        <input {...register('profile_picture_url')} className="form-control" type="url" />
                                    </div>
                                    <button type="submit" className="btn btn-primary me-2">Save</button>
                                    <button type="button" className="btn btn-secondary" onClick={() => setEditing(false)}>
                                        Cancel
                                    </button>
                                </form>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
