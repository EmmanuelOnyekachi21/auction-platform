import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import apiClient from '../../api/client';

export default function VerifySellersPage() {
  const [sellers, setSellers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSeller, setSelectedSeller] = useState(null);
  const { register, handleSubmit, reset } = useForm();

  useEffect(() => {
    fetchSellers();
  }, []);

  const fetchSellers = async () => {
    try {
      // For now, we'll manually add seller user IDs
      // In a real app, you'd have an endpoint to list all sellers
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch sellers:', error);
      setLoading(false);
    }
  };

  const verifySeller = async (userId, data) => {
    try {
      await apiClient.patch(`/users/${userId}/seller-profile/verify`, {
        is_verified: data.is_verified,
        rejection_reason: data.rejection_reason || null
      });

      alert(data.is_verified ? 'Seller verified successfully!' : 'Seller rejected');
      setSelectedSeller(null);
      reset();
    } catch (error) {
      console.error('Failed to verify seller:', error);
      alert(error.response?.data?.detail || 'Failed to verify seller');
    }
  };

  const onSubmit = (data) => {
    if (selectedSeller) {
      verifySeller(selectedSeller, data);
    }
  };

  return (
    <div className="container mt-5">
      <div className="row">
        <div className="col-md-10 mx-auto">
          <div className="card">
            <div className="card-header bg-primary text-white">
              <h3 className="mb-0">Verify Sellers</h3>
            </div>
            <div className="card-body">
              <div className="alert alert-info">
                <strong>Admin Tool:</strong> Enter a user ID below to verify or reject their seller application.
              </div>

              <form onSubmit={handleSubmit(onSubmit)}>
                <div className="mb-3">
                  <label className="form-label">User ID</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Enter user UUID"
                    value={selectedSeller || ''}
                    onChange={(e) => setSelectedSeller(e.target.value)}
                    required
                  />
                  <small className="text-muted">
                    You can get the user ID from the database or user profile URL
                  </small>
                </div>

                <div className="mb-3">
                  <label className="form-label">Action</label>
                  <div>
                    <div className="form-check">
                      <input
                        {...register('is_verified')}
                        className="form-check-input"
                        type="radio"
                        value="true"
                        id="approve"
                        defaultChecked
                      />
                      <label className="form-check-label text-success" htmlFor="approve">
                        <strong>Approve</strong> - Verify this seller
                      </label>
                    </div>
                    <div className="form-check">
                      <input
                        {...register('is_verified')}
                        className="form-check-input"
                        type="radio"
                        value="false"
                        id="reject"
                      />
                      <label className="form-check-label text-danger" htmlFor="reject">
                        <strong>Reject</strong> - Deny seller verification
                      </label>
                    </div>
                  </div>
                </div>

                <div className="mb-3">
                  <label className="form-label">Rejection Reason (required if rejecting)</label>
                  <textarea
                    {...register('rejection_reason')}
                    className="form-control"
                    rows="3"
                    placeholder="Explain why the seller application was rejected..."
                  />
                </div>

                <button type="submit" className="btn btn-primary">
                  Submit Verification
                </button>
              </form>

              <hr className="my-4" />

              <div className="alert alert-secondary">
                <h5>How to use:</h5>
                <ol>
                  <li>A user registers as a seller via "Become a Seller" page</li>
                  <li>Get their user ID from the database or their profile URL</li>
                  <li>Enter the user ID above</li>
                  <li>Choose to approve or reject</li>
                  <li>If rejecting, provide a reason</li>
                  <li>Submit - the user will receive an email notification</li>
                </ol>
              </div>

              <div className="card bg-light mt-3">
                <div className="card-body">
                  <h6>Quick Test:</h6>
                  <p className="mb-2">To test this feature:</p>
                  <ol className="mb-0">
                    <li>Register a new user account</li>
                    <li>Go to "Become a Seller" and submit</li>
                    <li>Note the user ID from the profile URL or database</li>
                    <li>Come back here as admin and verify them</li>
                  </ol>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
