import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

export async function analyzeInput(input) {
  const response = await axios.post(`${API_BASE}/analyze`, { input });
  return response.data;
}
