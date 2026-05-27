import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, FileSpreadsheet, Clock, User, Database,
  CheckCircle2, XCircle, AlertTriangle, ChevronRight,
  RefreshCw, FileText, Hash,
} from 'lucide-react';
import { ingestionAPI } from '../api/ingestion';
import { useToast } from '../context/ToastContext';
import { SkeletonCard, SkeletonTable } from '../components/LoadingSkeleton';
import './IngestionDetailPage.css';

const formatDate = (dateStr) => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

export default function IngestionDetailPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [job, setJob] = useState(null);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('errors');
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    loadJobDetail();
  }, [jobId]);

  const loadJobDetail = async () => {
    setLoading(true);
    try {
      const [jobRes, errorsRes] = await Promise.allSettled([
        ingestionAPI.getJobDetail(jobId),
        ingestionAPI.getJobErrors(jobId),
      ]);

      if (jobRes.status === 'fulfilled') {
        setJob(jobRes.value);
      } else {
        toast.error('Failed to load job details');
      }

      if (errorsRes.status === 'fulfilled') {
        const errData = errorsRes.value;
        setErrors(Array.isArray(errData) ? errData : errData?.results || []);
      }
    } catch {
      toast.error('Failed to load job details');
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await ingestionAPI.retryJob(jobId);
      toast.success('Retry initiated successfully');
      loadJobDetail();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Retry failed');
    } finally {
      setRetrying(false);
    }
  };

  const getStatusClass = (status) => {
    const map = {
      completed: 'job-status-completed',
      processing: 'job-status-processing',
      failed: 'job-status-failed',
      pending: 'job-status-pending',
      partial: 'job-status-partial',
    };
    return map[status?.toLowerCase()] || 'job-status-pending';
  };

  if (loading) {
    return (
      <div className="ingestion-detail-page fade-in">
        <div className="detail-breadcrumb">
          <Link to="/ingestion"><ArrowLeft size={14} /> Ingestion</Link>
          <span className="separator">/</span>
          <span>Job #{jobId}</span>
        </div>
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <SkeletonCard />
        </div>
        <div className="job-summary-cards stagger-children">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="card job-summary-card">
              <SkeletonCard />
            </div>
          ))}
        </div>
        <div className="card" style={{ marginTop: 'var(--space-6)' }}>
          <SkeletonTable rows={6} cols={4} />
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="ingestion-detail-page fade-in">
        <div className="detail-breadcrumb">
          <Link to="/ingestion"><ArrowLeft size={14} /> Ingestion</Link>
          <span className="separator">/</span>
          <span>Job #{jobId}</span>
        </div>
        <div className="empty-state">
          <AlertTriangle size={40} />
          <h3>Job not found</h3>
          <p>The job you're looking for doesn't exist or has been removed.</p>
          <Link to="/ingestion" className="btn btn-sm btn-primary" style={{ marginTop: 'var(--space-4)' }}>
            <ArrowLeft size={14} /> Back to Ingestion
          </Link>
        </div>
      </div>
    );
  }

  const totalRecords = (job.success_count ?? job.records_created ?? 0) + (job.error_count ?? job.records_failed ?? 0);
  const successCount = job.success_count ?? job.records_created ?? 0;
  const errorCount = job.error_count ?? job.records_failed ?? 0;
  const successRate = totalRecords > 0 ? ((successCount / totalRecords) * 100).toFixed(1) : 0;

  return (
    <div className="ingestion-detail-page fade-in">
      {/* Breadcrumb */}
      <div className="detail-breadcrumb">
        <Link to="/ingestion">
          <ArrowLeft size={14} /> Data Ingestion
        </Link>
        <span className="separator">/</span>
        <span>Job #{jobId}</span>
      </div>

      {/* Job Metadata Card */}
      <div className="card job-meta-card">
        <div className="job-meta-left">
          <div className="job-meta-title">
            <div className="job-meta-file-icon">
              <FileSpreadsheet size={20} />
            </div>
            {job.file_name || job.filename || `Job #${jobId}`}
          </div>
          <div className="job-meta-details">
            <div className="job-meta-item">
              <Database size={14} />
              <span>{job.source_type || 'Unknown'} Source</span>
            </div>
            <div className="job-meta-item">
              <User size={14} />
              <span>{job.uploaded_by || job.user || 'System'}</span>
            </div>
            <div className="job-meta-item">
              <Clock size={14} />
              <span>{formatDate(job.created_at || job.uploaded_at)}</span>
            </div>
            <div className="job-meta-item">
              <Hash size={14} />
              <span className="font-mono">ID: {jobId}</span>
            </div>
          </div>
        </div>
        <div className="job-meta-right">
          <span className={`job-status ${getStatusClass(job.status)}`}>
            {job.status || 'pending'}
          </span>
          {(job.status === 'failed' || job.status === 'partial') && (
            <button
              className="btn btn-sm btn-warning"
              onClick={handleRetry}
              disabled={retrying}
            >
              <RefreshCw size={14} className={retrying ? 'refreshing' : ''} />
              {retrying ? 'Retrying...' : 'Retry Job'}
            </button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="job-summary-cards stagger-children">
        <div className="card job-summary-card">
          <div className="job-summary-icon" style={{ background: 'var(--accent-info-muted)', color: 'var(--accent-info)' }}>
            <FileText size={20} />
          </div>
          <div className="job-summary-content">
            <div className="job-summary-value" style={{ color: 'var(--accent-info)' }}>{totalRecords}</div>
            <div className="job-summary-label">Total Rows</div>
          </div>
        </div>
        <div className="card job-summary-card">
          <div className="job-summary-icon" style={{ background: 'var(--accent-success-muted)', color: 'var(--accent-success)' }}>
            <CheckCircle2 size={20} />
          </div>
          <div className="job-summary-content">
            <div className="job-summary-value" style={{ color: 'var(--accent-success)' }}>{successCount}</div>
            <div className="job-summary-label">Successful</div>
          </div>
        </div>
        <div className="card job-summary-card">
          <div className="job-summary-icon" style={{ background: 'var(--accent-danger-muted)', color: 'var(--accent-danger)' }}>
            <XCircle size={20} />
          </div>
          <div className="job-summary-content">
            <div className="job-summary-value" style={{ color: 'var(--accent-danger)' }}>{errorCount}</div>
            <div className="job-summary-label">Failed</div>
          </div>
        </div>
        <div className="card job-summary-card">
          <div className="job-summary-icon" style={{ background: 'var(--accent-primary-muted)', color: 'var(--accent-primary)' }}>
            <CheckCircle2 size={20} />
          </div>
          <div className="job-summary-content">
            <div className="job-summary-value" style={{ color: 'var(--accent-primary)' }}>{successRate}%</div>
            <div className="job-summary-label">Success Rate</div>
          </div>
        </div>
      </div>

      {/* Result Tabs + Table */}
      <div className="card result-section">
        <div className="result-tabs">
          <button
            className={`result-tab ${activeTab === 'errors' ? 'active' : ''}`}
            onClick={() => setActiveTab('errors')}
          >
            <XCircle size={14} />
            Failed Rows
            <span className="result-tab-count">{errorCount}</span>
          </button>
          <button
            className={`result-tab ${activeTab === 'success' ? 'active' : ''}`}
            onClick={() => setActiveTab('success')}
          >
            <CheckCircle2 size={14} />
            Successful Rows
            <span className="result-tab-count">{successCount}</span>
          </button>
        </div>

        {activeTab === 'errors' && (
          <div className="fade-in">
            {errors.length === 0 ? (
              <div className="empty-state" style={{ padding: 'var(--space-10)' }}>
                <CheckCircle2 size={40} style={{ color: 'var(--accent-success)' }} />
                <h3>No errors</h3>
                <p>All rows were processed successfully.</p>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>Field</th>
                      <th>Value</th>
                      <th>Error Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {errors.map((err, i) => (
                      <tr key={i}>
                        <td>
                          <span className="row-number">{err.row ?? err.row_number ?? i + 1}</span>
                        </td>
                        <td>
                          <span className="font-mono text-sm">{err.field || err.column || '—'}</span>
                        </td>
                        <td>
                          <span className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>
                            {err.value != null ? String(err.value).substring(0, 50) : '—'}
                          </span>
                        </td>
                        <td>
                          <span className="error-message">
                            {err.message || err.error || err.detail || 'Validation error'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'success' && (
          <div className="fade-in">
            {successCount === 0 ? (
              <div className="empty-state" style={{ padding: 'var(--space-10)' }}>
                <AlertTriangle size={40} />
                <h3>No successful rows</h3>
                <p>No rows were processed successfully. Check the errors tab for details.</p>
              </div>
            ) : (
              <div className="empty-state" style={{ padding: 'var(--space-10)' }}>
                <CheckCircle2 size={40} style={{ color: 'var(--accent-success)' }} />
                <h3>{successCount} rows processed</h3>
                <p>These records are now available in the review dashboard.</p>
                <Link
                  to="/"
                  className="action-link"
                  style={{ marginTop: 'var(--space-4)' }}
                >
                  Go to Dashboard <ChevronRight size={14} />
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
