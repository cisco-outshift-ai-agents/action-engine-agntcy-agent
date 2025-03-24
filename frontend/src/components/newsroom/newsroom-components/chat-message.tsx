import ChatMessageText from "./chat-message-text";
import CiscoAIAssistantLogo from "@/components/newsroom/newsroom-assets/cisco-ai-assistant.png";
import { Circle } from "lucide-react";
import { ReactNode } from "react";
import {
  ExecutorTools,
  ToolResultMessage,
  ErrorMessage,
} from "@/components/chat-messages";

export type NodeType = "thinking" | "planning" | "executor";

export interface ChatMessageProps {
  content: ReactNode | undefined | null;
  error?: string | undefined | null;
  warnings?: string[] | undefined | null;
  isLoading?: boolean | undefined | null;
  role: "user" | "assistant";
  thought?: string | undefined | null;
  actions?: string[] | undefined | null;
  isDone?: boolean;
  nodeType?: NodeType;
}

const ChatMessage: React.FC<ChatMessageProps> = ({
  content,
  role,
  error,
  warnings,
  thought,
  actions,
  isDone,
  nodeType,
}) => {
  if (isDone) {
    return null;
  }

  // Render user messages
  if (role === "user") {
    return (
      <div className="text-l text-[#f7f7f7]">
        <div className="py-2">
          <div className="flex">
            <div className="flex flex-col">
              <div className="flex items-center mb-2">
                <Circle className="w-5 h-5 text-[#ACACAC] fill-[#ACACAC] mr-2 flex-shrink-0" />
                <p className="text-base font-semibold leading-[22px] tracking-normal text-[#f7f7f7]">
                  You
                </p>
              </div>
              <ChatMessageText content={content} role={role} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // For planning node, show a concise message
  if (nodeType === "planning") {
    return (
      <div className="text-l text-[#f7f7f7]">
        <div className="py-2">
          <div className="flex items-center text-gray-400">
            <img
              src={CiscoAIAssistantLogo}
              alt="outshift-logo"
              width={16}
              className="mr-2"
            />
            <span className="text-sm">Updating plan...</span>
          </div>
        </div>
      </div>
    );
  }

  // For executor node, show action-focused UI
  if (nodeType === "executor") {
    return (
      <div className="text-l text-[#f7f7f7]">
        <div className="py-2">
          <div className="flex items-start">
            <img
              src={CiscoAIAssistantLogo}
              alt="outshift-logo"
              width={16}
              className="mr-2 mt-1"
            />
            {actions?.length ? <ExecutorTools actions={actions} /> : null}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorMessage error={error} warnings={warnings} />;
  }

  // For tool message (result of tool execution)
  if (role === "assistant" && content && !nodeType) {
    return <ToolResultMessage content={content as string} />;
  }

  // For thinking node (and fallback), show conversational UI
  return (
    <div className="text-l text-[#f7f7f7]">
      <div className="py-2 rounded-xl bg-[#373C42]">
        <div className="flex items-start px-4">
          <img
            src={CiscoAIAssistantLogo}
            alt="outshift-logo"
            width={24}
            className="mr-3 mt-0.5"
          />
          <div className="flex flex-col">
            <div className="flex flex-col gap-4">
              <ChatMessageText
                content={content}
                thought={thought}
                role={role}
              />
              {(error || warnings?.length) && (
                <ErrorMessage error={error} warnings={warnings} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
