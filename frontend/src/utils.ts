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

export const getLastAITools = (data: GraphData): string[] => {
  const lastAIMessage = data.messages
    .filter((m) => m.type === "AIMessage")
    .pop();

  if (!lastAIMessage) {
    return [];
  }

  return [
    ...(lastAIMessage.tool_calls?.map((t) => {
      return JSON.stringify(t);
    }) || []),
    lastAIMessage.content || "",
  ].filter((a) => !!a);
};
