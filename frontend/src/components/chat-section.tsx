import React, { useState, useEffect, useRef } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { PaperPlaneRight } from "@magnetic/icons";
import { Button } from "@magnetic/button";
import { cn } from "@/utils";
import { Flex } from "@magnetic/flex";
import ChatMessage from "./newsroom/newsroom-components/chat-message";
import { z } from "zod";
import { TodoFixAny } from "@/types";
import { useChatStore } from "@/stores/chat";

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
  const wsRef = useRef<WebSocket | null>(null);
  const isProcessing = useChatStore((state) => state.isProcessing);
  const setIsProcessing = useChatStore((state) => state.setIsProcessing);

  useEffect(() => {
    const useLocal = true;
    const url = useLocal ? "localhost:7788" : window.location.host;
    const ws = new WebSocket(`ws://${url}/ws/chat`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("Connected to chat server");
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
        setIsProcessing(false);
      }
    };

    ws.onclose = () => {
      console.log("Disconnected from chat server");
    };

    return () => {
      ws.close();
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
    setIsProcessing(true);
  };

  return (
    <div className="h-full rounded-lg  bg-[#32363c] w-full px-2 py-6 flex flex-col">
      <div className="flex-1 overflow-y-auto px-2 pt-2 pb-3">
        <div className="flex flex-col-reverse gap-2 space-y-reverse">
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
          className="max-w-3xl mx-auto bg-[#373c42] border-2 border-white/50 p-3 rounded-lg"
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
              if (e.key === "Enter") {
                e.preventDefault();
                sendMessage();
              }
            }}
          />

          <Button
            type="button"
            kind="tertiary"
            onClick={sendMessage}
            disabled={isProcessing}
            icon={<PaperPlaneRight className="text-blue-500 fill-blue-500" />}
            className="hover:opacity-80 px-2"
          />
        </Flex>
        <div className="text-center mt-2 text-xs text-[#D0D4D9]">
          Assistant can make mistakes. Verify responses.
        </div>
      </div>
    </div>
  );
};

const DataZod = z.object({
  action: z.array(
    z.union([
      z.string(),
      z.object({
        input_text: z
          .object({ index: z.number(), text: z.string() })
          .optional(),
        click_element: z.object({ index: z.number() }).optional(),
        prev_action_evaluation: z.string().optional(),
        important_contents: z.string().optional(),
        task_progress: z.string().optional(),
        future_plans: z.string().optional(),
        thought: z.string().optional(),
        summary: z.string().optional(),
        done: z.union([z.boolean(), z.object({ text: z.string() })]).optional(),
      }),
    ])
  ),
  current_state: z.object({}).optional(),
  html_content: z.string(),
});
type Data = z.infer<typeof DataZod>;

// Removes the union type
const CleanerDataZod = z.object({
  action: z.array(
    z.object({
      input_text: z.object({ index: z.number(), text: z.string() }).optional(),
      click_element: z.object({ index: z.number() }).optional(),
      prev_action_evaluation: z.string().optional(),
      important_contents: z.string().optional(),
      task_progress: z.string().optional(),
      future_plans: z.string().optional(),
      thought: z.string().optional(),
      summary: z.string().optional(),
      done: z.boolean().optional(),
    })
  ),
  current_state: z.object({}).optional(),
  html_content: z.string(),
});
type CleanerData = z.infer<typeof CleanerDataZod>;

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
