import React, { useState, useEffect, useCallback } from 'react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import MetricCard from '../components/MetricCard';
import RecommendationCard from '../components/RecommendationCard';
import { getMachines, getMachine, getRecommendations, getHealth } from '../api';

const CHART_COLORS = ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444'];

function Dashboard({ onNavigate }) {
  const [machines, setMachines] = useState([]);
  const [selectedMachine, setSelectedMachine] = useState('');
  const [machineInfo, setMachineInfo] = useState(null);
  const [recommendations, setRecs] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const init = async () => {
      try {
        const [mRes, hRes] = await Promise.all([getMachines(), getHealth()]);
        setMachines(mRes.data.machines || []);
        setHealth(hRes.data);
        if (mRes.data.machines?.length > 0) {
          setSelectedMachine(mRes.data.machines[0].machine_id);
        }
      } catch (err) {
        setError('Failed to connect to backend. Ensure server is running.');
      }
    };
    init();
  }, []);

  const fetchMachineData = useCallback(async (mid) => {
    if (!mid) return;
    setLoading(true);
    setError(null);
    try {
      const [mRes, rRes] = await Promise.all([
        getMachine(mid),
        getRecommendations(mid, 5),
      ]);
      setMachineInfo(mRes.data);
      setRecs(rRes.data.recommendations || []);
    } catch (err) {
      setError('Failed to fetch machine data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedMachine) fetchMachineData(selectedMachine);
  }, [selectedMachine, fetchMachineData]);

  const sensor = machineInfo?.sensor_data || {};

  const radarData = [
    { subject: 'Temperature', value: Math.min((sensor.avg_temperature || 0) / 2, 100), fullMark: 100 },
    { subject: 'Vibration', value: Math.min((sensor.avg_vibration || 0) * 10, 100), fullMark: 100 },
    { subject: 'Pressure', value: Math.min((sensor.avg_pressure || 0) / 3, 100), fullMark: 100 },
    { subject: 'Anomaly', value: (sensor.max_anomaly || 0) * 100, fullMark: 100 },
    { subject: 'Usage', value: Math.min(((machineInfo?.usage_hours_per_day || 0) / 24) * 100, 100), fullMark: 100 },
    { subject: 'Age', value: Math.min(((machineInfo?.age_years || 0) / 20) * 100, 100), fullMark: 100 },
  ];

  const recBarData = recommendations.map((r) => ({
    name: r.part_name || r.part_id,
    score: Math.round((r.score || 0) * 100),
    cf: Math.round((r.cf_contribution || 0) * 100),
    cb: Math.round((r.cb_contribution || 0) * 100),
  }));

  const categoryData = recommendations.reduce((acc, r) => {
    const cat = r.category || 'other';
    const existing = acc.find((x) => x.name === cat);
    if (existing) existing.value += 1;
    else acc.push({ name: cat, value: 1 });
    return acc;
  }, []);

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Real-time machine monitoring and spare parts intelligence</p>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <div className="select-wrapper" style={{ maxWidth: '400px' }}>
          <select
            value={selectedMachine}
            onChange={(e) => setSelectedMachine(e.target.value)}
          >
            {machines.map((m) => (
              <option key={m.machine_id} value={m.machine_id}>
                {m.machine_id} — {m.machine_type} ({m.location})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div style={{ padding: '16px', background: 'rgba(239,68,68,0.1)', border: '1px solid var(--accent-red)', borderRadius: 'var(--radius-sm)', marginBottom: '20px', color: 'var(--accent-red)', fontSize: '14px' }}>
          {error}
        </div>
      )}

      <div className="grid-4" style={{ marginBottom: '24px' }}>
        <MetricCard
          title="Temperature"
          value={sensor.avg_temperature?.toFixed(1) || '—'}
          unit="°C"
          icon="🌡"
          color={sensor.avg_temperature > 80 ? 'amber' : 'blue'}
        />
        <MetricCard
          title="Vibration"
          value={sensor.avg_vibration?.toFixed(1) || '—'}
          unit="mm/s"
          icon="📳"
          color={sensor.avg_vibration > 8 ? 'amber' : 'green'}
        />
        <MetricCard
          title="Pressure"
          value={sensor.avg_pressure?.toFixed(0) || '—'}
          unit="PSI"
          icon="🔵"
          color="blue"
        />
        <MetricCard
          title="Anomaly Score"
          value={sensor.max_anomaly?.toFixed(2) || '—'}
          unit=""
          icon="⚠"
          color={sensor.max_anomaly > 0.5 ? 'amber' : 'green'}
        />
      </div>

      {loading ? (
        <div className="loading-spinner"><div className="spinner" /></div>
      ) : (
        <>
          <div className="grid-2" style={{ marginBottom: '24px' }}>
            <div className="card">
              <div className="card-header">
                <span className="card-title">Machine Health Profile</span>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#334155" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <PolarRadiusAxis tick={false} axisLine={false} />
                  <Radar
                    name="Machine"
                    dataKey="value"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.25}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Score Breakdown</span>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={recBarData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={100} />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '13px' }}
                    labelStyle={{ color: '#f1f5f9' }}
                  />
                  <Bar dataKey="cf" stackId="a" fill="#8b5cf6" name="Collaborative" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="cb" stackId="a" fill="#06b6d4" name="Content-Based" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid-2" style={{ marginBottom: '24px' }}>
            <div className="card">
              <div className="card-header">
                <span className="card-title">Machine Details</span>
              </div>
              {machineInfo && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {[
                    ['Machine ID', machineInfo.machine_id],
                    ['Type', machineInfo.machine_type],
                    ['Age', `${machineInfo.age_years || 'N/A'} years`],
                    ['Location', machineInfo.location],
                    ['Usage', `${machineInfo.usage_hours_per_day} hrs/day`],
                    ['Maintenance Events', machineInfo.total_maintenance_events],
                    ['Avg Downtime', `${machineInfo.avg_downtime?.toFixed(1) || '0'} hrs`],
                  ].map(([label, val]) => (
                    <div key={label} style={{ padding: '10px', background: 'var(--bg-primary)', borderRadius: 'var(--radius-sm)' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>{label}</div>
                      <div style={{ fontSize: '14px', fontWeight: '600' }}>{val}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Part Categories</span>
              </div>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {categoryData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '600' }}>Top Recommendations</h3>
              <button
                className="nav-item"
                style={{ width: 'auto', color: 'var(--accent-blue)' }}
                onClick={() => onNavigate('recommendations')}
              >
                View All →
              </button>
            </div>
          </div>

          <div className="grid-3">
            {recommendations.slice(0, 3).map((rec, i) => (
              <RecommendationCard key={rec.part_id} rec={rec} rank={i + 1} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;
