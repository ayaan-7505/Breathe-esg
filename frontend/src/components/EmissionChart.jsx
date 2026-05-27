import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from 'recharts';
import { SkeletonChart } from './LoadingSkeleton';
import './EmissionChart.css';

const SCOPE_COLORS = {
  'Scope 1': '#6366f1',
  'Scope 2': '#10b981',
  'Scope 3': '#f59e0b',
};

const SOURCE_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6'];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="chart-tooltip-value" style={{ color: entry.color }}>
          <span className="chart-tooltip-dot" style={{ background: entry.color }} />
          {entry.name}: {Number(entry.value).toLocaleString(undefined, { maximumFractionDigits: 1 })} tCO₂e
        </p>
      ))}
    </div>
  );
};

const PieTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-value" style={{ color: entry.payload.fill }}>
        <span className="chart-tooltip-dot" style={{ background: entry.payload.fill }} />
        {entry.name}: {Number(entry.value).toLocaleString(undefined, { maximumFractionDigits: 1 })} tCO₂e
      </p>
    </div>
  );
};

const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  if (percent < 0.05) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={12} fontWeight={600}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

export default function EmissionChart({ scopeData, sourceData, loading }) {
  if (loading) {
    return (
      <div className="charts-grid">
        <SkeletonChart />
        <SkeletonChart />
      </div>
    );
  }

  // Fallback data for demo
  const barData = scopeData?.length ? scopeData : [
    { month: 'Jan', 'Scope 1': 420, 'Scope 2': 310, 'Scope 3': 180 },
    { month: 'Feb', 'Scope 1': 380, 'Scope 2': 290, 'Scope 3': 210 },
    { month: 'Mar', 'Scope 1': 450, 'Scope 2': 340, 'Scope 3': 190 },
    { month: 'Apr', 'Scope 1': 390, 'Scope 2': 280, 'Scope 3': 220 },
    { month: 'May', 'Scope 1': 410, 'Scope 2': 320, 'Scope 3': 240 },
    { month: 'Jun', 'Scope 1': 360, 'Scope 2': 260, 'Scope 3': 200 },
  ];

  const pieData = sourceData?.length ? sourceData : [
    { name: 'SAP (Energy)', value: 4200, fill: SOURCE_COLORS[0] },
    { name: 'Utility Bills', value: 2800, fill: SOURCE_COLORS[1] },
    { name: 'Travel Records', value: 1600, fill: SOURCE_COLORS[2] },
    { name: 'Fleet Data', value: 900, fill: SOURCE_COLORS[3] },
  ];

  return (
    <div className="charts-grid">
      <div className="card chart-card">
        <div className="chart-header">
          <h3 className="chart-title">Emissions by Scope</h3>
          <span className="chart-subtitle">Monthly breakdown (tCO₂e)</span>
        </div>
        <div className="chart-body">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={barData} barGap={2} barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="month"
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99,102,241,0.05)' }} />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              />
              {Object.entries(SCOPE_COLORS).map(([key, color]) => (
                <Bar key={key} dataKey={key} fill={color} radius={[4, 4, 0, 0]} maxBarSize={40} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card chart-card">
        <div className="chart-header">
          <h3 className="chart-title">By Source Type</h3>
          <span className="chart-subtitle">Distribution of emissions</span>
        </div>
        <div className="chart-body">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={110}
                paddingAngle={3}
                dataKey="value"
                labelLine={false}
                label={renderCustomLabel}
                stroke="var(--bg-card)"
                strokeWidth={2}
              >
                {pieData.map((entry, index) => (
                  <Cell key={index} fill={entry.fill || SOURCE_COLORS[index % SOURCE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<PieTooltip />} />
              <Legend
                iconType="circle"
                iconSize={8}
                layout="vertical"
                align="right"
                verticalAlign="middle"
                wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
