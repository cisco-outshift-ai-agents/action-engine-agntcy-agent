import ChatMessageText from "./chat-message-text";
import CiscoAIAssistantLogo from "@/components/newsroom/newsroom-assets/cisco-ai-assistant.png";
import { cn } from "@/utils";
import { Circle } from "lucide-react";
import { ReactNode } from "react";

const ChatMessage: React.FC<ChatMessageProps> = ({
  content,
  role,
  error,
  warnings,
  thought,
  actions,
  isDone,
}) => {
  if (isDone) {
    return null;
  }

  return (
    <div className={cn("text-l  text-[#f7f7f7]")}>
      <div
        className={cn("py-2", {
          "rounded-xl bg-[#373C42] ": role === "assistant",
        })}
      >
        <div
          className={cn("flex", {
            "items-start": role === "assistant",
            "px-4": role === "assistant",
          })}
        >
          {role === "assistant" && (
            <img
              src={CiscoAIAssistantLogo}
              alt="outshift-logo"
              width={24}
              className="mr-3 mt-0.5"
            />
          )}

          <div className="flex flex-col">
            {role === "user" && (
              <div className="flex items-center mb-2">
                <Circle className="w-5 h-5 text-[#ACACAC] fill-[#ACACAC] mr-2 flex-shrink-0" />
                <p className="text-base font-semibold leading-[22px] tracking-normal text-[#f7f7f7]">
                  You
                </p>
              </div>
            )}

            <ChatMessageText
              content={content}
              thought={thought}
              errors={error ? [error] : undefined}
              warnings={warnings}
              role={role}
              actions={actions}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export interface ChatMessageProps {
  content: ReactNode | undefined | null;
  error?: string | undefined | null;
  warnings?: string[] | undefined | null;
  isLoading?: boolean | undefined | null;
  role: "user" | "assistant";
  thought?: string | undefined | null;
  actions?: string[] | undefined | null;
  isDone?: boolean;
}

export default ChatMessage;
