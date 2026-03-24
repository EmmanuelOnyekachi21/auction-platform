import { Outlet } from 'react-router-dom';

export default function AuthLayout() {
    return (
        <div className="min-vh-100 bg-light d-flex align-items-center py-5">
            <div className="container">
                <div className="text-center mb-4">
                    <h1 className="fw-bold text-primary">AuctionPlatform</h1>
                </div>
                {/* This is where the Login/Register forms will appear */}
                <Outlet />
            </div>
        </div>
    );
}
