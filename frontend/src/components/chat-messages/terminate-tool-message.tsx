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
