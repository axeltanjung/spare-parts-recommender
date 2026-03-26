import React, { useState } from 'react';

function RecommendationCard({ rec, rank }) {
  const [expanded, setExpanded] = useState(false);

  const scorePercent = Math.round((rec.score || 0) * 100);
  const cfPercent = Math.round((rec.cf_score || 0) * 100);
  const cbPercent = Math.round((rec.cb_score || 0) * 100);
  const shapData = rec.shap_explanation || {};
  const featureContributions = shapData.feature_contributions || {};
  const topReasons = shapData.top_reasons || [];
  const explanation = rec.explanation || {};

  const critBadge = {
    high: 'badge-high',
    medium: 'badge-medium',
    low: 'badge-low',
  };

  return (
    <div className="rec-card" onClick={() => setExpanded(!expanded)}>
      <div className="rec-card-header">
        <div>
          <div className="rec-card-id">{rec.part_id}</div>
          <div className="rec-card-name">{rec.part_name || rec.part_id}</div>
          <div className="rec-card-category">{rec.category}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '28px', fontWeight: '700', color: 'var(--accent-cyan)' }}>
            #{rank}
          </div>
          <span className={`badge ${critBadge[rec.criticality] || 'badge-medium'}`}>
            {rec.criticality}
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px' }}>
        <span>Score</span>
        <span style={{ color: 'var(--accent-blue)', fontWeight: '600' }}>{scorePercent}%</span>
      </div>
      <div className="score-bar">
        <div className="score-bar-fill" style={{ width: `${scorePercent}%` }} />
      </div>

      <div className="score-breakdown">
        <div className="score-item">
          <div className="score-item-label">Collaborative</div>
          <div className="score-item-value" style={{ color: 'var(--accent-purple)' }}>{cfPercent}%</div>
        </div>
        <div className="score-item">
          <div className="score-item-label">Content</div>
          <div className="score-item-value" style={{ color: 'var(--accent-cyan)' }}>{cbPercent}%</div>
        </div>
        <div className="score-item">
          <div className="score-item-label">Cost</div>
          <div className="score-item-value" style={{ color: 'var(--accent-green)' }}>
            {rec.cost_usd ? `$${Math.round(rec.cost_usd)}` : 'N/A'}
          </div>
        </div>
        <div className="score-item">
          <div className="score-item-label">Lead Time</div>
          <div className="score-item-value" style={{ color: 'var(--accent-amber)' }}>
            {rec.lead_time_days}d
          </div>
        </div>
      </div>

      {explanation.reason && (
        <div style={{ marginTop: '12px', padding: '8px 12px', background: 'var(--bg-primary)', borderRadius: 'var(--radius-sm)', fontSize: '13px', color: 'var(--text-secondary)' }}>
          {explanation.reason}
        </div>
      )}

      {expanded && (
        <div className="explanation-section">
          <div className="explanation-title">Feature Contributions (SHAP)</div>

          {Object.entries(featureContributions).length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              {Object.entries(featureContributions)
                .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
                .map(([feature, value]) => {
                  const maxVal = 0.25;
                  const pct = Math.min(Math.abs(value) / maxVal * 50, 50);
                  return (
                    <div className="feature-bar" key={feature}>
                      <div className="feature-bar-name">{feature.replace(/_/g, ' ')}</div>
                      <div className="feature-bar-track">
                        <div className="feature-bar-center" />
                        {value >= 0 ? (
                          <div className="feature-bar-positive" style={{ width: `${pct}%` }} />
                        ) : (
                          <div className="feature-bar-negative" style={{ width: `${pct}%` }} />
                        )}
                      </div>
                    </div>
                  );
                })}
            </div>
          )}

          {topReasons.length > 0 && (
            <div>
              <div className="explanation-title">Key Reasons</div>
              {topReasons.map((reason, i) => (
                <div className="reason-item" key={i}>
                  <span className={`reason-dot ${reason.direction === 'increases' ? 'positive' : 'negative'}`} />
                  <span>{reason.description}</span>
                </div>
              ))}
            </div>
          )}

          {shapData.summary && (
            <div style={{ marginTop: '12px', padding: '10px 14px', background: 'rgba(59,130,246,0.1)', borderRadius: 'var(--radius-sm)', fontSize: '13px', color: 'var(--accent-blue)', borderLeft: '3px solid var(--accent-blue)' }}>
              {shapData.summary}
            </div>
          )}

          {explanation.weighting_logic && (
            <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
              {explanation.weighting_logic}
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: '12px', textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
        {expanded ? 'Click to collapse' : 'Click to expand explanation'}
      </div>
    </div>
  );
}

export default RecommendationCard;
