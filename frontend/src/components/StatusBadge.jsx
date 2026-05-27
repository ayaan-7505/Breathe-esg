import './StatusBadge.css';

const statusConfig = {
  pending: { label: 'Pending', className: 'badge-pending' },
  reviewed: { label: 'Reviewed', className: 'badge-reviewed' },
  flagged: { label: 'Flagged', className: 'badge-flagged' },
  approved: { label: 'Approved', className: 'badge-approved' },
  locked: { label: 'Locked', className: 'badge-locked' },
};

export default function StatusBadge({ status }) {
  const config = statusConfig[status] || statusConfig.pending;

  return (
    <span className={`badge ${config.className}`}>
      <span className="status-dot" />
      {config.label}
    </span>
  );
}
