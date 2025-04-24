import React, { useState, useEffect, useRef } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { Button } from "./ui/button";
import { SendHorizontal, StopCircle } from "lucide-react";
import { cn } from "@/utils";

import ChatMessage, {
  ChatMessageProps,
  NodeType,
} from "./chat/chat-components/chat-message";
import CiscoAIAssistantLoader from "@/components/chat/chat-assets/thinking.gif";

import { TodoFixAny } from "@/types";
import { useChatStore } from "@/stores/chat";
import {
  GraphData,
  GraphDataZod,
  NodeUpdateZod,
  StopDataZod,
} from "@/pages/session/types";
import PlanRenderer from "./plan-renderer";

interface ChatSectionProps {
  className?: string;
  onTerminalUpdate?: (
    content: string,
    isTerminal: boolean,
    hasEmptyThought: boolean,
    isDone: boolean,
    terminalId: string,
    workingDirectory: string
  ) => void;
}

const ChatSection: React.FC<ChatSectionProps> = () => {
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null); //Main websocket for tasks
  const wsStopRef = useRef<WebSocket | null>(null); //Websocket for stop requests
  const bottomOfChatRef = useRef<HTMLDivElement | null>(null);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const {
    messages,
    addMessage,
    isThinking,
    setisThinking,
    isStopped,
    setIsStopped,
    plan,
    setPlan,
  } = useChatStore();

  const connectWebSocket = () => {
    const useLocal = true;
    const url = useLocal ? "localhost:7788" : window.location.host;
    const ws = new WebSocket(`ws://${url}/ws/chat`);
    wsRef.current = ws;
    window.wsRef = wsRef;
    //Websocket for stop requests
    const wsStop = new WebSocket(`ws://${url}/ws/stop`);

    wsStopRef.current = wsStop;

    ws.onopen = () => {
      setIsConnected(true);
      console.log("Connected to chat server");
    };

    ws.onmessage = (event: MessageEvent) => {
      console.log("received websocket message:", JSON.parse(event.data));
      const data = JSON.parse((event as TodoFixAny).data);

      if (data.type === "approval_request") {
        const { message, tool_call } = data.data;

        addMessage({
          content: message,
          role: "assistant",
          nodeType: "approval_request",
          toolCall: tool_call,
        });

        return;
      }

      // Check if this is an error message
      if (data.error) {
        addMessage({
          content: data.error,
          role: "assistant",
          error: data.error,
        });
        setisThinking(false);
        return;
      }

      // Check if this is a node-specific update
      const parseNodeUpdate = NodeUpdateZod.safeParse(data);
      if (parseNodeUpdate.success) {
        const update = parseNodeUpdate.data;

        if (update.thinking) {
          const cleanedData = cleanAPIData(update.thinking, "thinking");
          addMessage(cleanedData);
        }

        if (update.planning) {
          const plan = getPlanFromMessage(update.planning);
          if (plan) setPlan(plan);
        }

        if (update.executor) {
          const cleanedData = cleanAPIData(update.executor, "executor");
          if (cleanedData.actions?.length) {
            addMessage(cleanedData);
          }
        }

        // Check if any node signals completion
        if (
          (update.thinking?.exiting || update.executor?.exiting) &&
          !update.planning
        ) {
          setisThinking(false);
        }

        return;
      }

      // Fall back to handling legacy format
      const parseGraphData = GraphDataZod.safeParse(data);
      if (!parseGraphData.success) {
        console.error(parseGraphData.error);
        return;
      }

      // Check if this is a stop response
      if (data.stopped !== undefined) {
        const parse = StopDataZod.safeParse(data);
        if (parse.success) {
          const stopResponse = parse.data;
          if (stopResponse.stopped) {
            setisThinking(false);
            setIsStopped(false);
          }
          addMessage({
            content: stopResponse.summary,
            role: "assistant",
          });
          return;
        }
      }

      const cleanedData = cleanAPIData(parseGraphData.data);
      addMessage(cleanedData);

      if (cleanedData.isDone) {
        setisThinking(false);
      }

      const plan = getPlanFromMessage(parseGraphData.data);
      if (plan) {
        setPlan(plan);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log("Disconnected from chat server");
    };

    wsRef.current = ws;
  };

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const sendMessage = () => {
    if (!wsRef.current) {
      return;
    }

    const payload = {
      task: input,
    };

    wsRef.current.send(JSON.stringify(payload));
    addMessage({
      content: input,
      role: "user",
    });

    setInput("");
    setisThinking(true);
  };

  const stopTask = () => {
    if (!wsRef.current || isStopped) {
      return;
    }

    setIsStopped(true);

    wsRef.current.send(JSON.stringify({ task: "stop" }));
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const cleanAPIData = (
    data: GraphData,
    nodeType?: NodeType
  ): ChatMessageProps => {
    if (nodeType === "executor") {
      return {
        role: "assistant",
        content: null, // We don't need content for executor, just actions
        actions: getLastAITools(data),
        error: data.error,
        isDone: data.exiting,
        nodeType,
      };
    }

    if (nodeType === "planning") {
      return {
        role: "assistant",
        content: null, // Planning node just shows "Updating plan..."
        error: data.error,
        isDone: data.exiting,
        nodeType,
      };
    }

    // For thinking and other nodes, show conversational UI
    return {
      role: "assistant",
      content: data.brain.summary,
      thought: data.brain.thought,
      error: data.error,
      isDone: data.exiting,
      nodeType,
    };
  };

  const getPlanFromMessage = (
    data: GraphData
  ): NonNullable<GraphData["plan"]> | null => {
    if (!data.plan) {
      return null;
    }
    return data.plan;
  };

  const scrollToBottom = () => {
    if (bottomOfChatRef.current && chatContainerRef.current) {
      bottomOfChatRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  const disableLearning = async () => {
    await fetch(`http://localhost:7788/api/learning`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        learning_enabled: false,
      }),
    });
  };

  useEffect(() => {
    disableLearning();
  }, []);

  return (
    <div className="h-[95%] rounded-lg  bg-[#32363c] w-full px-2 py-4 flex flex-col border-white/10 border">
      <div className="flex items-center justify-end">
        <div
          className={`rounded-full aspect-square h-2 w-2 ${
            isConnected ? "bg-green-500" : "bg-red-500"
          }`}
        />
        <p className="ml-2 text-xs text-white font-semibold">
          {isConnected
            ? "Connected to chat socket"
            : "Disconnected from chat socket"}
        </p>
      </div>
      <PlanRenderer plan={plan} />
      <div
        className="flex-1 overflow-y-auto px-2 pt-2 pb-3"
        ref={chatContainerRef}
      >
        <div className="flex flex-col gap-4 space-y-reverse">
          {[...messages].map((message, index) => (
            <div key={index}>
              <ChatMessage {...message} />
            </div>
          ))}
          {isThinking && (
            <div className="flex items-start px-2 py-2">
              <img
                src={CiscoAIAssistantLoader}
                alt="outshift-logo"
                width={36}
                className="mr-3 "
              />
            </div>
          )}
        </div>
        <div ref={bottomOfChatRef}></div>
      </div>
      <div className="px-4 pt-2 pb-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!isThinking) sendMessage();
          }}
          className={cn(
            "max-w-3xl mx-auto bg-[#373c42] border-2 border-[#7E868F] pr-3 pt-2 pl-5 pb-2 rounded-lg",
            "group focus-within:border-[#649EF5] flex items-center"
          )}
        >
          <TextareaAutosize
            tabIndex={1}
            minRows={1}
            maxRows={8}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="What do you want ActionEngine to do?"
            className={cn(
              "w-full bg-transparent text-white font-normal text-base leading-[22px] placeholder:text-[#889099] placeholder:text-sm focus:ring-0 focus:border-0 focus:outline-none resize-none"
            )}
            wrap="hard"
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.shiftKey) return;
              if (e.key === "Enter" && !isThinking) {
                e.preventDefault();
                sendMessage();
              } else if (e.key === "Enter" && isThinking) {
                e.preventDefault();
              }
            }}
          />
          <Button
            type="button"
            variant="ghost"
            className="p-1 hover:opacity-80"
            onClick={isThinking ? stopTask : sendMessage}
            disabled={isThinking && isStopped}
          >
            {isThinking ? (
              <StopCircle className="w-[18.83px] h-[20.73px] text-[#649EF5]" />
            ) : (
              <SendHorizontal className="w-[18.83px] h-[20.73px] text-[#649EF5]" />
            )}
          </Button>
        </form>
        <div className="text-center mt-2 text-xs text-[#D0D4D9]">
          Assistant can make mistakes. Verify responses.
        </div>
      </div>
    </div>
  );
};

const getLastAITools = (data: GraphData): string[] => {
  const lastAIMessage = data.messages
    .filter((m) => m.type === "AIMessage")
    .pop();

  if (!lastAIMessage) {
    return [];
  }

  return [
    ...(lastAIMessage.tool_calls?.map((t) => {
      return JSON.stringify(t);
    }) || []),
    lastAIMessage.content || "",
  ].filter((a) => !!a);
};

export default ChatSection;
