import React, { useState, useEffect, useRef } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { PaperPlaneRight, StopCircle } from "@magnetic/icons";
import { Button } from "@magnetic/button";
import { cn } from "@/utils";
import { Flex } from "@magnetic/flex";
import ChatMessage from "./newsroom/newsroom-components/chat-message";
import CiscoAIAssistantLoader from "@/components/newsroom/newsroom-assets/thinking.gif";

import { TodoFixAny } from "@/types";
import { useChatStore } from "@/stores/chat";
import { CleanerData, Data, DataZod, StopDataZod } from "@/pages/session/types";

interface ChatSectionProps {
  className?: string;
}

const ChatSection: React.FC<ChatSectionProps> = () => {
  const [messages, setMessages] = useState<
    {
      sender: string;
      text: CleanerData;
    }[]
  >([]);
  const [input, setInput] = useState("");
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
      console.log("received websocket message:", event.data);
      const d = JSON.parse((event as TodoFixAny).data) as Data;
      const parse = DataZod.safeParse(d);
      if (!parse.success) {
        console.error(parse.error);
        return;
      }
      const clean = cleanData(d);
      console.log("processed data:", clean);

      setMessages((messages) => [
        ...messages,
        {
          sender: "agent",
          text: clean,
        },
      ]);
      if (clean.action.some((a) => a.done === true)) {
        setisThinking(false);
      }
    };

    wsStop.onmessage = (event: MessageEvent) => {
      console.log("received stop response:", event.data);
      const d = JSON.parse((event as TodoFixAny).data) as Data;
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
            action: [{ summary: stopResponse.summary }],
            current_state: {},
            html_content: "",
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
        text: cleanData({
          action: [{ summary: input }],
          current_state: {},
          html_content: "",
        }),
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
              <ChatMessage
                content={message.text.action.map((a) => a.summary).join("\n")}
                isDone={message.text.action.some((a) => a.done === true)}
                thoughts={
                  message.text.action
                    .map((a) => a.thought)
                    .filter((a) => !!a) as string[]
                }
                actions={
                  message.text.action
                    .map((a) => {
                      if (a.click_element) {
                        return `Click element ${a.click_element.index}`;
                      } else if (a.input_text) {
                        return `Input text ${a.input_text.text} at index ${a.input_text.index}`;
                      } else {
                        return undefined;
                      }
                    })
                    .filter((a) => !!a) as string[]
                }
                role={message.sender === "agent" ? "assistant" : "user"}
              />
            </div>
          ))}
        </div>
      </div>
      <div className="px-4 pt-2 pb-3">
        <Flex
          as="form"
          align="center"
          className="max-w-3xl mx-auto bg-[#373c42] border-2 border-[#7E868F] pr-3 pt-2 pr-3 pl-5 pb-2 rounded-lg"
        >
          <TextareaAutosize
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

const cleanData = (data: Data): CleanerData => {
  console.log(data);

  if (typeof data === "string") {
    return {
      action: [{ summary: data }],
      current_state: {},
      html_content: "",
    };
  }
  return {
    action: data.action.map((action) => {
      if (typeof action === "string") {
        return {
          summary: action,
        };
      }

      return {
        input_text: action.input_text,
        click_element: action.click_element,
        prev_action_evaluation: action.prev_action_evaluation,
        important_contents: action.important_contents,
        task_progress: action.task_progress,
        future_plans: action.future_plans,
        thought: action.thought,
        summary: action.summary,
        done: typeof action.done === "boolean" ? action.done : false,
      };
    }),
    current_state: data.current_state,
    html_content: data.html_content,
  };
};

export default ChatSection;
