import { useState, useMemo, useCallback, useEffect } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  getFilteredRowModel,
  flexRender,
} from '@tanstack/react-table';
import StatusBadge from './StatusBadge';
import {
  ArrowUpDown, ArrowUp, ArrowDown,
  ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight,
  CheckCircle2, Flag, Lock, MoreHorizontal, Eye,
} from 'lucide-react';
import { SkeletonTable } from './LoadingSkeleton';
import { useToast } from '../context/ToastContext';
import { emissionsAPI } from '../api/emissions';
import './ReviewTable.css';

const formatCO2e = (val) => {
  if (val == null) return '—';
  return Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const formatDate = (dateStr) => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
};

export default function ReviewTable({ data, loading, onRowSelect, onRefresh, selectedId }) {
  const [sorting, setSorting] = useState([]);
  const [rowSelection, setRowSelection] = useState({});
  const [globalFilter, setGlobalFilter] = useState('');
  const [showBulkActions, setShowBulkActions] = useState(false);
  const toast = useToast();

  const selectedCount = Object.keys(rowSelection).filter(k => rowSelection[k]).length;

  useEffect(() => {
    setShowBulkActions(selectedCount > 0);
  }, [selectedCount]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.key === 'a' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        const allSelected = {};
        (data || []).forEach((_, i) => { allSelected[i] = true; });
        setRowSelection(allSelected);
      }
      if (e.key === 'Enter' && selectedCount > 0 && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        handleBulkAction('approve');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [data, selectedCount]);

  const handleAction = useCallback(async (action, id, reason = '') => {
    try {
      if (action === 'approve') await emissionsAPI.approve(id);
      else if (action === 'flag') await emissionsAPI.flag(id, reason);
      else if (action === 'lock') await emissionsAPI.lock(id);
      toast.success(`Record ${action}ed successfully`);
      onRefresh?.();
    } catch (err) {
      toast.error(`Failed to ${action} record: ${err.response?.data?.detail || err.message}`);
    }
  }, [toast, onRefresh]);

  const handleBulkAction = useCallback(async (action) => {
    const selectedIndices = Object.keys(rowSelection).filter(k => rowSelection[k]).map(Number);
    const ids = selectedIndices.map(i => data[i]?.id).filter(Boolean);
    if (ids.length === 0) return;

    try {
      await emissionsAPI.bulkAction(action, ids);
      toast.success(`${ids.length} records ${action}ed successfully`);
      setRowSelection({});
      onRefresh?.();
    } catch (err) {
      toast.error(`Bulk ${action} failed: ${err.response?.data?.detail || err.message}`);
    }
  }, [rowSelection, data, toast, onRefresh]);

  const columns = useMemo(() => [
    {
      id: 'select',
      header: ({ table }) => (
        <input
          type="checkbox"
          checked={table.getIsAllPageRowsSelected()}
          onChange={table.getToggleAllPageRowsSelectedHandler()}
          style={{ accentColor: 'var(--accent-primary)' }}
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={row.getIsSelected()}
          onChange={row.getToggleSelectedHandler()}
          style={{ accentColor: 'var(--accent-primary)' }}
        />
      ),
      size: 40,
      enableSorting: false,
    },
    {
      accessorKey: 'record_date',
      header: 'Date',
      cell: ({ getValue }) => (
        <span className="font-mono text-sm">{formatDate(getValue())}</span>
      ),
      size: 120,
    },
    {
      accessorKey: 'source_type',
      header: 'Source',
      cell: ({ getValue }) => (
        <span className="table-source-tag">{getValue() || '—'}</span>
      ),
      size: 100,
    },
    {
      accessorKey: 'scope',
      header: 'Scope',
      cell: ({ getValue }) => {
        const rawVal = getValue();
        const v = rawVal ? String(rawVal).replace(/\D/g, '') : '';
        const colorMap = { 1: 'var(--accent-primary)', 2: 'var(--accent-success)', 3: 'var(--accent-warning)' };
        return (
          <span className="table-scope" style={{ color: colorMap[v] || 'var(--text-secondary)' }}>
            Scope {v || '?'}
          </span>
        );
      },
      size: 90,
    },
    {
      accessorKey: 'category',
      header: 'Category',
      cell: ({ getValue }) => (
        <span className="truncate" style={{ maxWidth: 160 }}>{getValue() || '—'}</span>
      ),
      size: 160,
    },
    {
      accessorKey: 'co2e_kg',
      header: 'CO₂e (kg)',
      cell: ({ getValue }) => (
        <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>
          {formatCO2e(getValue())}
        </span>
      ),
      size: 110,
      meta: { align: 'right' },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ getValue }) => <StatusBadge status={getValue()} />,
      size: 120,
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const record = row.original;
        const isLocked = record.status === 'locked';
        const isApproved = record.status === 'approved';
        return (
          <div className="table-actions">
            <button
              className="btn btn-sm btn-ghost"
              onClick={(e) => { e.stopPropagation(); onRowSelect?.(record); }}
              title="View details"
            >
              <Eye size={14} />
            </button>
            {!isLocked && (
              <>
                {!isApproved && (
                  <button
                    className="btn btn-sm btn-ghost"
                    onClick={(e) => { e.stopPropagation(); handleAction('approve', record.id); }}
                    title="Approve"
                    style={{ color: 'var(--accent-success)' }}
                  >
                    <CheckCircle2 size={14} />
                  </button>
                )}
                <button
                  className="btn btn-sm btn-ghost"
                  onClick={(e) => { e.stopPropagation(); handleAction('flag', record.id, 'Flagged for review'); }}
                  title="Flag"
                  style={{ color: 'var(--accent-warning)' }}
                >
                  <Flag size={14} />
                </button>
                {isApproved && (
                  <button
                    className="btn btn-sm btn-ghost"
                    onClick={(e) => { e.stopPropagation(); handleAction('lock', record.id); }}
                    title="Lock"
                    style={{ color: 'var(--accent-primary)' }}
                  >
                    <Lock size={14} />
                  </button>
                )}
              </>
            )}
          </div>
        );
      },
      size: 140,
      enableSorting: false,
    },
  ], [handleAction, onRowSelect]);

  const tableData = useMemo(() => data || [], [data]);

  const table = useReactTable({
    data: tableData,
    columns,
    state: { sorting, rowSelection, globalFilter },
    onSortingChange: setSorting,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    enableRowSelection: true,
    initialState: {
      pagination: { pageSize: 15 },
    },
  });

  if (loading) {
    return (
      <div className="card review-table-card">
        <div className="review-table-header">
          <h3>Emission Records</h3>
        </div>
        <SkeletonTable rows={8} cols={7} />
      </div>
    );
  }

  return (
    <div className="card review-table-card">
      <div className="review-table-header">
        <div>
          <h3 className="review-table-title">Emission Records</h3>
          <span className="review-table-count">{tableData.length} total records</span>
        </div>
        <div className="review-table-search">
          <input
            type="text"
            className="input input-sm"
            placeholder="Filter records..."
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            style={{ width: 220 }}
          />
        </div>
      </div>

      {/* Bulk actions bar */}
      {showBulkActions && (
        <div className="bulk-actions-bar fade-in">
          <span className="bulk-count">{selectedCount} selected</span>
          <div className="bulk-buttons">
            <button className="btn btn-sm btn-success" onClick={() => handleBulkAction('approve')}>
              <CheckCircle2 size={14} /> Approve
            </button>
            <button className="btn btn-sm btn-warning" onClick={() => handleBulkAction('flag')}>
              <Flag size={14} /> Flag
            </button>
            <button className="btn btn-sm btn-primary" onClick={() => handleBulkAction('lock')}>
              <Lock size={14} /> Lock
            </button>
            <button className="btn btn-sm btn-ghost" onClick={() => setRowSelection({})}>
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="table-wrapper">
        <table className="review-table">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    style={{
                      width: header.getSize(),
                      textAlign: header.column.columnDef.meta?.align || 'left',
                    }}
                    onClick={header.column.getToggleSortingHandler()}
                    className={header.column.getCanSort() ? 'sortable' : ''}
                  >
                    <div className="th-content">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        <span className="sort-icon">
                          {header.column.getIsSorted() === 'asc' ? (
                            <ArrowUp size={13} />
                          ) : header.column.getIsSorted() === 'desc' ? (
                            <ArrowDown size={13} />
                          ) : (
                            <ArrowUpDown size={13} className="sort-icon-neutral" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="table-empty">
                  <div className="empty-state" style={{ padding: 'var(--space-10)' }}>
                    <h3>No records found</h3>
                    <p>Try adjusting your filters or upload new data.</p>
                  </div>
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className={`table-row ${row.getIsSelected() ? 'row-selected' : ''} ${row.original.id === selectedId ? 'row-active' : ''}`}
                  onClick={() => onRowSelect?.(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      style={{ textAlign: cell.column.columnDef.meta?.align || 'left' }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="table-pagination">
        <div className="pagination-info">
          <span>
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount() || 1}
          </span>
          <select
            className="select input-sm"
            value={table.getState().pagination.pageSize}
            onChange={(e) => table.setPageSize(Number(e.target.value))}
            style={{ width: 100 }}
          >
            {[10, 15, 25, 50].map(size => (
              <option key={size} value={size}>{size} / page</option>
            ))}
          </select>
        </div>
        <div className="pagination-controls">
          <button
            className="btn btn-sm btn-ghost btn-icon"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
          >
            <ChevronsLeft size={16} />
          </button>
          <button
            className="btn btn-sm btn-ghost btn-icon"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            className="btn btn-sm btn-ghost btn-icon"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            <ChevronRight size={16} />
          </button>
          <button
            className="btn btn-sm btn-ghost btn-icon"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
          >
            <ChevronsRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
