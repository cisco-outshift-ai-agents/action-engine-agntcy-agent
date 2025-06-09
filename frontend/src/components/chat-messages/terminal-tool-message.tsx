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
# SPDX-License-Identifier: Apache-2.0
*/
import { TerminalToolProps } from "@/pages/session/types";
import { cn } from "@/utils";
import { Terminal } from "lucide-react";
import React from "react";

const TerminalToolMessage: React.FC<TerminalToolProps> = ({
  className,
  action,
  script,
  terminal_id,
  message,
}) => {
  // Generate appropriate content based on action type
  const getContent = () => {
    if (action === "create") {
      return terminal_id ? 
        `Created terminal session with ID: ${terminal_id}` : 
        message || "Creating new terminal session";
    } else if (action === "run" && script) {
      return (
        <code className="ml-1 text-blue-600 border p-1 rounded-md bg-gray-500/10 text-xs">
          {script}
        </code>
      );
    } else if (action === "switch") {
      return `Switching to terminal${terminal_id ? ` ID: ${terminal_id}` : ''}`;
    } else if (action === "close") {
      return `Closing terminal${terminal_id ? ` ID: ${terminal_id}` : ''}`;
    } else if (action === "list") {
      return "Listing terminal sessions";
    } else if (script) {
      // Fallback for when action isn't specified but script is
      return (
        <code className="ml-1 text-blue-600 border p-1 rounded-md bg-gray-500/10 text-xs">
          {script}
        </code>
      );
    } else {

      return message || "Terminal operation";
    }
  };

  return (
    <div
      className={cn("flex items-center gap-2 text-sm text-blue-400", className)}
    >
      <span className="flex items-center gap-1 border p-1 rounded-md bg-gray-500/10">
        <Terminal className="w-4 h-4" />
      </span>
      <span>{getContent()}</span>
    </div>
  );
};

export default TerminalToolMessage;