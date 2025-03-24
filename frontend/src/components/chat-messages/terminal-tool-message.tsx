import { cn } from "@/utils";
import { Terminal } from "lucide-react";
import { TerminalToolProps } from "./types";

const TerminalToolMessage: React.FC<TerminalToolProps> = ({
  className,
  command,
}) => {
  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm text-green-400",
        className
      )}
    >
      <Terminal className="w-4 h-4" />
      <span>Executing: {command}</span>
    </div>
  );
};

export default TerminalToolMessage;
