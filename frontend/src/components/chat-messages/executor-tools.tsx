import React from "react";
import { cn } from "@/utils";
import BrowserToolMessage from "./browser-tool-message";
import TerminalToolMessage from "./terminal-tool-message";
import TerminateToolMessage from "./terminate-tool-message";
import {
  BrowserUseArgsZod,
  TerminalUseArgsZod,
  TerminateUseArgsZod,
  GraphData,
} from "@/pages/session/types";

interface InvalidToolMessageProps {
  toolName: string;
  error: string;
}

const InvalidToolMessage: React.FC<InvalidToolMessageProps> = ({
  toolName,
  error,
}) => (
  <div className="rounded-md bg-red-50 p-4 border border-red-200">
    <div className="text-sm text-red-800">
      <p className="font-medium">Invalid {toolName} tool call</p>
      <pre className="mt-1 text-xs whitespace-pre-wrap">{error}</pre>
    </div>
  </div>
);

interface ExecutorToolsProps {
  className?: string;
  messages: GraphData["messages"];
}

const ExecutorTools: React.FC<ExecutorToolsProps> = ({
  className,
  messages,
}) => {
  // Get the most recent AI message's tool calls
  const lastAIMessage = messages
    .filter((m) => m.type === "AIMessage" && m.tool_calls?.length)
    .pop();

  const toolCalls = lastAIMessage?.tool_calls || [];

  const renderToolCall = (
    toolCall: NonNullable<typeof toolCalls>[number],
    index: number
  ) => {
    switch (toolCall.name) {
      case "browser_use": {
        const result = BrowserUseArgsZod.safeParse(toolCall.args);

  
        if (!result.success) {
          console.error("Invalid browser_use args:", result.error);
          return (
            <InvalidToolMessage
              key={index}
              toolName="browser_use"
              error={result.error.message}
            />
          );
        }

        return <BrowserToolMessage key={index} {...result.data} />;
      }
      case "terminal": {
        const result = TerminalUseArgsZod.safeParse(toolCall.args);
        if (!result.success) {
          console.error("Invalid terminal args:", result.error);
          return (
            <InvalidToolMessage
              key={index}
              toolName="terminal"
              error={result.error.message}
            />
          );
        }
        return <TerminalToolMessage key={index} {...result.data} />;
      }
      case "terminate": {
        const result = TerminateUseArgsZod.safeParse(toolCall.args);
        if (!result.success) {
          console.error("Invalid terminate args:", result.error);
          return (
            <InvalidToolMessage
              key={index}
              toolName="terminate"
              error={result.error.message}
            />
          );
        }
        return <TerminateToolMessage key={index} {...result.data} />;
      }
      default:
        return null;
    }
  };

  const validToolCalls = toolCalls
    .map((tc, i) => renderToolCall(tc, i))
    .filter(Boolean);

  if (validToolCalls.length === 0) {
    return null;
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>{validToolCalls}</div>
  );
};

export default ExecutorTools;
