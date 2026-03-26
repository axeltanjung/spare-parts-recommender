import React from 'react';

function MetricCard({ title, value, unit, icon, color }) {
  const gradients = {
    blue: 'var(--gradient-blue)',
    green: 'var(--gradient-green)',
    amber: 'var(--gradient-amber)',
    purple: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
  };

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">{title}</span>
        <span style={{ fontSize: '24px' }}>{icon}</span>
      </div>
      <div>
        <span
          className="metric-value"
          style={{ background: gradients[color] || gradients.blue, WebkitBackgroundClip: 'text', backgroundClip: 'text' }}
        >
          {value}
        </span>
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
    </div>
  );
}

export default MetricCard;
