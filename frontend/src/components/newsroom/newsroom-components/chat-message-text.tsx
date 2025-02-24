import Markdown from "@/components/newsroom/markdown";
import { TodoFixAny } from "@/types";
import {
  MessageCircleMore,
  MousePointerClick,
  TextCursorIcon,
} from "lucide-react";
import { ReactNode } from "react";

const ChatMessageText: React.FC<ChatMessageTextProps> = ({
  content,
  isThinking,
  role,
  thoughts,
  actions,
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
        <div className="overflow-hidden font-light">
          {content && role === "user" && (
            <p className="font-normal text-base tracking-normal text-[#F7F7F7] whitespace-pre-wrap break-words text-base leading-[22px]">
              {content}
            </p>
          )}
          {content && role === "assistant" && (
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
              {action}
            </span>
          ))}
        </div>
      )}
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

  role: "user" | "assistant";
}

export default ChatMessageText;
