import ChatMessageText from "./chat-message-text";
import CiscoAIAssistantLogo from "@/components/newsroom/newsroom-assets/cisco-ai-assistant.png";
import { Circle, Check, XCircle } from "lucide-react";
import { ReactNode, useState } from "react";
import {
  ExecutorTools,
  ToolResultMessage,
  ErrorMessage,
} from "@/components/chat-messages";

// Extend the Window interface to include wsRef
declare global {
  interface Window {
    wsRef?: {
      current: WebSocket | null;
    };
  }
}
import { Button } from "@magnetic/button";

export type NodeType =
  | "thinking"
  | "planning"
  | "executor"
  | "approval_request";

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
  toolCall?: {
    name: string;
    args: {
      terminal_id: string;
      script: string;
      action: string;
    };
    id: string;
    type: string;
  };
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
  toolCall,
}) => {
  const [approvalResponse, setApprovalResponse] = useState<
    "approved" | "declined" | null
  >(null);
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

  if (nodeType === "approval_request" && content && toolCall) {
    const handleResponse = (approved: boolean) => {
      if (
        !window.wsRef?.current ||
        window.wsRef.current.readyState !== WebSocket.OPEN
      ) {
        console.error("WebSocket not ready");
        return;
      }
      setApprovalResponse(approved ? "approved" : "declined");

      const response = {
        approval_response: {
          approved,
          tool_call: toolCall,
        },
      };

      window.wsRef.current.send(JSON.stringify(response));
    };

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
            <div className="flex flex-col gap-4">
              <p className="font-normal text-base tracking-normal text-[#F7F7F7] whitespace-pre-wrap break-words leading-[22px]">
                {content}
              </p>
              {approvalResponse === null ? (
                <div className="flex gap-2">
                  <Button kind="primary" onClick={() => handleResponse(true)}>
                    Approve
                  </Button>
                  <Button
                    kind="secondary"
                    onClick={() => handleResponse(false)}
                  >
                    Decline
                  </Button>
                </div>
              ) : approvalResponse === "approved" ? (
                <div className="flex items-center text-green-500">
                  <Check className="inline w-4 h-4 mr-2 flex-shrink-0" />
                  <span className="text-sm">Approved</span>
                </div>
              ) : (
                <div className="flex items-center text-red-500">
                  <XCircle className="inline w-4 h-4 mr-2 flex-shrink-0" />
                  <span className="text-sm">Declined</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
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
