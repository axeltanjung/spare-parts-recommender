import React, { useState, useEffect, useCallback } from 'react';
import RecommendationCard from '../components/RecommendationCard';
import { getMachines, getRecommendations } from '../api';

function RecommendationView() {
  const [machines, setMachines] = useState([]);
  const [selectedMachine, setSelectedMachine] = useState('');
  const [recommendations, setRecs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [numRecs, setNumRecs] = useState(5);
  const [inferenceTime, setInferenceTime] = useState(0);

  useEffect(() => {
    getMachines().then((res) => {
      const m = res.data.machines || [];
      setMachines(m);
      if (m.length > 0) setSelectedMachine(m[0].machine_id);
    }).catch(() => {});
  }, []);

  const fetchRecs = useCallback(async () => {
    if (!selectedMachine) return;
    setLoading(true);
    try {
      const res = await getRecommendations(selectedMachine, numRecs);
      setRecs(res.data.recommendations || []);
      setInferenceTime(res.data.inference_time_ms || 0);
    } catch {
      setRecs([]);
    } finally {
      setLoading(false);
    }
  }, [selectedMachine, numRecs]);

  useEffect(() => {
    fetchRecs();
  }, [fetchRecs]);

  return (
    <div>
      <div className="page-header">
        <h2>Spare Part Recommendations</h2>
        <p>AI-powered part suggestions based on collaborative filtering and content analysis</p>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '500' }}>
              Select Machine
            </label>
            <div className="select-wrapper">
              <select value={selectedMachine} onChange={(e) => setSelectedMachine(e.target.value)}>
                {machines.map((m) => (
                  <option key={m.machine_id} value={m.machine_id}>
                    {m.machine_id} — {m.machine_type} ({m.location})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ minWidth: '120px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '500' }}>
              Results
            </label>
            <div className="select-wrapper">
              <select value={numRecs} onChange={(e) => setNumRecs(Number(e.target.value))}>
                {[3, 5, 10, 15, 20].map((n) => (
                  <option key={n} value={n}>{n} parts</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ minWidth: '120px' }}>
            <button
              className="nav-item active"
              style={{ width: 'auto', padding: '10px 24px', borderRadius: 'var(--radius-sm)', fontSize: '14px' }}
              onClick={fetchRecs}
            >
              Get Recommendations
            </button>
          </div>
        </div>

        {inferenceTime > 0 && (
          <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
            Inference time: {inferenceTime.toFixed(1)}ms | {recommendations.length} results
          </div>
        )}
      </div>

      {loading ? (
        <div className="loading-spinner"><div className="spinner" /></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '20px' }}>
          {recommendations.map((rec, i) => (
            <RecommendationCard key={rec.part_id} rec={rec} rank={i + 1} />
          ))}
        </div>
      )}

      {!loading && recommendations.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>&#9881;</div>
          <div style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>No Recommendations</div>
          <div style={{ color: 'var(--text-muted)' }}>Select a machine and click "Get Recommendations"</div>
        </div>
      )}
    </div>
  );
}

export default RecommendationView;
