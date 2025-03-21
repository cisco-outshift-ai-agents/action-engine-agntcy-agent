import React from "react";
import { cn } from "@/utils";
import BrowserToolMessage from "./browser-tool-message";
import TerminalToolMessage from "./terminal-tool-message";
import TerminateToolMessage from "./terminate-tool-message";
import { BrowserAction } from "./types";

interface ExecutorToolsProps {
  className?: string;
  actions: string[];
}

interface ToolCall {
  id: string;
  name: string;
  type: string;
  args: Record<string, unknown>;
}

const ExecutorTools: React.FC<ExecutorToolsProps> = ({
  className,
  actions,
}) => {
  const renderToolCall = (action: string, index: number) => {
    try {
      const toolCall = JSON.parse(action) as ToolCall;

      // Only render if it's a tool call
      if (toolCall.type !== "tool_call") {
        return null;
      }

      switch (toolCall.name) {
        case "browser_use": {
          const args = toolCall.args as {
            action: BrowserAction;
            url?: string;
            index?: number;
            text?: string;
            script?: string;
            scroll_amount?: number;
            tab_id?: number;
          };
          return <BrowserToolMessage key={index} {...args} />;
        }
        case "terminal": {
          const args = toolCall.args as { command: string };
          return <TerminalToolMessage key={index} {...args} />;
        }
        case "terminate": {
          const args = toolCall.args as {
            status: "success" | "failure";
            reason?: string;
          };
          return <TerminateToolMessage key={index} {...args} />;
        }
        default:
          return null;
      }
    } catch (e) {
      // If not valid JSON or not a tool call, don't render anything
      return null;
    }
  };

  const validToolCalls = actions
    .map((action, index) => renderToolCall(action, index))
    .filter(Boolean);

  if (validToolCalls.length === 0) {
    return null;
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>{validToolCalls}</div>
  );
};

export default ExecutorTools;
