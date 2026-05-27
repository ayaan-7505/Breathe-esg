import { Search, Bell, LogOut, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function Header({ sidebarCollapsed, onToggleSidebar }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const searchVal = searchParams.get('search') || '';

  const handleSearchChange = (e) => {
    const val = e.target.value;
    if (val) {
      setSearchParams({ search: val });
    } else {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('search');
      setSearchParams(nextParams);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U';

  return (
    <header className="header">
      <div className="header-left">
        <button
          className="btn-icon btn-ghost"
          onClick={onToggleSidebar}
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
        <div className="header-search">
          <Search size={15} className="header-search-icon" />
          <input
            type="text"
            className="input"
            placeholder="Search records, jobs..."
            value={searchVal}
            onChange={handleSearchChange}
          />
        </div>
      </div>

      <div className="header-right">
        <button className="btn-icon btn-ghost" style={{ position: 'relative' }}>
          <Bell size={18} />
          <span
            style={{
              position: 'absolute',
              top: 6,
              right: 6,
              width: 7,
              height: 7,
              background: 'var(--accent-danger)',
              borderRadius: '50%',
              border: '2px solid var(--bg-primary)',
            }}
          />
        </button>

        <div className="header-user">
          <div className="header-avatar">{initials}</div>
          <div className="header-user-info">
            <span className="header-user-name">{user?.name || 'User'}</span>
            <span className="header-user-role">{user?.role || 'Analyst'}</span>
          </div>
        </div>

        <button
          className="btn-icon btn-ghost"
          onClick={handleLogout}
          title="Sign out"
        >
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
