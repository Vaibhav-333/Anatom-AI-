import axios from "axios";

const api = axios.create({ baseURL: "/api", timeout: 60000 });

export const lifestyleApi = {
  generatePlan: (payload: object) =>
    api.post("/lifestyle/generate", payload),
  getLatestPlan: (userId: string) =>
    api.get(`/lifestyle/${userId}/latest`),
  getPlanHistory: (userId: string, limit = 7) =>
    api.get(`/lifestyle/${userId}/history`, { params: { limit } }),
  getRecommendations: (userId: string) =>
    api.get(`/lifestyle/${userId}/recommendations`),
  sharePlan: (payload: object) =>
    api.post("/lifestyle/share", payload),
  getSharedPlan: (token: string) =>
    api.get(`/lifestyle/share/${token}`),
};
