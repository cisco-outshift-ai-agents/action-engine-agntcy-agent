import ChatMessageText from "./chat-message-text";
import CiscoAIAssistantLogo from "@/components/chat/chat-assets/cisco-ai-assistant.png";
import { Circle, Check, XCircle } from "lucide-react";
import { ReactNode, useState } from "react";
import {
  ExecutorTools,
  ToolResultMessage,
  ErrorMessage,
} from "@/components/chat-messages";

import { Button } from "@/components/ui/button";
import { GraphData } from "@/pages/session/types";
import { getLastToolCallAIMessage, getLastToolMessage } from "@/utils";
import { TodoFixAny } from "@/types";

const ChatMessage: React.FC<ChatMessageProps> = (props) => {
  const {
    content,
    error,
    warnings,
    role,
    isDone,
    nodeType,
    onHitlConfirmation,
  } = props;
  // Local state to maintain the approval response over time
  const [approvalResponse, setApprovalResponse] = useState<
    "approved" | "declined" | null
  >(null);

  const handleHitlConfirmation = (approved: boolean) => {
    if (!onHitlConfirmation) {
      console.error("onHitlConfirmation callback is not provided");
      return;
    }

    setApprovalResponse(approved ? "approved" : "declined");
    onHitlConfirmation(approved);
  };

  if (isDone) {
    return null;
  }

  // For errors and warnings, show error message
  if (error) {
    return <ErrorMessage error={error} warnings={warnings} />;
  }

  // For tool message (result of tool execution)
  if (role === "assistant" && content && !nodeType) {
    return <ToolResultMessage content={content as string} />;
  }

  // Render user messages
  if (role === "user") {
    return <UserChatMessage {...props} />;
  }

  // For planning node, show a concise message
  if (nodeType === "planning") {
    return <PlanningChatMessage {...props} />;
  }

  // For executor node, show action-focused UI
  if (nodeType === "executor") {
    return <ExecutorChatMessage {...props} />;
  }

  // For human in the loop (HITL) confirmation, show approval request UI
  if (nodeType === "approval_request") {
    return (
      <ApprovalRequestChatMessage
        {...props}
        handleHitlConfirmation={handleHitlConfirmation}
        approvalResponse={approvalResponse}
      />
    );
  }

  // For all other messages show conversational UI
  return <AssistantChatMessage {...props} />;
};

const UserChatMessage: React.FC<ChatMessageProps> = ({ content, role }) => {
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
};

const PlanningChatMessage: React.FC<ChatMessageProps> = ({ messages }) => {
  const lastAIMessage = getLastToolCallAIMessage(messages);
  const lastMessageTC = lastAIMessage?.tool_calls?.[0];
  const args = lastMessageTC?.args || {};
  const command = args["command"] || "update_plan";

  const commandMapper = {
    update_plan: "Updating the plan...",
    create: "Creating a new plan...",
    mark_steps: "Updating the plan...",
  };

  const mappedCommand =
    commandMapper[command as unknown as keyof typeof commandMapper] ||
    "Updating the plan...";

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
          <span className="text-sm">{mappedCommand}</span>
        </div>
      </div>
    </div>
  );
};

const ExecutorChatMessage: React.FC<ChatMessageProps> = ({
  actions,
  messages,
}) => {
  const lastToolMessage = getLastToolMessage(messages);
  const lastToolMessageContent = lastToolMessage?.content || "";

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
      {lastToolMessageContent && (
        <div className="flex gap-2 font-mono overflow-auto">
          🛠️
          <p className="text-sm text-gray-400">{lastToolMessageContent}</p>
        </div>
      )}
    </div>
  );
};

const ApprovalRequestChatMessage: React.FC<
  ChatMessageProps & {
    handleHitlConfirmation: (approved: boolean) => void;
    approvalResponse: "approved" | "declined" | null;
  }
> = ({ content, handleHitlConfirmation, approvalResponse }) => {
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
                <Button
                  variant="default"
                  className="bg-[#649EF5] hover:bg-[#538ee0] text-white px-4 py-2 text-sm font-semibold rounded"
                  onClick={() => handleHitlConfirmation(true)}
                >
                  Approve
                </Button>
                <Button
                  variant="outline"
                  className="border text-white px-4 py-2 text-sm font-semibold rounded hover:bg-white/10"
                  onClick={() => handleHitlConfirmation(false)}
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
};

const AssistantChatMessage: React.FC<ChatMessageProps> = ({
  content,
  thought,
  role,
  error,
  warnings,
}) => {
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
export interface ChatMessageProps {
  content: ReactNode | undefined | null;
  error?: string | undefined | null;
  warnings?: string[] | undefined | null;
  isLoading?: boolean | undefined | null;
  role: "user" | "assistant";
  thought?: string | undefined | null;
  actions?: string[] | undefined | null;
  isDone?: boolean;
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
  onHitlConfirmation?: (approved: boolean) => void;
  nodeType?: GraphData["node_type"];
  messages: GraphData["messages"];
}

export default ChatMessage;
