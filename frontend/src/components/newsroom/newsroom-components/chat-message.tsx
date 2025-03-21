import ChatMessageText from "./chat-message-text";
import CiscoAIAssistantLogo from "@/components/newsroom/newsroom-assets/cisco-ai-assistant.png";
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
  nodeType,
}) => {
  if (isDone) {
    return null;
  }

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
            {nodeType === "thinking" && (
              <ChatMessageText
                content={content}
                thought={thought}
                role={role}
                errors={error ? [error] : undefined}
              />
            )}
            {(nodeType === "executor" ||
              nodeType === "planning" ||
              !nodeType) && (
              <ChatMessageText
                content={content}
                role={role}
                actions={actions}
                errors={error ? [error] : undefined}
                warnings={warnings}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

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

export default ChatMessage;
