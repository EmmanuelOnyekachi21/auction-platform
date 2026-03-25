import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

export default function MainLayout() {
  return (
    <div className="min-vh-100 d-flex flex-column">
      <Navbar />
      <main className="flex-grow-1">
        <Outlet />
      </main>
      <footer className="bg-light py-3 mt-auto">
        <div className="container text-center text-muted">
          <small>&copy; 2024 Auction Platform. All rights reserved.</small>
        </div>
      </footer>
    </div>
  );
}
