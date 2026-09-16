import React from 'react';
import { useAuth } from '../../context/AuthContext';

export default function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <div>
      <h1>Welcome, {user?.username || 'User'}!</h1>
      <button onClick={logout}>Log Out</button>
    </div>
  );
}