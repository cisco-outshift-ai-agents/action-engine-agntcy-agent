import { TerminateToolProps } from "@/pages/session/types";
import { cn } from "@/utils";
import { AlertTriangle, CheckCircle } from "lucide-react";

const TerminateToolMessage: React.FC<TerminateToolProps> = ({
  className,
  status,
  reason,
}) => {
  return (
    <div
      className={cn(
        "flex items-center gap-1 text-sm",
        status === "success" ? "text-green-400" : "text-red-400",
        className
      )}
    >
      <span className="flex items-center gap-1 border p-1 rounded-md bg-gray-500/10">
        {status === "success" ? (
          <CheckCircle className="w-4 h-4" />
        ) : (
          <AlertTriangle className="w-4 h-4" />
        )}
      </span>
      <span>
        {status === "success" ? "Task completed" : "Task failed"}
        {reason && `: ${reason}`}
      </span>
    </div>
  );
};

export default TerminateToolMessage;
