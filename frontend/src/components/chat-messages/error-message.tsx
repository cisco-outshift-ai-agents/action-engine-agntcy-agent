import { cn } from "@/utils";
import { AlertTriangle, AlertOctagon } from "lucide-react";

interface ErrorMessageProps {
  className?: string;
  error?: string | null;
  warnings?: string[] | null;
}

const ErrorMessage: React.FC<ErrorMessageProps> = ({
  className,
  error,
  warnings,
}) => {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {error && (
        <div className="flex items-start gap-2 text-sm text-red-400 bg-red-900/20 p-2 rounded">
          <AlertOctagon className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {warnings?.map((warning, index) => (
        <div
          key={index}
          className="flex items-start gap-2 text-sm text-yellow-400 bg-yellow-900/20 p-2 rounded"
        >
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{warning}</span>
        </div>
      ))}
    </div>
  );
};

export default ErrorMessage;
