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
import {
  GraphDataSSEMessage,
  InterruptSSEMessage,
} from "./../pages/session/types";
import { useEffect, useRef, useState } from "react";
import { useChatStore } from "@/stores/chat";
import { chatApi } from "@/services/chat-api";
import { transformSSEDataToMessage } from "@/utils/message-transformer";

export const useChatStream = () => {
  const [isWaitingForApproval, setIsWaitingForApproval] = useState(false);
  const [runId, setRunId] = useState("");
  const eventSourceRef = useRef<EventSource | null>(null);
  const { addMessage, setisThinking, isStopped, setIsStopped, setPlan } =
    useChatStore();

  const setupEventStream = (runId: string) => {
    // Clean up any existing stream
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    console.log("Setting up EventSource for", runId);

    const events = new EventSource(chatApi.getStreamUrl(runId));
    events.onopen = () => console.log("EventSource connection opened");

    // Handle default message events
    events.onmessage = (event) => {
      console.log("💾 SSE default message received:", event.data);
      try {
        const data = JSON.parse(event.data);
        handleEventData(data);
      } catch (error) {
        console.error("Error parsing default SSE message:", error);
      }
    };

    // Handle specific agent_event events
    events.addEventListener("agent_event", (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("💾 agent_event received:", data);
        handleEventData(data);
      } catch (error) {
        console.error("Error parsing agent_event:", error);
      }
    });

    // Common handler for both event types
    const handleEventData = (data: any) => {
      // Check if it's exiting
      if (data.exiting || data.values?.exiting) {
        console.log("Exiting flow detected, setting isThinking to false");
        setisThinking(false);
      }


      // Handle interrupts from WorkflowSrv
      if (data.type === "interrupt") {
        setIsWaitingForApproval(true);
        const newMessage = transformSSEDataToMessage(data);
        if (newMessage) {
          addMessage(newMessage);
        }
        return;
      }

      // This is the interrupt from human_approval node, formatted differently
      // due to WorkflowSrv requirements
      const interruptParse = InterruptSSEMessage.safeParse(data);
      if (interruptParse.success) {
        const interruptData = interruptParse.data.values;
        addMessage({
          role: "assistant",
          content: interruptData.message,
          toolCall: interruptData.tool_call,
          nodeType: "approval_request",
          messages: [],
        });
        setIsWaitingForApproval(true);
        return;
      }

      const graphDataParse = GraphDataSSEMessage.safeParse(data);
      if (!graphDataParse.success) {
        console.error("Failed to parse graph data:", graphDataParse.error);
        return;
      }

      const graphData = graphDataParse.data;

  // Only process if values exists, and access plan if values has expected properties in GraphData

  if (graphData.values) {
    if ('node_type' in graphData.values) {
      const plan = graphData.values.plan;
      if (plan) {
        console.log("Setting plan:", plan);
        setPlan(plan);
      }
    }

     // Only transform if it's a valid GraphData structure
    if ('node_type' in graphData.values) {
      const newMessage = transformSSEDataToMessage(graphData.values);
      if (newMessage) {
        console.log("Adding message:", newMessage);
        addMessage(newMessage);
        setIsWaitingForApproval(false);
      }
    }
  }
};

    events.onerror = (error) => {
      console.error("SSE Error:", error);
      eventSourceRef.current?.close();
      setisThinking(false);
    };

    eventSourceRef.current = events;
    return events;
  };

  const sendMessage = async (input: string) => {
    try {
      const run = await chatApi.createRun(input);
      setRunId(run.run_id);
      setupEventStream(run.run_id);

      addMessage({
        content: input,
        role: "user",
        messages: [],
      });
      setisThinking(true);
    } catch (error) {
      console.error("Failed:", error);
      setisThinking(false);
    }
  };

  const handleHitlConfirmation = async (approved: boolean) => {
    try {
      await chatApi.resumeRun(runId, {
        approved,
      });
      setupEventStream(runId);
      setIsWaitingForApproval(false);
      setisThinking(true);
    } catch (error) {
      console.error("Failed to resume run:", error);
      setisThinking(false);
    }
  };

  const stopTask = () => {
    if (isStopped) return;

    setIsStopped(true);
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setisThinking(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Disable learning on mount
  useEffect(() => {
    chatApi.disableLearning();
  }, []);

  return {
    sendMessage,
    handleHitlConfirmation,
    stopTask,
    isWaitingForApproval,
    isThinking: useChatStore((state) => state.isThinking),
    isStopped: useChatStore((state) => state.isStopped),
  };
};