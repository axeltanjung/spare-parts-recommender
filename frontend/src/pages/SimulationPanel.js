import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
} from 'recharts';
import RecommendationCard from '../components/RecommendationCard';
import { simulateRecommendations } from '../api';

const MACHINE_TYPES = ['crusher', 'conveyor', 'pump', 'compressor', 'motor', 'turbine'];

function SimulationPanel() {
  const [temperature, setTemperature] = useState(75);
  const [vibration, setVibration] = useState(6.0);
  const [pressure, setPressure] = useState(150);
  const [machineType, setMachineType] = useState('pump');
  const [recommendations, setRecs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [inferenceTime, setInferenceTime] = useState(0);
  const [autoUpdate, setAutoUpdate] = useState(true);

  const fetchSimulation = useCallback(async () => {
    setLoading(true);
    try {
      const res = await simulateRecommendations(temperature, vibration, pressure, machineType, 5);
      setRecs(res.data.recommendations || []);
      setInferenceTime(res.data.inference_time_ms || 0);

      setHistory((prev) => {
        const next = [...prev, {
          time: prev.length + 1,
          temperature,
          vibration: vibration * 10,
          pressure: pressure / 3,
          topScore: Math.round(((res.data.recommendations || [])[0]?.score || 0) * 100),
        }];
        return next.slice(-20);
      });
    } catch {
      setRecs([]);
    } finally {
      setLoading(false);
    }
  }, [temperature, vibration, pressure, machineType]);

  useEffect(() => {
    if (autoUpdate) {
      const timer = setTimeout(fetchSimulation, 500);
      return () => clearTimeout(timer);
    }
  }, [temperature, vibration, pressure, machineType, autoUpdate, fetchSimulation]);

  const anomalyScore = Math.min(
    1,
    0.3 * Math.max(0, (temperature - 70) / 70) +
    0.4 * Math.max(0, (vibration - 5) / 10) +
    0.2 * Math.abs(pressure - 150) / 150
  );

  const riskLevel = anomalyScore > 0.6 ? 'HIGH' : anomalyScore > 0.3 ? 'MEDIUM' : 'LOW';
  const riskColor = { HIGH: 'var(--accent-red)', MEDIUM: 'var(--accent-amber)', LOW: 'var(--accent-green)' };

  const radarData = [
    { metric: 'Temp', value: Math.min((temperature / 200) * 100, 100) },
    { metric: 'Vibration', value: Math.min((vibration / 25) * 100, 100) },
    { metric: 'Pressure', value: Math.min((pressure / 500) * 100, 100) },
    { metric: 'Anomaly', value: anomalyScore * 100 },
    { metric: 'Risk', value: anomalyScore * 100 },
  ];

  return (
    <div>
      <div className="page-header">
        <h2>Sensor Simulation</h2>
        <p>Adjust sensor parameters to see real-time recommendation updates</p>
      </div>

      <div className="grid-2" style={{ marginBottom: '24px' }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Sensor Controls</span>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={autoUpdate}
                onChange={(e) => setAutoUpdate(e.target.checked)}
                style={{ accentColor: 'var(--accent-blue)' }}
              />
              Auto-update
            </label>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '500' }}>
              Machine Type
            </label>
            <div className="select-wrapper">
              <select value={machineType} onChange={(e) => setMachineType(e.target.value)}>
                {MACHINE_TYPES.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="slider-container">
            <div className="slider-label">
              <span>Temperature</span>
              <span>{temperature.toFixed(0)}°C</span>
            </div>
            <input
              type="range"
              min="20"
              max="200"
              step="1"
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
              style={{
                background: `linear-gradient(to right, #10b981 0%, #f59e0b 50%, #ef4444 100%)`
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              <span>20°C (Normal)</span>
              <span>200°C (Critical)</span>
            </div>
          </div>

          <div className="slider-container">
            <div className="slider-label">
              <span>Vibration</span>
              <span>{vibration.toFixed(1)} mm/s</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="25"
              step="0.1"
              value={vibration}
              onChange={(e) => setVibration(Number(e.target.value))}
              style={{
                background: `linear-gradient(to right, #10b981 0%, #f59e0b 50%, #ef4444 100%)`
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              <span>0.5 mm/s (Low)</span>
              <span>25 mm/s (Severe)</span>
            </div>
          </div>

          <div className="slider-container">
            <div className="slider-label">
              <span>Pressure</span>
              <span>{pressure.toFixed(0)} PSI</span>
            </div>
            <input
              type="range"
              min="10"
              max="500"
              step="1"
              value={pressure}
              onChange={(e) => setPressure(Number(e.target.value))}
              style={{
                background: `linear-gradient(to right, #3b82f6 0%, #10b981 30%, #10b981 70%, #ef4444 100%)`
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              <span>10 PSI</span>
              <span>500 PSI</span>
            </div>
          </div>

          {!autoUpdate && (
            <button
              className="nav-item active"
              style={{ width: '100%', justifyContent: 'center', padding: '12px', borderRadius: 'var(--radius-sm)', marginTop: '8px' }}
              onClick={fetchSimulation}
            >
              Run Simulation
            </button>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Risk Assessment</span>
            <span style={{ color: riskColor[riskLevel], fontWeight: '700', fontSize: '14px' }}>
              ● {riskLevel} RISK
            </span>
          </div>

          <div style={{ textAlign: 'center', marginBottom: '16px' }}>
            <div style={{
              width: '120px', height: '120px', borderRadius: '50%', margin: '0 auto',
              background: `conic-gradient(${riskColor[riskLevel]} ${anomalyScore * 360}deg, var(--bg-primary) 0deg)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <div style={{
                width: '90px', height: '90px', borderRadius: '50%',
                background: 'var(--bg-card)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexDirection: 'column'
              }}>
                <div style={{ fontSize: '24px', fontWeight: '700', color: riskColor[riskLevel] }}>
                  {(anomalyScore * 100).toFixed(0)}%
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Anomaly</div>
              </div>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Radar dataKey="value" stroke={riskColor[riskLevel]} fill={riskColor[riskLevel]} fillOpacity={0.2} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>

          {inferenceTime > 0 && (
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '8px' }}>
              Inference: {inferenceTime.toFixed(1)}ms
            </div>
          )}
        </div>
      </div>

      {history.length > 1 && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <span className="card-title">Simulation History</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Line type="monotone" dataKey="topScore" stroke="#3b82f6" strokeWidth={2} dot={false} name="Top Score" />
              <Line type="monotone" dataKey="temperature" stroke="#ef4444" strokeWidth={1} dot={false} name="Temp" />
              <Line type="monotone" dataKey="vibration" stroke="#f59e0b" strokeWidth={1} dot={false} name="Vib×10" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>
        Simulation Results
      </h3>

      {loading ? (
        <div className="loading-spinner"><div className="spinner" /></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '20px' }}>
          {recommendations.map((rec, i) => (
            <RecommendationCard key={rec.part_id} rec={rec} rank={i + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default SimulationPanel;
