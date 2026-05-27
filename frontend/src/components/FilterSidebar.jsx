import { useState } from 'react';
import { Filter, X, RotateCcw } from 'lucide-react';
import './FilterSidebar.css';

const SCOPES = [
  { value: '1', label: 'Scope 1 — Direct' },
  { value: '2', label: 'Scope 2 — Energy' },
  { value: '3', label: 'Scope 3 — Indirect' },
];

const SOURCES = ['SAP', 'Utility', 'Travel', 'Fleet'];
const STATUSES = ['pending', 'reviewed', 'flagged', 'approved', 'locked'];

const statusColors = {
  pending: 'var(--text-muted)',
  reviewed: 'var(--accent-info)',
  flagged: 'var(--accent-warning)',
  approved: 'var(--accent-success)',
  locked: 'var(--accent-primary)',
};

export default function FilterSidebar({ filters, onFilterChange, onReset }) {
  const { scopes = [], sources = [], statuses = [], dateFrom = '', dateTo = '' } = filters;

  const toggleArray = (arr, value) => {
    return arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
  };

  const hasFilters = scopes.length > 0 || sources.length > 0 || statuses.length > 0 || dateFrom || dateTo;

  return (
    <div className="filter-sidebar">
      <div className="filter-header">
        <div className="filter-header-title">
          <Filter size={15} />
          <span>Filters</span>
        </div>
        {hasFilters && (
          <button className="btn btn-sm btn-ghost" onClick={onReset}>
            <RotateCcw size={13} />
            Reset
          </button>
        )}
      </div>

      {/* Scope Filter */}
      <div className="filter-group">
        <label className="filter-label">Scope</label>
        {SCOPES.map((scope) => (
          <label key={scope.value} className="checkbox-wrapper filter-option">
            <input
              type="checkbox"
              checked={scopes.includes(scope.value)}
              onChange={() => onFilterChange({ scopes: toggleArray(scopes, scope.value) })}
            />
            <span className="filter-option-label">{scope.label}</span>
          </label>
        ))}
      </div>

      {/* Source Filter */}
      <div className="filter-group">
        <label className="filter-label">Source Type</label>
        {SOURCES.map((source) => (
          <label key={source} className="checkbox-wrapper filter-option">
            <input
              type="checkbox"
              checked={sources.includes(source)}
              onChange={() => onFilterChange({ sources: toggleArray(sources, source) })}
            />
            <span className="filter-option-label">{source}</span>
          </label>
        ))}
      </div>

      {/* Status Filter */}
      <div className="filter-group">
        <label className="filter-label">Status</label>
        {STATUSES.map((status) => (
          <label key={status} className="checkbox-wrapper filter-option">
            <input
              type="checkbox"
              checked={statuses.includes(status)}
              onChange={() => onFilterChange({ statuses: toggleArray(statuses, status) })}
            />
            <span
              className="filter-status-dot"
              style={{ background: statusColors[status] }}
            />
            <span className="filter-option-label" style={{ textTransform: 'capitalize' }}>{status}</span>
          </label>
        ))}
      </div>

      {/* Date Range */}
      <div className="filter-group">
        <label className="filter-label">Date Range</label>
        <div className="filter-date-range">
          <input
            type="date"
            className="input input-sm"
            value={dateFrom}
            onChange={(e) => onFilterChange({ dateFrom: e.target.value })}
          />
          <span className="filter-date-separator">to</span>
          <input
            type="date"
            className="input input-sm"
            value={dateTo}
            onChange={(e) => onFilterChange({ dateTo: e.target.value })}
          />
        </div>
      </div>

      {/* Active filter count */}
      {hasFilters && (
        <div className="filter-active-count">
          {[scopes.length, sources.length, statuses.length, dateFrom ? 1 : 0, dateTo ? 1 : 0]
            .reduce((a, b) => a + b, 0)} active filters
        </div>
      )}
    </div>
  );
}
