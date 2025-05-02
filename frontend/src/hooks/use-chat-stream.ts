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

    const events = new EventSource(chatApi.getStreamUrl(runId));

    events.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // Handle interrupts
      if (data.type === "interrupt") {
        setIsWaitingForApproval(true);
        const newMessage = transformSSEDataToMessage(data);
        if (newMessage) {
          addMessage(newMessage);
        }
        return;
      }

      // Ignore other messages while waiting for approval
      if (isWaitingForApproval) {
        return;
      }

      // Handle plan data first
      if (data.event === "planning" && data.data.plan) {
        setPlan(data.data.plan);
      }

      // Process messages
      const newMessage = transformSSEDataToMessage(data);
      if (newMessage) {
        addMessage(newMessage);
        // Reset approval state when we get a non-interrupt message
        setIsWaitingForApproval(false);
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
