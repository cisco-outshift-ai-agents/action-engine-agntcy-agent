import { cn } from "@/utils";
import { AlertTriangle, CheckCircle } from "lucide-react";
import { TerminateToolProps } from "./types";

const TerminateToolMessage: React.FC<TerminateToolProps> = ({
  className,
  status,
  reason,
}) => {
  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm",
        status === "success" ? "text-green-400" : "text-red-400",
        className
      )}
    >
      {status === "success" ? (
        <CheckCircle className="w-4 h-4" />
      ) : (
        <AlertTriangle className="w-4 h-4" />
      )}
      <span>
        {status === "success" ? "Task completed" : "Task failed"}
        {reason && `: ${reason}`}
      </span>
    </div>
  );
};

export default TerminateToolMessage;
