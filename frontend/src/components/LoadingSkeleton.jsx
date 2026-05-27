import './LoadingSkeleton.css';

export function SkeletonCard() {
  return (
    <div className="skeleton-card-wrapper">
      <div className="skeleton skeleton-line" style={{ width: '40%', height: 12 }} />
      <div className="skeleton skeleton-line" style={{ width: '60%', height: 28, marginTop: 12 }} />
      <div className="skeleton skeleton-line" style={{ width: '30%', height: 12, marginTop: 8 }} />
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 6 }) {
  return (
    <div className="skeleton-table">
      <div className="skeleton-table-header">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="skeleton skeleton-line" style={{ height: 12, flex: 1 }} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={rowIdx} className="skeleton-table-row">
          {Array.from({ length: cols }).map((_, colIdx) => (
            <div
              key={colIdx}
              className="skeleton skeleton-line"
              style={{ height: 12, flex: 1, opacity: 1 - rowIdx * 0.12 }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="skeleton-chart-wrapper">
      <div className="skeleton" style={{ width: '100%', height: '100%', minHeight: 280 }} />
    </div>
  );
}

export default function LoadingSkeleton({ type = 'card', ...props }) {
  switch (type) {
    case 'card':
      return <SkeletonCard />;
    case 'table':
      return <SkeletonTable {...props} />;
    case 'chart':
      return <SkeletonChart />;
    default:
      return <div className="skeleton" style={{ height: 20, ...props.style }} />;
  }
}
