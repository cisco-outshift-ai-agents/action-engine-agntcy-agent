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
import { ToolResultProps } from "@/pages/session/types";
import { cn } from "@/utils";
import { ArrowRight } from "lucide-react";

const ToolMessageResult: React.FC<ToolResultProps> = ({
  className,
  content,
}) => {
  return (
    <div
      className={cn("flex items-center gap-2 text-sm text-gray-300", className)}
    >
      <ArrowRight className="w-4 h-4" />
      <span>{content}</span>
    </div>
  );
};

export default ToolMessageResult;
