import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload, FileSpreadsheet, X, CheckCircle2, AlertCircle,
  Clock, Database, Plane, Zap, Building2, ChevronRight,
  FileText,
} from 'lucide-react';
import { ingestionAPI } from '../api/ingestion';
import { useToast } from '../context/ToastContext';
import { SkeletonTable } from '../components/LoadingSkeleton';
import './IngestionPage.css';

const SOURCE_TYPES = [
  {
    value: 'SAP',
    label: 'SAP Energy Data',
    desc: 'Plant energy, fuel consumption, process emissions',
    icon: Building2,
  },
  {
    value: 'Utility',
    label: 'Utility Bills',
    desc: 'Electricity, gas, water utility invoices',
    icon: Zap,
  },
  {
    value: 'Travel',
    label: 'Travel Records',
    desc: 'Business travel, flights, mileage logs',
    icon: Plane,
  },
];

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

const formatDate = (dateStr) => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

export default function IngestionPage() {
  const [sourceType, setSourceType] = useState('SAP');
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const fileInputRef = useRef(null);
  const toast = useToast();
  const navigate = useNavigate();

  // Load recent jobs
  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    setJobsLoading(true);
    try {
      const data = await ingestionAPI.getJobs();
      setJobs(Array.isArray(data) ? data : data?.results || []);
    } catch {
      // Silent — empty state shown
    } finally {
      setJobsLoading(false);
    }
  };

  // File selection handlers
  const handleFileSelect = useCallback((selectedFile) => {
    if (!selectedFile) return;
    const ext = selectedFile.name.split('.').pop()?.toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
      toast.warning('Please upload a CSV or Excel file (.csv, .xlsx, .xls)');
      return;
    }
    if (selectedFile.size > 50 * 1024 * 1024) {
      toast.warning('File size must be under 50 MB');
      return;
    }
    setFile(selectedFile);
    setUploadResult(null);
  }, [toast]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) handleFileSelect(droppedFile);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  // Upload handler
  const handleUpload = async () => {
    if (!file || !sourceType) {
      toast.warning('Please select a file and source type');
      return;
    }

    setUploading(true);
    setProgress(0);

    try {
      const result = await ingestionAPI.uploadFile(file, sourceType, (percent) => {
        setProgress(percent);
      });
      setUploadResult(result);
      toast.success('File uploaded successfully! Processing will begin shortly.');
      setFile(null);
      setProgress(0);
      // Refresh job list
      loadJobs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setUploadResult(null);
    setProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const getJobStatusClass = (status) => {
    const map = {
      completed: 'job-status-completed',
      processing: 'job-status-processing',
      failed: 'job-status-failed',
      pending: 'job-status-pending',
      partial: 'job-status-partial',
    };
    return map[status?.toLowerCase()] || 'job-status-pending';
  };

  return (
    <div className="ingestion-page fade-in">
      <div className="page-header">
        <h1>Data Ingestion</h1>
        <p>Upload CSV or Excel files to ingest emission data from various sources</p>
      </div>

      {/* Upload Section */}
      <div className="upload-section">
        {/* Dropzone */}
        <div className="card dropzone-card">
          {uploadResult ? (
            <div className="upload-success">
              <div className="upload-success-icon">
                <CheckCircle2 size={28} />
              </div>
              <h3 style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Upload Complete</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                Job #{uploadResult.id || uploadResult.job_id} created.
                Processing has started.
              </p>
              <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-3)' }}>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={() => navigate(`/ingestion/${uploadResult.id || uploadResult.job_id}`)}
                >
                  View Details <ChevronRight size={14} />
                </button>
                <button
                  className="btn btn-sm btn-ghost"
                  onClick={() => setUploadResult(null)}
                >
                  Upload Another
                </button>
              </div>
            </div>
          ) : (
            <>
              <div
                className={`dropzone ${dragOver ? 'drag-over' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => handleFileSelect(e.target.files?.[0])}
                />
                <div className="dropzone-icon">
                  <Upload size={24} />
                </div>
                <div className="dropzone-title">
                  Drop your file here, or <span className="dropzone-browse">browse</span>
                </div>
                <div className="dropzone-subtitle">
                  Select a CSV or Excel file containing emission data
                </div>
                <div className="dropzone-formats">
                  Supported: .csv, .xlsx, .xls — Max 50 MB
                </div>
              </div>

              {/* Selected file preview */}
              {file && (
                <div className="selected-file" style={{ marginTop: 'var(--space-4)' }}>
                  <div className="selected-file-info">
                    <div className="selected-file-icon">
                      <FileSpreadsheet size={18} />
                    </div>
                    <div>
                      <div className="selected-file-name">{file.name}</div>
                      <div className="selected-file-size">{formatFileSize(file.size)}</div>
                    </div>
                  </div>
                  <button className="btn btn-sm btn-ghost btn-icon" onClick={clearFile}>
                    <X size={14} />
                  </button>
                </div>
              )}

              {/* Upload progress */}
              {uploading && (
                <div className="upload-progress">
                  <div className="progress-bar-wrapper">
                    <div className="progress-bar" style={{ width: `${progress}%` }} />
                  </div>
                  <div className="progress-text">
                    <span>Uploading...</span>
                    <span>{progress}%</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Upload Config */}
        <div className="card upload-config">
          <div>
            <div className="upload-config-title">Source Type</div>
            <div className="upload-config-desc">
              Select the data source format for proper parsing
            </div>
          </div>

          <div className="source-type-selector">
            {SOURCE_TYPES.map((type) => {
              const Icon = type.icon;
              return (
                <div
                  key={type.value}
                  className={`source-type-option ${sourceType === type.value ? 'selected' : ''}`}
                  onClick={() => setSourceType(type.value)}
                >
                  <div className="source-type-radio" />
                  <Icon size={18} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                  <div>
                    <div className="source-type-label">{type.label}</div>
                    <div className="source-type-desc">{type.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Upload button */}
          <button
            className="btn btn-primary btn-lg w-full"
            onClick={handleUpload}
            disabled={!file || uploading}
            style={{ marginTop: 'auto' }}
          >
            {uploading ? (
              <>Processing...</>
            ) : (
              <>
                <Upload size={18} />
                Upload & Process
              </>
            )}
          </button>
        </div>
      </div>

      {/* Recent Jobs */}
      <div className="jobs-section">
        <div className="jobs-header">
          <h2>Recent Upload Jobs</h2>
          <button className="btn btn-sm btn-ghost" onClick={loadJobs}>
            Refresh
          </button>
        </div>

        <div className="card">
          {jobsLoading ? (
            <SkeletonTable rows={5} cols={6} />
          ) : jobs.length === 0 ? (
            <div className="empty-state">
              <Database size={40} />
              <h3>No upload jobs yet</h3>
              <p>Upload a CSV or Excel file above to create your first ingestion job.</p>
            </div>
          ) : (
            <div className="jobs-table-wrapper">
              <table className="jobs-table">
                <thead>
                  <tr>
                    <th>Job ID</th>
                    <th>File</th>
                    <th>Source</th>
                    <th>Status</th>
                    <th>Records</th>
                    <th>Created</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <tr
                      key={job.id}
                      onClick={() => navigate(`/ingestion/${job.id}`)}
                    >
                      <td>
                        <span className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>
                          #{job.id}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <FileText size={14} style={{ color: 'var(--text-muted)' }} />
                          <span className="truncate" style={{ maxWidth: 200 }}>
                            {job.file_name || job.filename || '—'}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="record-type-tag">{job.source_type || '—'}</span>
                      </td>
                      <td>
                        <span className={`job-status ${getJobStatusClass(job.status)}`}>
                          {job.status || 'pending'}
                        </span>
                      </td>
                      <td>
                        <div className="job-stats">
                          <span className="job-stat job-stat-success">
                            <CheckCircle2 size={12} />
                            {job.success_count ?? job.records_created ?? 0}
                          </span>
                          <span className="job-stat job-stat-error">
                            <AlertCircle size={12} />
                            {job.error_count ?? job.records_failed ?? 0}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {formatDate(job.created_at || job.uploaded_at)}
                        </span>
                      </td>
                      <td>
                        <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
