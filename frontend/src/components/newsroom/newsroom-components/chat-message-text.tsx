import Markdown from "@/components/newsroom/markdown";
import { TodoFixAny } from "@/types";
import { ReactNode } from "react";

const ChatMessageText: React.FC<ChatMessageTextProps> = ({
  content,
  isThinking,
  role,
  //   isDone,
}) => {
  //Don't return anything if content is empty and done is true
  //   if (isDone) {
  //     return null;
  //   }
  return (
    <div className="flex gap-2 flex-col">
      {/* {errors?.map((error) => (
        <Alert className="my-2" variant="destructive">
          <AlertOctagonIcon className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{parseError(error)}</AlertDescription>
        </Alert>
      ))} */}

      {/* {warnings?.map((warning) => (
        <Alert className="my-2">
          <ExclamationTriangleIcon className="h-4 w-4" />
          <AlertTitle>Warning</AlertTitle>
          <AlertDescription>{warning}</AlertDescription>
        </Alert>
      ))} */}

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
  role: "user" | "assistant";
  //   isDone?: boolean;
}

export default ChatMessageText;
