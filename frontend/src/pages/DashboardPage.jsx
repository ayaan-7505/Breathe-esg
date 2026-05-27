import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { RefreshCw, BarChart3, Filter } from 'lucide-react';
import SummaryCards from '../components/SummaryCards';
import EmissionChart from '../components/EmissionChart';
import ReviewTable from '../components/ReviewTable';
import FilterSidebar from '../components/FilterSidebar';
import DetailPanel from '../components/DetailPanel';
import { emissionsAPI } from '../api/emissions';
import { useToast } from '../context/ToastContext';
import './DashboardPage.css';

const DEFAULT_FILTERS = {
  scopes: [],
  sources: [],
  statuses: [],
  dateFrom: '',
  dateTo: '',
};

export default function DashboardPage() {
  const [searchParams] = useSearchParams();
  const searchVal = searchParams.get('search') || '';

  const [records, setRecords] = useState([]);
  const [summary, setSummary] = useState(null);
  const [chartData, setChartData] = useState({ scopeData: null, sourceData: null });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [showFilters, setShowFilters] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const toast = useToast();

  // Build query params from filters
  const buildParams = useCallback(() => {
    const params = {};
    if (filters.scopes.length) params.scope = filters.scopes.join(',');
    if (filters.sources.length) params.source_type = filters.sources.join(',');
    if (filters.statuses.length) params.status = filters.statuses.join(',');
    if (filters.dateFrom) params.date_from = filters.dateFrom;
    if (filters.dateTo) params.date_to = filters.dateTo;
    if (searchVal) params.search = searchVal;
    return params;
  }, [filters, searchVal]);

  // Fetch all data
  const fetchData = useCallback(async (showRefreshIndicator = false) => {
    if (showRefreshIndicator) setRefreshing(true);
    else setLoading(true);

    const params = buildParams();

    try {
      const [recordsRes, summaryRes, chartsRes] = await Promise.allSettled([
        emissionsAPI.getRecords(params),
        emissionsAPI.getSummary(params),
        emissionsAPI.getChartData(params),
      ]);

      if (recordsRes.status === 'fulfilled') {
        const data = recordsRes.value;
        setRecords(Array.isArray(data) ? data : data?.results || []);
      }

      if (summaryRes.status === 'fulfilled') {
        setSummary(summaryRes.value);
      }

      if (chartsRes.status === 'fulfilled') {
        const charts = chartsRes.value;
        setChartData({
          scopeData: charts?.scope_data || charts?.by_scope || null,
          sourceData: charts?.source_data || charts?.by_source || null,
        });
      }

      setLastUpdated(new Date());
    } catch (err) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [buildParams, toast]);

  // Load data on mount and filter changes
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle filter changes
  const handleFilterChange = useCallback((updates) => {
    setFilters(prev => ({ ...prev, ...updates }));
  }, []);

  const handleFilterReset = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  // Handle row selection for detail panel
  const handleRowSelect = useCallback((record) => {
    setSelectedRecord(prev => prev?.id === record?.id ? null : record);
  }, []);

  // Refresh after an action
  const handleRefresh = useCallback(() => {
    fetchData(true);
    // Also refresh the selected record if one is open
    if (selectedRecord) {
      emissionsAPI.getRecord(selectedRecord.id)
        .then(updated => setSelectedRecord(updated))
        .catch(() => setSelectedRecord(null));
    }
  }, [fetchData, selectedRecord]);

  const formatTime = (date) => {
    if (!date) return '';
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={`dashboard-page ${selectedRecord ? 'dashboard-detail-active' : ''}`}>
      {/* Page Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <h1>Carbon Review Dashboard</h1>
          <p>Review, approve, and manage emission records across all scopes</p>
        </div>
        <div className="dashboard-header-right">
          {lastUpdated && (
            <div className="last-updated">
              <span className="pulse-dot" />
              <span>Updated {formatTime(lastUpdated)}</span>
            </div>
          )}
          <button
            className="filter-toggle-btn btn btn-sm btn-ghost"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter size={14} />
            Filters
          </button>
          <button
            className={`btn btn-sm btn-ghost refresh-btn ${refreshing ? 'refreshing' : ''}`}
            onClick={() => fetchData(true)}
            disabled={refreshing}
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* Main layout: Filters + Content */}
      <div className="dashboard-layout">
        {/* Left filter sidebar */}
        <div className={`dashboard-filters ${showFilters ? 'visible' : ''}`}>
          <FilterSidebar
            filters={filters}
            onFilterChange={handleFilterChange}
            onReset={handleFilterReset}
          />
        </div>

        {/* Main content area */}
        <div className="dashboard-main">
          {/* Summary Cards */}
          <SummaryCards data={summary} loading={loading} />

          {/* Charts */}
          <div className="dashboard-section">
            <div className="dashboard-section-header">
              <span className="dashboard-section-title">
                <BarChart3 size={16} />
                Analytics Overview
              </span>
            </div>
            <EmissionChart
              scopeData={chartData.scopeData}
              sourceData={chartData.sourceData}
              loading={loading}
            />
          </div>

          {/* Review Table */}
          <div className="dashboard-section">
            <ReviewTable
              data={records}
              loading={loading}
              onRowSelect={handleRowSelect}
              onRefresh={handleRefresh}
              selectedId={selectedRecord?.id}
            />
          </div>
        </div>
      </div>

      {/* Detail Panel (slide-in) */}
      {selectedRecord && (
        <DetailPanel
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
          onRefresh={handleRefresh}
        />
      )}
    </div>
  );
}
