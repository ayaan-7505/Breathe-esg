import { TrendingUp, TrendingDown, Clock, CheckCircle2, AlertTriangle, Activity } from 'lucide-react';
import { SkeletonCard } from './LoadingSkeleton';
import './SummaryCards.css';

const cardConfigs = [
  {
    key: 'total_co2e',
    title: 'Total CO₂e',
    icon: Activity,
    color: 'var(--accent-primary)',
    bgColor: 'var(--accent-primary-muted)',
    format: (v) => `${(v || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} t`,
  },
  {
    key: 'pending',
    title: 'Pending Review',
    icon: Clock,
    color: 'var(--accent-warning)',
    bgColor: 'var(--accent-warning-muted)',
    format: (v) => (v || 0).toLocaleString(),
  },
  {
    key: 'approved',
    title: 'Approved',
    icon: CheckCircle2,
    color: 'var(--accent-success)',
    bgColor: 'var(--accent-success-muted)',
    format: (v) => (v || 0).toLocaleString(),
  },
  {
    key: 'flagged',
    title: 'Flagged',
    icon: AlertTriangle,
    color: 'var(--accent-danger)',
    bgColor: 'var(--accent-danger-muted)',
    format: (v) => (v || 0).toLocaleString(),
  },
];

export default function SummaryCards({ data, loading }) {
  if (loading) {
    return (
      <div className="summary-cards stagger-children">
        {[1, 2, 3, 4].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="summary-cards stagger-children">
      {cardConfigs.map((config) => {
        const Icon = config.icon;
        const value = data?.[config.key] ?? 0;
        const trend = data?.[`${config.key}_trend`];
        const isPositive = trend > 0;

        return (
          <div key={config.key} className="summary-card card card-glow">
            <div className="summary-card-header">
              <span className="summary-card-title">{config.title}</span>
              <div
                className="summary-card-icon"
                style={{ background: config.bgColor, color: config.color }}
              >
                <Icon size={18} />
              </div>
            </div>
            <div className="summary-card-value" style={{ color: config.color }}>
              {config.format(value)}
            </div>
            {trend !== undefined && trend !== null && (
              <div className={`summary-card-trend ${isPositive ? 'trend-up' : 'trend-down'}`}>
                {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                <span>{Math.abs(trend).toFixed(1)}%</span>
                <span className="trend-label">vs last period</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
