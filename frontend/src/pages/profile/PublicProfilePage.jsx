import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../../api/client';

export default function PublicProfilePage() {
  const { userId } = useParams();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPublicProfile();
  }, [userId]);

  const fetchPublicProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(`/users/${userId}`);
      setProfile(response.data);
    } catch (error) {
      console.error('Failed to fetch public profile:', error);
      setError(error.response?.data?.detail || 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const renderStars = (rating) => {
    const stars = [];
    const ratingValue = parseFloat(rating) || 0;
    for (let i = 0; i < 5; i++) {
      stars.push(
        <span key={i} className={i < Math.floor(ratingValue) ? 'text-warning' : 'text-muted'}>
          ★
        </span>
      );
    }
    return stars;
  };

  if (loading) {
    return (
      <div className="container mt-5">
        <div className="text-center">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="container mt-5">
        <div className="alert alert-warning" role="alert">
          User not found
        </div>
      </div>
    );
  }

  return (
    <div className="container mt-5">
      <div className="row">
        <div className="col-md-8 mx-auto">
          <div className="card shadow">
            <div className="card-header bg-primary text-white">
              <h3 className="mb-0">
                {profile.first_name} {profile.last_name}
              </h3>
            </div>
            <div className="card-body">
              <div className="row mb-3">
                <div className="col-md-6">
                  <div className="mb-3">
                    <strong>Rating:</strong>
                    <div className="mt-1">
                      {renderStars(profile.rating)}
                      <span className="ms-2 text-muted">
                        ({parseFloat(profile.rating || 0).toFixed(2)}/5.0)
                      </span>
                    </div>
                  </div>
                </div>
                <div className="col-md-6">
                  <div className="mb-3">
                    <strong>Member Since:</strong>
                    <div className="mt-1">
                      {new Date(profile.member_since).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </div>
                  </div>
                </div>
              </div>

              <div className="row mb-3">
                <div className="col-md-6">
                  <div className="card bg-light">
                    <div className="card-body text-center">
                      <h5 className="card-title text-success">{profile.total_sales}</h5>
                      <p className="card-text text-muted mb-0">Total Sales</p>
                    </div>
                  </div>
                </div>
                <div className="col-md-6">
                  <div className="card bg-light">
                    <div className="card-body text-center">
                      <h5 className="card-title text-primary">{profile.total_purchases}</h5>
                      <p className="card-text text-muted mb-0">Total Purchases</p>
                    </div>
                  </div>
                </div>
              </div>

              {profile.is_verified_seller && (
                <div className="alert alert-success d-flex align-items-center" role="alert">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    fill="currentColor"
                    className="bi bi-patch-check-fill me-2"
                    viewBox="0 0 16 16"
                  >
                    <path d="M10.067.87a2.89 2.89 0 0 0-4.134 0l-.622.638-.89-.011a2.89 2.89 0 0 0-2.924 2.924l.01.89-.636.622a2.89 2.89 0 0 0 0 4.134l.637.622-.011.89a2.89 2.89 0 0 0 2.924 2.924l.89-.01.622.636a2.89 2.89 0 0 0 4.134 0l.622-.637.89.011a2.89 2.89 0 0 0 2.924-2.924l-.01-.89.636-.622a2.89 2.89 0 0 0 0-4.134l-.637-.622.011-.89a2.89 2.89 0 0 0-2.924-2.924l-.89.01-.622-.636zm.287 5.984-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7 8.793l2.646-2.647a.5.5 0 0 1 .708.708z"/>
                  </svg>
                  <div>
                    <strong>Verified Seller</strong>
                    {profile.seller_type && (
                      <span className="ms-2">
                        - {profile.seller_type.charAt(0) + profile.seller_type.slice(1).toLowerCase()}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {!profile.is_verified_seller && profile.total_sales === 0 && (
                <div className="alert alert-info" role="alert">
                  This user hasn't made any sales yet.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
