import { useState, useEffect } from 'react';
import {
  X, ChevronRight, FileText, GitBranch, Clock,
  CheckCircle2, Flag, Lock, AlertTriangle, Eye,
  ExternalLink, Copy,
} from 'lucide-react';
import StatusBadge from './StatusBadge';
import { emissionsAPI } from '../api/emissions';
import { auditAPI } from '../api/audit';
import { useToast } from '../context/ToastContext';
import './DetailPanel.css';

const tabs = [
  { id: 'overview', label: 'Overview', icon: Eye },
  { id: 'raw', label: 'Raw Data', icon: FileText },
  { id: 'audit', label: 'Audit Trail', icon: Clock },
];

export default function DetailPanel({ record, onClose, onRefresh }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [provenance, setProvenance] = useState(null);
  const [auditHistory, setAuditHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (!record?.id) return;
    setActiveTab('overview');
    loadDetails();
  }, [record?.id]);

  const loadDetails = async () => {
    if (!record?.id) return;
    setLoading(true);
    try {
      const [prov, audit] = await Promise.allSettled([
        emissionsAPI.getProvenance(record.id),
        auditAPI.getRecordHistory(record.id),
      ]);
      if (prov.status === 'fulfilled') setProvenance(prov.value);
      if (audit.status === 'fulfilled') setAuditHistory(audit.value?.results || audit.value || []);
    } catch {
      // silent — panel still shows record data
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action) => {
    try {
      if (action === 'approve') await emissionsAPI.approve(record.id);
      else if (action === 'flag') await emissionsAPI.flag(record.id, 'Flagged from detail panel');
      else if (action === 'lock') await emissionsAPI.lock(record.id);
      toast.success(`Record ${action}ed successfully`);
      onRefresh?.();
    } catch (err) {
      toast.error(`Failed to ${action}: ${err.response?.data?.detail || err.message}`);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.info('Copied to clipboard');
  };

  if (!record) return null;

  const isLocked = record.status === 'locked';
  const isApproved = record.status === 'approved';

  return (
    <div className="detail-panel-overlay" onClick={onClose}>
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="detail-header">
          <div>
            <h3 className="detail-title">Record Details</h3>
            <span className="detail-id font-mono text-xs">
              ID: {record.id}
              <button className="copy-btn" onClick={() => copyToClipboard(String(record.id))}>
                <Copy size={12} />
              </button>
            </span>
          </div>
          <button className="btn-icon btn-ghost" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Status + Actions */}
        <div className="detail-status-bar">
          <StatusBadge status={record.status} />
          {!isLocked && (
            <div className="detail-actions">
              {!isApproved && (
                <button className="btn btn-sm btn-success" onClick={() => handleAction('approve')}>
                  <CheckCircle2 size={14} /> Approve
                </button>
              )}
              <button className="btn btn-sm btn-warning" onClick={() => handleAction('flag')}>
                <Flag size={14} /> Flag
              </button>
              {isApproved && (
                <button className="btn btn-sm btn-primary" onClick={() => handleAction('lock')}>
                  <Lock size={14} /> Lock
                </button>
              )}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="detail-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`detail-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon size={14} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="detail-body">
          {activeTab === 'overview' && (
            <div className="detail-overview fade-in">
              <div className="detail-section">
                <h4 className="detail-section-title">Normalized Data</h4>
                <div className="detail-grid">
                  <div className="detail-field">
                    <span className="detail-label">Date</span>
                    <span className="detail-value">{record.date ? new Date(record.date).toLocaleDateString() : '—'}</span>
                  </div>
                  <div className="detail-field">
                    <span className="detail-label">Source Type</span>
                    <span className="detail-value">{record.source_type || '—'}</span>
                  </div>
                  <div className="detail-field">
                    <span className="detail-label">Scope</span>
                    <span className="detail-value">Scope {record.scope || '?'}</span>
                  </div>
                  <div className="detail-field">
                    <span className="detail-label">Category</span>
                    <span className="detail-value">{record.category || '—'}</span>
                  </div>
                  <div className="detail-field full-width">
                    <span className="detail-label">CO₂e (kg)</span>
                    <span className="detail-value font-mono" style={{ fontSize: 'var(--text-xl)', color: 'var(--accent-primary)' }}>
                      {Number(record.co2e_kg || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              </div>

              {record.emission_factor && (
                <div className="detail-section">
                  <h4 className="detail-section-title">Emission Factor</h4>
                  <div className="detail-grid">
                    <div className="detail-field">
                      <span className="detail-label">Factor</span>
                      <span className="detail-value font-mono">{record.emission_factor}</span>
                    </div>
                    <div className="detail-field">
                      <span className="detail-label">Unit</span>
                      <span className="detail-value">{record.unit || '—'}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Provenance Chain */}
              {provenance && (
                <div className="detail-section">
                  <h4 className="detail-section-title">
                    <GitBranch size={14} /> Provenance Chain
                  </h4>
                  <div className="provenance-chain">
                    {(provenance.chain || [provenance]).map((step, i) => (
                      <div key={i} className="provenance-step">
                        <div className="provenance-dot" />
                        <div className="provenance-content">
                          <span className="provenance-action">{step.action || step.stage || 'Processing'}</span>
                          <span className="provenance-time text-xs text-muted">
                            {step.timestamp ? new Date(step.timestamp).toLocaleString() : ''}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'raw' && (
            <div className="detail-raw fade-in">
              <div className="detail-section">
                <h4 className="detail-section-title">Raw Source Data</h4>
                <pre className="raw-data-block font-mono">
                  {JSON.stringify(record.raw_data || record, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {activeTab === 'audit' && (
            <div className="detail-audit fade-in">
              <div className="detail-section">
                <h4 className="detail-section-title">Audit History</h4>
                {auditHistory.length === 0 ? (
                  <div className="empty-state" style={{ padding: 'var(--space-8)' }}>
                    <Clock size={32} />
                    <h3>No audit history yet</h3>
                    <p>Actions performed on this record will appear here.</p>
                  </div>
                ) : (
                  <div className="audit-timeline">
                    {auditHistory.map((entry, i) => (
                      <div key={i} className="audit-entry">
                        <div className="audit-entry-dot" />
                        <div className="audit-entry-content">
                          <div className="audit-entry-header">
                            <span className="audit-entry-action">{entry.action}</span>
                            <span className="audit-entry-time text-xs text-muted">
                              {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : ''}
                            </span>
                          </div>
                          <span className="audit-entry-user text-xs text-muted">
                            by {entry.user || entry.user_email || 'System'}
                          </span>
                          {entry.changes && (
                            <pre className="audit-changes font-mono text-xs">
                              {typeof entry.changes === 'string' ? entry.changes : JSON.stringify(entry.changes, null, 2)}
                            </pre>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
