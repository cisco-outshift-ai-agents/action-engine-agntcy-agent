import { TerminalToolProps } from "@/pages/session/types";
import { cn } from "@/utils";
import { Terminal } from "lucide-react";

const TerminalToolMessage: React.FC<TerminalToolProps> = ({
  className,
  script,
}) => {
  return (
    <div
      className={cn("flex items-center gap-2 text-sm text-blue-400", className)}
    >
      <span className="flex items-center gap-1 border p-1 rounded-md bg-gray-500/10">
        <Terminal className="w-4 h-4" />
      </span>
      <span>
        <code className="ml-1 text-blue-600 border p-1 rounded-md bg-gray-500/10">
          {script}
        </code>
      </span>
    </div>
  );
};

export default TerminalToolMessage;
