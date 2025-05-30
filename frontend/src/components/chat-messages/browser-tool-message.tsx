/*
# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0"
*/
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
        return `Entering text "${text?.substring(0, 6)}${
          (text?.length || 0) > 6 ? "..." : ""
        }" into element ${index}`;
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
      <span>
        <code className="ml-1 text-blue-600 border p-1 rounded-md bg-gray-500/10 text-xs">
          {getMessage()}
        </code>
      </span>
    </div>
  );
};

export default BrowserToolMessage;
