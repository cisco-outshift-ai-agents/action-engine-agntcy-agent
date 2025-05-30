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
