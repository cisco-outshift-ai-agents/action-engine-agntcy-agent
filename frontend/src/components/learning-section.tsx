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
import React, { useState, useEffect, useRef } from "react";
import useSWR from "swr";
import { LTOEvent, LTOEventZod } from "@/types";
import { Plan, PlanZod } from "@/pages/session/types";
import PlanRenderer from "./plan-renderer";
import { Loader2Icon } from "lucide-react";

const LearningSection: React.FC = () => {
  const [events, setEvents] = useState<LTOEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const getWsRef = useRef<WebSocket | null>(null);
  const reconnectIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const { data, error, isLoading } = useSWR<{
    plan: Plan;
  }>(
    "http://localhost:7788/api/event-log/analyze",
    async (url) => {
      const response = await fetch(url, {
        method: "POST",
      });
      const data = await response.json();
      return data;
    },
    {
      refreshInterval: 10000,
      revalidateOnMount: true,
    }
  );

  const connectWebSocket = () => {
    const getWs = new WebSocket(`ws://localhost:7788/ws/get-events`);
    getWsRef.current = getWs;

    getWs.onopen = () => {
      setIsConnected(true);
      console.log("Connected to LTO events socket");
      if (reconnectIntervalRef.current) {
        clearInterval(reconnectIntervalRef.current);
        reconnectIntervalRef.current = null;
      }
    };

    getWs.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        const newEvents = Array.isArray(data) ? data : [data];

        const parsedEvents = newEvents
          .map((event) => {
            const safeParse = LTOEventZod.safeParse(
              typeof event === "string" ? JSON.parse(event) : event
            );

            if (!safeParse.success) {
              console.error("Failed to parse event:", safeParse.error);
            }

            return safeParse.success ? safeParse.data : null;
          })
          .filter((event): event is LTOEvent => event !== null);

        setEvents(parsedEvents);
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    getWs.onclose = () => {
      setIsConnected(false);
      console.log("Disconnected from get events server");
      if (!reconnectIntervalRef.current) {
        reconnectIntervalRef.current = setInterval(connectWebSocket, 5000);
      }
    };
  };

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (getWsRef.current) {
        getWsRef.current.close();
      }
      if (reconnectIntervalRef.current) {
        clearInterval(reconnectIntervalRef.current);
      }
    };
  }, []);

  const formatEvent = (data: LTOEvent) => {
    return `${data.operation?.original_op}: ${data.operation?.target} ${data.operation?.value} [pos_candidates: ${data.pos_candidates?.length}]`;
  };

  const enableLearning = async () => {
    await fetch(`http://localhost:7788/api/learning`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        learning_enabled: true,
      }),
    });
  };

  useEffect(() => {
    enableLearning();
  }, []);

  useEffect(() => {
    const safeParse = PlanZod.safeParse(data?.plan);
    if (!safeParse.success) {
      console.error("Failed to parse plan:", safeParse.error);
      return;
    }
    if (data) {
      setPlan(data?.plan);
    }
  }, [data]);

  return (
    <div className="h-full rounded-lg  bg-[#32363c] w-full px-2 py-4 flex flex-col border-white/10 border">
      <div className="flex items-center justify-end w-full mb-1">
        <div className="flex items-center">
          <div>
            <div
              className={`rounded-full aspect-square h-2 w-2 ${
                isConnected ? "bg-green-500" : "bg-red-500"
              }`}
            />
          </div>
          <p className="ml-2 text-xs text-white font-semibold">
            {isConnected
              ? "Connected to LTO events socket"
              : "Disconnected from LTO events socket"}
          </p>
        </div>
      </div>
      <div className="flex-1 overflow-hidden text-white text-sm flex flex-col gap-1">
        <span>
          {events.length} event{events.length !== 1 && "s"} received
        </span>
        <div className="flex flex-col h-full overflow-auto p-4 bg-gray-800 rounded text-xs max-h-[150px]">
          {events.map((event) => (
            <code>{formatEvent(event)}</code>
          ))}
        </div>
        {/* <button
          onClick={analyzeEventLog}
          disabled={isAnalyzing}
          className={
            "flex gap-2 text-sm items-center rounded-lg px-2 py-1 cursor-pointer border-2 border-white/10 bg-white/10 hover:bg-white/20 text-white font-medium"
          }
        >
          {isAnalyzing ? "Analyzing..." : "Analyze Event Log"}
        </button> */}
        <div className="h-3">
          {isLoading && <Loader2Icon className="w-4 h-4 animate-spin" />}
        </div>

        {plan ? (
          <PlanRenderer plan={plan} />
        ) : (
          <span className="my-2 font-medium px-4 py-3 block text-center border border-white/10 rounded-lg">
            No plan available
          </span>
        )}
      </div>
    </div>
  );
};

export default LearningSection;
