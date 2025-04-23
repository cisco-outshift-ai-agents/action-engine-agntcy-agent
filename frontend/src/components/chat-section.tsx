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

const AGENT_ID = "62f53991-0fec-4ff9-9b5c-ba1130d7bace";

const ChatSection: React.FC<ChatSectionProps> = () => {
  const [input, setInput] = useState("");
  const eventSourceRef = useRef<EventSource | null>(null);
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

  const sendMessage = async () => {
    try {
      // 1. Create a run
      const response = await fetch("http://localhost:7788/runs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          agent_id: AGENT_ID,
          input: { task: input },
          metadata: {},
          config: {
            recursion_limit: 25,
            configurable: {},
          },
        }),
      });

      const run = await response.json();

      // 2. Start streaming the results
      const events = new EventSource(
        `http://localhost:7788/runs/${run.run_id}/stream`
      );

      events.onmessage = (event) => {
        const data = JSON.parse(event.data);
        addMessage(getMessageFromSSEData(data.data, data.event, data.type));
      };

      eventSourceRef.current = events;
      addMessage({
        content: input,
        role: "user",
      });
      setInput("");
      setisThinking(true);
    } catch (error) {
      console.error("Failed:", error);
      setisThinking(false);
    }
  };

  const stopTask = () => {
    if (isStopped) {
      return;
    }

    setIsStopped(true);

    // TODO: Add delete run functionality here I think?
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getMessageFromSSEData = (
    data: GraphData,
    nodeType: NodeType,
    acpMessageType: "interrupt" | "error" | "message"
  ): ChatMessageProps => {
    if (acpMessageType === "interrupt") {
      return {
        role: "assistant",
        // TODO: REAL CONTENT
        content: "Please confirm",
        nodeType: "approval_request",
      };
    }

    if (acpMessageType === "error") {
      return {
        role: "assistant",
        content: data.error,
        error: data.error,
        isDone: data.exiting,
        nodeType,
      };
    }

    // For planning, just set the plan state
    if (nodeType === "planning") {
      setPlan(getPlanFromMessage(data));
    }

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
        <Flex
          as="form"
          align="center"
          className={cn(
            "max-w-3xl mx-auto bg-[#373c42] border-2 border-[#7E868F] pr-3 pt-2 pl-5 pb-2 rounded-lg",
            "group focus-within:border-[#649EF5]"
          )}
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
              "focus:ring-0 focus:border-0",
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
