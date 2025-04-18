import React, { useState, useEffect, useRef } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { PaperPlaneRight, StopCircle } from "@magnetic/icons";
import { Button } from "@magnetic/button";
import { cn } from "@/utils";
import { Flex } from "@magnetic/flex";
import ChatMessage, {
  ChatMessageProps,
  NodeType,
} from "./newsroom/newsroom-components/chat-message";
import CiscoAIAssistantLoader from "@/components/newsroom/newsroom-assets/thinking.gif";

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
    setPlan,
  } = useChatStore();

  useEffect(() => {
    const useLocal = true;
    const url = useLocal ? "localhost:7788" : window.location.host;
    const ws = new WebSocket(`ws://${url}/ws/chat`);
    wsRef.current = ws;
    window.wsRef = wsRef;
    //Websocket for stop requests
    const wsStop = new WebSocket(`ws://${url}/ws/stop`);
    wsStopRef.current = wsStop;

    ws.onopen = () => {
      console.log("Connected to chat server");
    };

    wsStop.onopen = () => {
      console.log("Connected to stop websocket");
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

    wsStop.onmessage = (event: MessageEvent) => {
      console.log("received stop response:", event.data);
      const d = JSON.parse((event as TodoFixAny).data) as GraphData;
      const parse = StopDataZod.safeParse(d);
      if (!parse.success) {
        console.error(parse.error);
        return;
      }

      const stopResponse = parse.data;

      if (stopResponse.stopped) {
        setisThinking(false);
        setIsStopped(false);
      }
      addMessage({
        content: stopResponse.summary,
        role: "assistant",
      });
    };

    ws.onclose = () => {
      console.log("Disconnected from chat server");
    };
    wsStop.onclose = () => {
      console.log("Disconnected from stop server");
    };

    return () => {
      ws.close();
      wsStop.close();
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
    if (!wsStopRef.current) {
      return;
    }

    if (isStopped) {
      return;
    }

    setIsStopped(true);

    const stopPayload = {
      task: "stop",
    };

    wsStopRef.current?.send(JSON.stringify(stopPayload));
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
      const SHOULD_SCROLL_PERCENTAGE = 0.9;

      const shouldScroll =
        chatContainerRef.current.scrollTop +
          chatContainerRef.current.clientHeight >=
        chatContainerRef.current.scrollHeight * SHOULD_SCROLL_PERCENTAGE;

      if (shouldScroll) {
        bottomOfChatRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  return (
    <div className="h-full rounded-lg  bg-[#32363c] w-full px-2 py-4 flex flex-col">
      <PlanRenderer />
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
        <Flex
          as="form"
          align="center"
          className="max-w-3xl mx-auto bg-[#373c42] border-2 border-[#7E868F] pr-3 pt-2 pl-5 pb-2 rounded-lg"
        >
          <TextareaAutosize
            tabIndex={1}
            minRows={1}
            maxRows={8}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="What do you want ActionEngine to do?"
            className={cn(
              "w-full bg-transparent text-white",
              "font-normal text-base leading-[22px]",
              "placeholder:text-[889099] placeholder:text-sm",
              "focus:outline-none resize-none"
            )}
            wrap="hard"
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.shiftKey) {
                return;
              }
              if (e.key === "Enter" && !isThinking) {
                e.preventDefault();
                sendMessage();
              } else if (e.key === "Enter" && isThinking) {
                e.preventDefault();
              }
            }}
          />
          {isThinking ? (
            <Button
              type="button"
              kind="tertiary"
              onClick={stopTask}
              icon={
                <div className="relative top-[1.64px] left-[2.87px]">
                  <StopCircle
                    className={cn(
                      "text-[#649EF5] fill-[#649EF5]",
                      "w-[18.83px] h-[20.73px]"
                    )}
                  />
                </div>
              }
              className="hover:opacity-80 px-2"
            />
          ) : (
            <Button
              type="button"
              kind="tertiary"
              onClick={sendMessage}
              disabled={isThinking}
              icon={
                <div className="relative top-[1.64px] left-[2.87px]">
                  {" "}
                  <PaperPlaneRight
                    className={cn(
                      "text-[#649EF5] fill-[#649EF5]",
                      "w-[18.83px] h-[20.73px]"
                    )}
                  />{" "}
                </div>
              }
              className="hover:opacity-80 px-2"
            />
          )}
        </Flex>
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
