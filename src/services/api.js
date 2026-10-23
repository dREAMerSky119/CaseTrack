import { demoComplaints, demoInstitutions, demoUser } from "../data/demoData";

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE !== "false";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";
let demoCases = [...demoComplaints];
let demoOrgs = [...demoInstitutions];

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.message || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  async getCurrentUser() {
    if (DEMO_MODE) return demoUser;
    return request("/auth/me");
  },
  async login(email, password, displayName = "") {
    if (DEMO_MODE) {
      const fallbackName = (email.split("@")[0] || "Demo User").replace(/[._-]+/g, " ").replace(/\b\w/g, char => char.toUpperCase());
      const name = displayName || fallbackName;
      const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0].toUpperCase()).join("") || "DU";
      return { ...demoUser, name, initials, email, demo: true };
    }
    return request("/auth/login", { method: "POST", body: JSON.stringify({ email, password, displayName }) });
  },
  async logout() {
    if (!DEMO_MODE) await request("/auth/logout", { method: "POST" });
  },
  async getComplaints() {
    if (DEMO_MODE) return [...demoCases];
    return request("/complaints");
  },
  async getComplaint(id) {
    if (DEMO_MODE) return demoCases.find((item) => item.id === id) || null;
    return request(`/complaints/${id}`);
  },
  async createComplaint(payload) {
    if (DEMO_MODE) {
      const record = { ...payload, id: `CT-${Date.now().toString().slice(-5)}`, score: 35, related: false, updated: payload.received };
      demoCases = [record, ...demoCases];
      return record;
    }
    return request("/complaints", { method: "POST", body: JSON.stringify(payload) });
  },
  async updateComplaint(id, payload) {
    if (DEMO_MODE) {
      demoCases = demoCases.map((item) => item.id === id ? { ...item, ...payload, updated: new Date().toISOString().slice(0, 10) } : item);
      return demoCases.find((item) => item.id === id);
    }
    return request(`/complaints/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
  },
  async getInstitutions() {
    if (DEMO_MODE) return [...demoOrgs];
    return request("/institutions");
  },
  async createInstitution(payload) {
    if (DEMO_MODE) {
      const record = { ...payload, complaints: 0 };
      demoOrgs = [record, ...demoOrgs];
      return record;
    }
    return request("/institutions", { method: "POST", body: JSON.stringify(payload) });
  }
};

export { DEMO_MODE };
