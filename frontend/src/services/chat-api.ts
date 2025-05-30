import axios from "axios";

const API_BASE_URL = "http://localhost:7788";

export const AGENT_ID = "62f53991-0fec-4ff9-9b5c-ba1130d7bace";

export const chatApi = {
  createRun: async (task: string) => {
    const { data } = await axios.post(`${API_BASE_URL}/runs`, {
      agent_id: AGENT_ID,
      input: { task },
      metadata: {},
      config: {
        recursion_limit: 25,
        configurable: {},
      },
    });
    return data;
  },

  resumeRun: async (runId: string, payload?: any) => {
    const { data } = await axios.post(`${API_BASE_URL}/runs/${runId}`, payload);
    return data;
  },

  disableLearning: async () => {
    await axios.post(`${API_BASE_URL}/api/learning`, {
      learning_enabled: false,
    });
  },

  getStreamUrl: (runId: string) => {
    return `${API_BASE_URL}/runs/${runId}/stream`;
  },
};
