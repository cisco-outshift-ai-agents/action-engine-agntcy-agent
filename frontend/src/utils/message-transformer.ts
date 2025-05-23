import { ChatMessageProps } from "@/components/chat/chat-components/chat-message";
import { GraphData } from "@/pages/session/types";
import { getLastAIMessageToolsStrAry } from "@/utils";
import { data } from "react-router-dom";

export const transformSSEDataToMessage = (
  graphData: GraphData | undefined
): ChatMessageProps | undefined => {
  console.log("💾 Transforming SSE data to message:", data);

  if (!graphData) {
    console.error("Graph data is missing in the parsed SSE data.");
    return undefined;
  }

  const nodeType = graphData.node_type;
  const messages = graphData.messages || [];

  if (nodeType === "executor") {
    return {
      role: "assistant",
      content: null,
      error: graphData.error,
      actions: getLastAIMessageToolsStrAry(messages),
      nodeType,
      messages,
    };
  }

  if (nodeType === "thinking") {
    return {
      role: "assistant",
      content: graphData.brain.summary,
      thought: graphData.brain.thought,
      error: graphData.error,
      nodeType,
      messages,
    };
  }

  if (nodeType === "planning") {
    return {
      role: "assistant",
      content: graphData.brain.summary,
      actions: getLastAIMessageToolsStrAry(messages),
      nodeType,
      messages,
    };
  }

  return undefined;
};
