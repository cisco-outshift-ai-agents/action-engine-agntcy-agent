import { ChatMessageProps } from "@/components/chat/chat-components/chat-message";
import { GraphDataZod } from "@/pages/session/types";
import { getLastAITools } from "@/utils";
import { z } from "zod";

export const transformSSEDataToMessage = (
  data: unknown
): ChatMessageProps | undefined => {
  const safeParse = SSEMessageZod.safeParse(data);
  if (!safeParse.success) {
    console.error("Failed to parse SSE data:", safeParse.error);
    return undefined;
  }
  const { data: graphData } = safeParse.data;

  const nodeType = graphData.node_type;

  if (nodeType === "executor") {
    return {
      role: "assistant",
      content: null,
      actions: getLastAITools(graphData),
      error: graphData.error,
      isDone: graphData.exiting,
      nodeType,
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
    };
  }

  return undefined;
};

export const SSEMessageZod = z.object({
  type: z.string().nullish(),
  run_id: z.string().nullish(),
  status: z.string().nullish(),
  data: GraphDataZod,
});
export type SSEMessage = z.infer<typeof SSEMessageZod>;
