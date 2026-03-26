import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

export const getHealth = () => api.get('/health');
export const getMachines = () => api.get('/machines');
export const getMachine = (machineId) => api.get(`/machines/${machineId}`);
export const getParts = () => api.get('/parts');
export const getMetrics = () => api.get('/metrics');

export const getRecommendations = (machineId, n = 5) =>
  api.post('/recommend', { machine_id: machineId, n, include_explanation: true });

export const simulateRecommendations = (temperature, vibration, pressure, machineType = 'pump', n = 5) =>
  api.post('/simulate', {
    temperature,
    vibration,
    pressure,
    machine_type: machineType,
    n,
    include_explanation: true,
  });

export default api;
