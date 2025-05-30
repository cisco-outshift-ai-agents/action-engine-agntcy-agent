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
import { ChatMessageProps } from "@/components/chat/chat-components/chat-message";
import { GraphData } from "@/pages/session/types";
import { data } from "react-router-dom";

export const transformSSEDataToMessage = (
  graphData: GraphData | undefined
): ChatMessageProps | undefined => {
  console.log("💾 Transforming SSE data to message:", data);

  if (!graphData) {
    console.error("Graph data is missing in the parsed SSE data.");
    return undefined;
  }

  const nodeType = graphData.node_type;
  const messages = graphData.messages || [];

  if (nodeType === "executor") {
    return {
      role: "assistant",
      content: null,
      error: graphData.error,
      nodeType,
      messages,
    };
  }

  if (nodeType === "thinking") {
    return {
      role: "assistant",
      content: graphData.brain.summary,
      thought: graphData.brain.thought,
      error: graphData.error,
      nodeType,
      messages,
    };
  }

  if (nodeType === "planning") {
    return {
      role: "assistant",
      content: graphData.brain.summary,
      nodeType,
      messages,
    };
  }

  return undefined;
};
