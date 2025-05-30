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
import React from "react";

interface ToolMessageContentProps {
  content: string;
}

const ToolMessageContent: React.FC<ToolMessageContentProps> = ({ content }) => {
  if (!content) return null;

  return (
    <details className="w-full">
      <summary className="text-sm text-gray-400 hover:text-gray-300 cursor-pointer">
        View details
      </summary>
      <div className="mt-2 pl-6 flex gap-2 font-mono overflow-auto">
        🛠️
        <p className="text-sm text-gray-400">{content}</p>
      </div>
    </details>
  );
};

export default ToolMessageContent;
