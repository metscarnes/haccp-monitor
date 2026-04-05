/* global API client for HACCP Monitor */
const API = {
  baseUrl: '',
  
  async get(endpoint) {
    const res = await fetch(this.baseUrl + endpoint, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  
  async post(endpoint, data) {
    const res = await fetch(this.baseUrl + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  
  async getDashboard(boutiqueId = 1) {
    return this.get(`/api/boutiques/${boutiqueId}/dashboard`);
  },
  
  async getTasksToday() {
    return this.get('/api/taches/today');
  },
  
  async getDlcAlertes() {
    return this.get('/api/etiquettes/alertes-dlc');
  },
  
  async getReceptions(limit = 10) {
    return this.get(`/api/receptions?limit=${limit}`);
  },
  
  async ping() {
    try {
      await this.get('/api/boutiques/1');
      return { ok: true };
    } catch {
      return { ok: false };
    }
  }
};
