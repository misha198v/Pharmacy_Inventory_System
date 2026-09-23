import React from 'react';
import './AppLayout.css';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">🏥 Pharmacy</div>
      <nav className="sidebar-nav">
        <a href="#" className="sidebar-link">Dashboard</a>
        <a href="#" className="sidebar-link">Inventory</a>
        <a href="#" className="sidebar-link">Reports</a>
      </nav>
    </aside>
  );
}