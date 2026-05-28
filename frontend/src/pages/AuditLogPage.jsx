import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search, ChevronRight, ChevronLeft, ChevronsLeft, ChevronsRight,
  Clock, Calendar, Filter, RefreshCw,
} from 'lucide-react';
import { auditAPI } from '../api/audit';
import { useToast } from '../context/ToastContext';
import { SkeletonTable } from '../components/LoadingSkeleton';
import './AuditLogPage.css';

const ACTION_TYPES = [
  'All Actions',
  'create',
  'approve',
  'flag',
  'reject',
  'lock',
  'update',
  'upload',
  'delete',
];

const formatTimestamp = (ts) => {
  if (!ts) return '—';
  const date = new Date(ts);
  return date.toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
};

const getActionClass = (action) => {
  if (!action) return 'action-default';
  const lower = action.toLowerCase();
  if (lower.includes('create') || lower.includes('approve')) return 'action-approve';
  if (lower.includes('flag')) return 'action-flag';
  if (lower.includes('lock')) return 'action-lock';
  if (lower.includes('reject') || lower.includes('delete')) return 'action-reject';
  if (lower.includes('update') || lower.includes('upload')) return 'action-update';
  return 'action-default';
};

const getUserInitials = (name) => {
  if (!name) return '?';
  return name.split(/[\s@]+/).map(n => n[0]).join('').toUpperCase().slice(0, 2);
};

export default function AuditLogPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const search = searchParams.get('search') || '';

  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('All Actions');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const toast = useToast();

  const setSearch = (val) => {
    if (val) {
      setSearchParams({ search: val });
    } else {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('search');
      setSearchParams(nextParams);
    }
  };

  const pageSize = 20;

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (actionFilter !== 'All Actions') params.action = actionFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const data = await auditAPI.getLogs(params);

      if (Array.isArray(data)) {
        setLogs(data);
        setTotalCount(data.length);
        setTotalPages(1);
      } else {
        setLogs(data?.results || []);
        setTotalCount(data?.count || data?.total || data?.results?.length || 0);
        setTotalPages(Math.ceil((data?.count || data?.total || 1) / pageSize));
      }
    } catch {
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, [page, search, actionFilter, dateFrom, dateTo, toast]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [search, actionFilter, dateFrom, dateTo]);

  const toggleRow = (id) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const renderChanges = (changes) => {
    if (!changes) return null;
    try {
      const obj = typeof changes === 'string' ? JSON.parse(changes) : changes;
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(changes);
    }
  };

  return (
    <div className="audit-page fade-in">
      <div className="page-header">
        <h1>Audit Trail</h1>
        <p>Track all actions performed on emission records and system events</p>
      </div>

      {/* Filters */}
      <div className="audit-filters">
        <div className="audit-search-wrapper">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            className="input"
            placeholder="Search by user, action, or record ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="select audit-action-filter"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
        >
          {ACTION_TYPES.map(action => (
            <option key={action} value={action}>
              {action === 'All Actions' ? action : action.charAt(0).toUpperCase() + action.slice(1)}
            </option>
          ))}
        </select>

        <div className="audit-date-filters">
          <Calendar size={14} style={{ color: 'var(--text-muted)' }} />
          <input
            type="date"
            className="input input-sm"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            style={{ width: 150 }}
          />
          <span className="date-separator">to</span>
          <input
            type="date"
            className="input input-sm"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            style={{ width: 150 }}
          />
        </div>

        <button className="btn btn-sm btn-ghost" onClick={fetchLogs}>
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Results */}
      <div className="card">
        <div className="audit-results-info">
          <span className="audit-results-count">
            Showing <strong>{logs.length}</strong> of <strong>{totalCount}</strong> entries
          </span>
        </div>

        {loading ? (
          <SkeletonTable rows={10} cols={6} />
        ) : logs.length === 0 ? (
          <div className="empty-state">
            <Clock size={40} />
            <h3>No audit entries found</h3>
            <p>
              {search || actionFilter !== 'All Actions' || dateFrom || dateTo
                ? 'Try adjusting your search filters.'
                : 'Audit entries will appear here as actions are performed.'}
            </p>
          </div>
        ) : (
          <>
            <div className="audit-table-wrapper">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th style={{ width: 30 }}></th>
                    <th>Timestamp</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Record Type</th>
                    <th>Record ID</th>
                    <th>Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => {
                    const id = log.id || log._id || Math.random();
                    const isExpanded = expandedRows.has(id);
                    const hasChanges = log.changes && (
                      (typeof log.changes === 'object' && Object.keys(log.changes).length > 0) ||
                      (typeof log.changes === 'string' && log.changes.length > 2)
                    );

                    return [
                      <tr
                        key={`row-${id}`}
                        className={isExpanded ? 'expanded' : ''}
                        onClick={() => hasChanges && toggleRow(id)}
                      >
                        <td>
                          {hasChanges && (
                            <span className={`expand-toggle ${isExpanded ? 'expanded' : ''}`}>
                              <ChevronRight size={14} />
                            </span>
                          )}
                        </td>
                        <td>
                          <span className="audit-timestamp">
                            {formatTimestamp(log.timestamp || log.created_at)}
                          </span>
                        </td>
                        <td>
                          <div className="audit-user">
                            <div className="audit-user-avatar">
                              {getUserInitials(log.user || log.user_email)}
                            </div>
                            <span className="text-sm">
                              {log.user || log.user_email || 'System'}
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className={`action-badge ${getActionClass(log.action)}`}>
                            {log.action || '—'}
                          </span>
                        </td>
                        <td>
                          <span className="record-type-tag">
                            {log.record_type || log.entity_type || '—'}
                          </span>
                        </td>
                        <td>
                          <span className="record-id">
                            {log.record_id || log.entity_id || '—'}
                          </span>
                        </td>
                        <td>
                          <span className="text-sm text-secondary truncate" style={{ maxWidth: 200, display: 'inline-block' }}>
                            {log.summary || log.description || '—'}
                          </span>
                        </td>
                      </tr>,
                      isExpanded && hasChanges && (
                        <tr key={`expanded-${id}`} className="audit-expanded-row">
                          <td colSpan={7}>
                            <div className="audit-changes-content">
                              <div className="changes-title">Field Changes</div>
                              <pre className="changes-json">
                                {renderChanges(log.changes)}
                              </pre>
                            </div>
                          </td>
                        </tr>
                      ),
                    ];
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="audit-pagination">
                <div className="audit-pagination-info">
                  Page {page} of {totalPages}
                </div>
                <div className="audit-pagination-controls">
                  <button
                    className="btn btn-sm btn-ghost btn-icon"
                    onClick={() => setPage(1)}
                    disabled={page <= 1}
                  >
                    <ChevronsLeft size={16} />
                  </button>
                  <button
                    className="btn btn-sm btn-ghost btn-icon"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page <= 1}
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    className="btn btn-sm btn-ghost btn-icon"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                  >
                    <ChevronRight size={16} />
                  </button>
                  <button
                    className="btn btn-sm btn-ghost btn-icon"
                    onClick={() => setPage(totalPages)}
                    disabled={page >= totalPages}
                  >
                    <ChevronsRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
