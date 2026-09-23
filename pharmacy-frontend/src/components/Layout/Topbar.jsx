import React from 'react';
import { useAuth } from '../../context/AuthContext';
import './AppLayout.css';

export default function Topbar() {
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <div className="topbar-title">Pharmacy Inventory System</div>
      <div className="topbar-user">
        <span className="topbar-username">
          {user?.username || 'User'}
        </span>
        <button onClick={logout} className="btn-logout">
          Log Out
        </button>
      </div>
    </header>
  );
}