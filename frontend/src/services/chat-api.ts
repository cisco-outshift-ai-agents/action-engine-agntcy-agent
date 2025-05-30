/*
# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0"
*/
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
