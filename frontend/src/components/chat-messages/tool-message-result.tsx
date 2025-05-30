import { ToolResultProps } from "@/pages/session/types";
import { cn } from "@/utils";
import { ArrowRight } from "lucide-react";

const ToolMessageResult: React.FC<ToolResultProps> = ({
  className,
  content,
}) => {
  return (
    <div
      className={cn("flex items-center gap-2 text-sm text-gray-300", className)}
    >
      <ArrowRight className="w-4 h-4" />
      <span>{content}</span>
    </div>
  );
};

export default ToolMessageResult;
