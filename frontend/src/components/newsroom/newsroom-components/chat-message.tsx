import ChatMessageText from "./chat-message-text";
import CiscoAIAssistantLogo from "@/components/newsroom/newsroom-assets/cisco-ai-assistant.png";
import { cn } from "@/utils";
import { MousePointerClick, TextCursorIcon } from "lucide-react";
import { ReactNode } from "react";

const ChatMessage: React.FC<ChatMessageProps> = ({
  content,
  role,
  error,
  warnings,
  isLoading,
  thoughts,
  actions,
  isDone,
}) => {
  if (isDone) {
    return null;
  }
  return (
    <>
      <div className={cn("bg-transparent rounded-md text-l text-[#f7f7f7]")}>
        <div
          className={cn(" ml-1 py-4 rounded-r-md", {
            "rounded-bl-md px-6 bg-[#373C42]": role === "assistant",
            "rounded-br-md": role === "user",
          })}
        >
          <div className="flex gap-3 items-center mb-2">
            {role === "assistant" && (
              <img src={CiscoAIAssistantLogo} alt="outshift-logo" width={24} />
            )}
            <p className="font-medium text-sm">
              {role === "assistant" ? "" : "You"}
            </p>
          </div>

          {isLoading ? (
            <span className="text-sm">Assistant is thinking...</span>
          ) : (
            <ChatMessageText
              content={content}
              errors={error ? [error] : undefined}
              warnings={warnings}
              role="assistant"
              thoughts={thoughts}
            />
          )}
          {actions && (
            <div className="flex flex-col gap-1 text-xs text-gray-400 mt-4">
              {actions.map((action, index) => (
                <span key={index}>
                  {action.toLowerCase().includes("click") && (
                    <MousePointerClick className="inline w-4 h-4 mr-2" />
                  )}
                  {action.toLowerCase().includes("input text") && (
                    <TextCursorIcon className="inline w-4 h-4 mr-2" />
                  )}
                  {action}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
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
