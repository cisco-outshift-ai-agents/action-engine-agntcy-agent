import ChatMessageText from "./chat-message-text";
import CiscoAIAssistantLogo from "@/components/newsroom/newsroom-assets/cisco-ai-assistant.png";
import { cn } from "@/utils";
import { ReactNode } from "react";

const ChatMessage: React.FC<ChatMessageProps> = ({
  content,
  role,
  error,
  warnings,
  thoughts,
  actions,
  isDone,
}) => {
  if (isDone) {
    return null;
  }

  return (
    <div className={cn("bg-transparent rounded-md text-l text-[#f7f7f7]")}>
      <div
        className={cn("ml-1 py-4 rounded-r-md", {
          "rounded-bl-md px-6 bg-[#373C42]": role === "assistant",
          "rounded-br-md": role === "user",
        })}
      >
        <div
          className={cn("flex", { "items-start gap-3": role === "assistant" })}
        >
          {role === "assistant" && (
            <img src={CiscoAIAssistantLogo} alt="outshift-logo" width={24} />
          )}

          <div className="flex flex-col">
            {role === "user" && (
              <p className="text-sm font-medium mb-1 text-white">You</p>
            )}

            <ChatMessageText
              content={content}
              thoughts={thoughts}
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

interface ChatMessageProps {
  content: ReactNode | undefined | null;
  error?: string | undefined | null;
  warnings?: string[] | undefined | null;
  isLoading?: boolean | undefined | null;
  role: "user" | "assistant";
  thoughts?: string[] | undefined | null;
  actions?: string[] | undefined | null;
  isDone?: boolean;
}

export default ChatMessage;
