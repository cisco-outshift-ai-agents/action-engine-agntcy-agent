import React, { useState, useEffect, useRef } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { PaperPlaneRight, StopCircle } from "@magnetic/icons";
import { Button } from "@magnetic/button";
import { cn } from "@/utils";
import { Flex } from "@magnetic/flex";
import ChatMessage, {
  ChatMessageProps,
} from "./newsroom/newsroom-components/chat-message";
import CiscoAIAssistantLoader from "@/components/newsroom/newsroom-assets/thinking.gif";

import { TodoFixAny } from "@/types";
import { useChatStore } from "@/stores/chat";
import { GraphData, GraphDataZod, StopDataZod } from "@/pages/session/types";

interface ChatSectionProps {
  className?: string;
}

const ChatSection: React.FC<ChatSectionProps> = () => {
  const [messages, setMessages] = useState<
    {
      sender: string;
      text: ChatMessageProps;
    }[]
  >([]);
  const [input, setInput] = useState(
    "Go to Wikipedia and search for Cisco Systems, then click on the first link on the page"
  );
  const wsRef = useRef<WebSocket | null>(null); //Main websocket for tasks
  const wsStopRef = useRef<WebSocket | null>(null); //Websocket for stop requests
  const isThinking = useChatStore((state) => state.isThinking);
  const setisThinking = useChatStore((state) => state.setisThinking);
  const isStopped = useChatStore((state) => state.isStopped);
  const setIsStopped = useChatStore((state) => state.setIsStopped);

  useEffect(() => {
    const useLocal = true;
    const url = useLocal ? "localhost:7788" : window.location.host;
    const ws = new WebSocket(`ws://${url}/ws/chat`);
    wsRef.current = ws;
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
      const d = JSON.parse((event as TodoFixAny).data) as GraphData;
      const parse = GraphDataZod.safeParse(d);
      if (!parse.success) {
        console.error(parse.error);
        return;
      }
      const clean = cleanAPIData(d);
      console.log("processed data:", clean);

      setMessages((messages) => [
        ...messages,
        {
          sender: "agent",
          text: clean,
        },
      ]);
      if (clean.isDone) {
        setisThinking(false);
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

      setMessages((messages) => [
        ...messages,
        {
          sender: "agent",
          text: {
            content: stopResponse.summary,
            role: "assistant",
          },
        },
      ]);
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
    setMessages((messages) => [
      ...messages,
      {
        sender: "user",
        text: {
          content: input,
          role: "user",
        },
      },
    ]);

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

  return (
    <div className="h-full rounded-lg  bg-[#32363c] w-full px-2 py-4 flex flex-col">
      <div className="flex-1 overflow-y-auto px-2 pt-2 pb-3">
        <div className="flex flex-col-reverse gap-4 space-y-reverse">
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
          {[...messages].reverse().map((message, index) => (
            <div key={index}>
              <ChatMessage {...message.text} />
            </div>
          ))}
        </div>
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

const cleanAPIData = (data: GraphData): ChatMessageProps => {
  return {
    content: data.brain.summary,
    thought: data.brain.thought,
    role: "assistant",
    actions: getLastAITools(data),
    error: data.error,
    isDone: data.exiting,
  };
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
