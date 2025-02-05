import React, { useState, useEffect, useRef } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { Paperclip, PaperPlaneRight } from "@magnetic/icons";
import { Button } from "@magnetic/button";
import { cn } from "@/utils";
import { Flex } from "@magnetic/flex";

const ChatSection: React.FC = () => {
  const [messages, setMessages] = useState<
    {
      sender: string;
      text: string;
    }[]
  >([]);
  const [input, setInput] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const useLocal = true;
    const url = useLocal ? "localhost:7788" : window.location.host;
    const ws = new WebSocket(`ws://${url}/ws/chat`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("Connected to chat server");
    };

    ws.onmessage = (event) => {
      setMessages((messages) => [
        ...messages,
        {
          sender: "agent",
          text: event.data,
        },
      ]);
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
        text: input,
      },
    ]);

    setInput("");
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      sendMessage();
    }
  };

  return (
    <>
      <div className="flex-1">
        {/* Temp styling */}
        <div className="bg-white">
          {messages.map((message, index) => (
            <div
              key={index}
              className={cn(
                "p-3",
                message.sender === "agent" ? "bg-gray-100" : "bg-gray-200"
              )}
            >
              <strong>{message.sender}:</strong>
              {message.text}
            </div>
          ))}
        </div>
      </div>
      <div className="px-4 pt-2 pb-3">
        <Flex
          as="form"
          align="center"
          className="max-w-3xl mx-auto bg-[#373c42] border border-[#666666] p-3 rounded-lg"
        >
          <Button
            type="button"
            kind="tertiary"
            icon={<Paperclip />}
            className="hover:opacity-80 px-2"
          />

          <TextareaAutosize
            minRows={1}
            maxRows={8}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="What do you want ActionEngine to do?"
            className={cn(
              "w-full bg-transparent text-white",
              "font-normal text-base leading-[22px]",
              "placeholder:text-grey-400 placeholder:text-sm",
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
            icon={<PaperPlaneRight />}
            className="hover:opacity-80 px-2"
          />
        </Flex>
      </div>
    </>
  );
};

export default ChatSection;
