import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Upload,
  ClipboardList,
  BarChart3,
  Leaf,
  Settings,
  HelpCircle,
} from 'lucide-react';
import './Sidebar.css';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/ingestion', label: 'Data Ingestion', icon: Upload },
  { path: '/audit', label: 'Audit Trail', icon: ClipboardList },
];

const secondaryItems = [
  { path: '/settings', label: 'Settings', icon: Settings },
  { path: '/help', label: 'Help & Docs', icon: HelpCircle },
];

export default function Sidebar({ collapsed }) {
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="logo-icon">
            <Leaf size={20} />
          </div>
          {!collapsed && (
            <div className="logo-text">
              <span className="logo-brand">Breathe</span>
              <span className="logo-sub">ESG</span>
            </div>
          )}
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          {!collapsed && <span className="nav-section-label">Main</span>}
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''}`
              }
              title={collapsed ? item.label : undefined}
            >
              <item.icon size={19} className="nav-icon" />
              {!collapsed && <span className="nav-label">{item.label}</span>}
            </NavLink>
          ))}
        </div>

        <div className="nav-section" style={{ marginTop: 'auto' }}>
          {!collapsed && <span className="nav-section-label">Support</span>}
          {secondaryItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''}`
              }
              title={collapsed ? item.label : undefined}
            >
              <item.icon size={19} className="nav-icon" />
              {!collapsed && <span className="nav-label">{item.label}</span>}
            </NavLink>
          ))}
        </div>
      </nav>

      {!collapsed && (
        <div className="sidebar-footer">
          <div className="sidebar-version">
            <BarChart3 size={14} />
            <span>v1.0.0 — Carbon Review</span>
          </div>
        </div>
      )}
    </aside>
  );
}
