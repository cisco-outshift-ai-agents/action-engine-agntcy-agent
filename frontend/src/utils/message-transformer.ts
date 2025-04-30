import {
  ChatMessageProps,
  NodeType,
} from "@/components/chat/chat-components/chat-message";
import { GraphData } from "@/pages/session/types";
import { getLastAITools } from "@/utils";

export const transformSSEDataToMessage = (
  data: GraphData,
  nodeType: NodeType,
  acpMessageType: "interrupt" | "error" | "message"
): ChatMessageProps | undefined => {
  if (acpMessageType === "interrupt") {
    return {
      role: "assistant",
      content: "Please confirm",
      nodeType: "approval_request",
    };
  }

  if (acpMessageType === "error") {
    return {
      role: "assistant",
      content: data.error,
      error: data.error,
      isDone: data.exiting,
      nodeType,
    };
  }

  if (nodeType === "executor") {
    return {
      role: "assistant",
      content: null,
      actions: getLastAITools(data),
      error: data.error,
      isDone: data.exiting,
      nodeType,
    };
  }

  if (nodeType === "thinking") {
    return {
      role: "assistant",
      content: data.brain.summary,
      thought: data.brain.thought,
      error: data.error,
      isDone: data.exiting,
      nodeType,
    };
  }

  return undefined;
};
