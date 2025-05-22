import { ChatMessageProps } from "@/components/chat/chat-components/chat-message";
import { GraphDataZod } from "@/pages/session/types";
import { getLastAIMessageToolsStrAry } from "@/utils";
import { z } from "zod";

export const transformSSEDataToMessage = (
  data: unknown
): ChatMessageProps | undefined => {
  console.log("💾 Transforming SSE data to message:", data);

  // Modified schema to allow either data or values
  const safeParse = SSEMessageZod.safeParse(data);
  if (!safeParse.success) {
    console.error("Failed to parse SSE data:", safeParse.error);
    return undefined;
  }

  // Extract graphData from either data or values
  const graphData = safeParse.data.data || safeParse.data.values;

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
      isDone: graphData.exiting,
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
      isDone: graphData.exiting,
      nodeType,
      messages,
    };
  }

  if (nodeType === "planning") {
    return {
      role: "assistant",
      content: graphData.brain.summary,
      actions: getLastAIMessageToolsStrAry(graphData.messages),
      nodeType,
      messages,
    };
  }

  return undefined;
};

export const SSEMessageZod = z.object({
  type: z.string().nullish(),
  run_id: z.string().nullish(),
  status: z.string().nullish(),
  data: GraphDataZod.optional(),
  values: GraphDataZod.optional(),
});
export type SSEMessage = z.infer<typeof SSEMessageZod>;
