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
# SPDX-License-Identifier: Apache-2.0
*/
import { twMerge } from "tailwind-merge";
import { type ClassValue, clsx } from "clsx";
import { GraphData } from "./pages/session/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const extractHostname = (summary: string): string => {
  const match = summary.match(/^(\S+@\S+):/);
  return match ? match[1] : "default-hostname";
};

export const getLastToolCallAIMessage = (
  messages: GraphData["messages"]
): GraphData["messages"][number] | undefined => {
  const lastAIMessage = messages
    .filter((m) => m.type === "AIMessage" && m.tool_calls?.length)
    .pop();

  return lastAIMessage;
};

export const getLastToolMessage = (
  messages: GraphData["messages"]
): GraphData["messages"][number] | undefined => {
  const lastToolMessage = messages
    .filter((m) => m.type === "ToolMessage")
    .pop();

  return lastToolMessage;
};
