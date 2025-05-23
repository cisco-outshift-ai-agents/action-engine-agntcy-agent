import { twMerge } from "tailwind-merge";
import { type ClassValue, clsx } from "clsx";
import { GraphData } from "./pages/session/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const extractHostname = (summary: string): string => {
  const match = summary.match(/^(\S+@\S+):/);
  return match ? match[1] : "default-hostname";
};

export const getLastToolCallAIMessage = (
  messages: GraphData["messages"]
): GraphData["messages"][number] | undefined => {
  const lastAIMessage = messages
    .filter((m) => m.type === "AIMessage" && m.tool_calls?.length)
    .pop();

  return lastAIMessage;
};

export const getLastToolMessage = (
  messages: GraphData["messages"]
): GraphData["messages"][number] | undefined => {
  const lastToolMessage = messages
    .filter((m) => m.type === "ToolMessage")
    .pop();

  return lastToolMessage;
};
