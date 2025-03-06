import Markdown from "@/components/newsroom/markdown";
import { TodoFixAny } from "@/types";
import {
  MessageCircleMore,
  MousePointerClick,
  TextCursorIcon,
  Terminal,
} from "lucide-react";
import { ReactNode } from "react";

const ChatMessageText: React.FC<ChatMessageTextProps> = ({
  content,
  isThinking,
  role,
  thoughts,
  actions,
  isTerminal,
  hasEmptyThought,
}) => {
  return (
    <div className="flex gap-2 flex-col">
      {thoughts && thoughts.length > 0 && (
        <div className="flex flex-col gap-1 text-xs text-gray-400 mb-2">
          {thoughts.map((thought, index) => (
            <span key={index}>
              <MessageCircleMore className="inline w-4 h-4 mr-2" />
              {thought}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center">
        <div className="overflow-hidden font-light w-full">
          {content && role === "user" && (
            <p className="font-normal text-base tracking-normal text-[#F7F7F7] whitespace-pre-wrap break-words text-base leading-[22px]">
              {content}
            </p>
          )}

          {content &&
            role === "assistant" &&
            isTerminal &&
            hasEmptyThought &&
            typeof content === "string" &&
            renderTerminalOutput(content)}

          {content &&
            role === "assistant" &&
            !(isTerminal && hasEmptyThought) && (
              <Markdown>{content as TodoFixAny}</Markdown>
            )}

          {!content && (
            <span className="text-muted-foreground text-sm">
              No response provided
            </span>
          )}
        </div>
        {isThinking && <span>...</span>}
      </div>
      {actions && actions.length > 0 && (
        <div className="flex flex-col gap-1 text-xs text-gray-400 mt-2">
          {actions.map((action, index) => (
            <span key={index}>
              {action.toLowerCase().includes("click") && (
                <MousePointerClick className="inline w-4 h-4 mr-2 flex-shrink-0" />
              )}
              {action.toLowerCase().includes("input text") && (
                <TextCursorIcon className="inline w-4 h-4 mr-2 flex-shrink-0" />
              )}
              {action.toLowerCase().includes("execute terminal") && (
                <Terminal className="inline w-4 h-4 mr-2 flex-shrink-0" />
              )}
              {action}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

const renderTerminalOutput = (content: string) => {
  const lines = content.split("\n");

  return (
    <div className="text-green-400 font-mono text-sm overflow-auto">
      <div className="mt-3">
        {lines.map((line, lineIndex) => {
          if (line.trim() && line.includes("  ")) {
            const items = line.split(/\s{2,}/g).filter((item) => item.trim());
            return (
              <div key={`line-${lineIndex}`} className="mb-1">
                {items.map((item, itemIndex) => (
                  <div
                    key={`item-${lineIndex}-${itemIndex}`}
                    className="pl-4 whitespace-nowrap"
                  >
                    {item}
                  </div>
                ))}
              </div>
            );
          }
          return (
            <div key={`line-${lineIndex}`} className="whitespace-pre-wrap">
              {line || " "}
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface ChatMessageTextProps {
  content: ReactNode | undefined | null;
  errors?: string[] | undefined | null;
  warnings?: string[] | undefined | null;
  isThinking?: boolean | undefined | null;
  thoughts?: string[] | undefined | null;
  actions?: string[] | undefined | null;
  isTerminal?: boolean;
  hasEmptyThought?: boolean;
  role: "user" | "assistant";
}

export default ChatMessageText;
