import { BrowserToolProps } from "@/pages/session/types";
import { cn } from "@/utils";
import {
  Globe,
  MousePointer,
  KeyboardIcon,
  Camera,
  Code,
  ScrollText,
  LayoutGrid,
  X,
  RefreshCw,
} from "lucide-react";

const BrowserToolMessage: React.FC<BrowserToolProps> = ({
  className,
  action,
  url,
  index,
  text,
  script,
  scroll_amount,
  tab_id,
}) => {
  const getIcon = () => {
    switch (action) {
      case "navigate":
      case "new_tab":
        return <Globe className="w-4 h-4" />;
      case "click":
        return <MousePointer className="w-4 h-4" />;
      case "input_text":
        return <KeyboardIcon className="w-4 h-4" />;
      case "screenshot":
      case "get_html":
      case "get_text":
        return <Camera className="w-4 h-4" />;
      case "execute_js":
        return <Code className="w-4 h-4" />;
      case "scroll":
        return <ScrollText className="w-4 h-4" />;
      case "switch_tab":
        return <LayoutGrid className="w-4 h-4" />;
      case "close_tab":
        return <X className="w-4 h-4" />;
      case "refresh":
        return <RefreshCw className="w-4 h-4" />;
      default:
        return <Globe className="w-4 h-4" />;
    }
  };

  const getMessage = () => {
    switch (action) {
      case "navigate":
        return `Navigating to ${url}`;
      case "click":
        return `Clicking element ${index}`;
      case "input_text":
        return `Entering text "${text}" into element ${index}`;
      case "screenshot":
        return "Taking screenshot";
      case "get_html":
        return "Getting page HTML";
      case "get_text":
        return "Getting page text";
      case "execute_js":
        return `Executing JavaScript: ${script}`;
      case "scroll":
        return `Scrolling ${
          scroll_amount && scroll_amount > 0 ? "down" : "up"
        } ${Math.abs(scroll_amount || 0)}px`;
      case "switch_tab":
        return `Switching to tab ${tab_id}`;
      case "new_tab":
        return `Opening new tab: ${url}`;
      case "close_tab":
        return "Closing current tab";
      case "refresh":
        return "Refreshing page";
      default:
        return `Unknown browser action: ${action}`;
    }
  };

  return (
    <div
      className={cn("flex items-center gap-2 text-sm text-blue-400", className)}
    >
      <span className="flex items-center gap-1 border p-1 rounded-md bg-gray-500/10">
        {getIcon()}
      </span>
      <span>{getMessage()}</span>
    </div>
  );
};

export default BrowserToolMessage;
