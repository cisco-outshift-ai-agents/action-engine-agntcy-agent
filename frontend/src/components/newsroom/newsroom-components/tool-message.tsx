import { cn } from "@/utils";
import CiscoAIAssistantLogo from "@/components/newsroom/newsroom-assets/cisco-ai-assistant.png";
import ChatMessageText from "./chat-message-text";

interface ToolMessageProps {
  content?: string | null;
  actions?: string[];
  error?: string | null;
  warnings?: string[] | null;
}

const ToolMessage: React.FC<ToolMessageProps> = ({
  content,
  actions,
  error,
  warnings,
}) => {
  if (!content && !actions?.length) return null;

  return (
    <div className={cn("text-l text-[#f7f7f7]")}>
      <div className="py-2 rounded-xl bg-[#373C42]">
        <div className="flex items-start px-4">
          <img
            src={CiscoAIAssistantLogo}
            alt="outshift-logo"
            width={24}
            className="mr-3 mt-0.5"
          />
          <div className="flex flex-col">
            <ChatMessageText
              content={content}
              role="assistant"
              actions={actions}
              errors={error ? [error] : undefined}
              warnings={warnings}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ToolMessage;
