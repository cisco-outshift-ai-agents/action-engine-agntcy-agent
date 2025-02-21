import Markdown from "@/components/newsroom/markdown";
import { TodoFixAny } from "@/types";
import { MessageCircleMore } from "lucide-react";
import { ReactNode } from "react";

const ChatMessageText: React.FC<ChatMessageTextProps> = ({
  content,
  isThinking,
  role,
  thoughts,
}) => {
  return (
    <div className="flex gap-2 flex-col">
      {thoughts && thoughts.length > 0 && (
        <div className="flex flex-col gap-1 text-xs text-gray-400 mb-4">
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
            <pre className="markdown-body font-cisco whitespace-pre-wrap break-words text-sm">
              {content}
            </pre>
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
    </div>
  );
};

interface ChatMessageTextProps {
  content: ReactNode | undefined | null;
  errors?: string[] | undefined | null;
  warnings?: string[] | undefined | null;
  isThinking?: boolean | undefined | null;
  thoughts?: string[] | undefined | null;
  role: "user" | "assistant";
}

export default ChatMessageText;
