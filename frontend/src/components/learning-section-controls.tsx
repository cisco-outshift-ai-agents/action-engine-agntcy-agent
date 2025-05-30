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
import { useState } from "react";

interface LearningSectionControlsProps {
  nnId?: string;
}

const LearningSectionControls: React.FC<LearningSectionControlsProps> = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const analyzeEventLog = async () => {
    setIsAnalyzing(true);
    try {
      const response = await fetch(
        `http://localhost:7788/api/event-log/analyze`,
        {
          method: "POST",
        }
      );
      const data = await response.json();
      console.log({ data });
      alert(data.summarized_result);

      if (data.error) {
        console.error("Error analyzing event log:", data.error);
        alert("Failed to analyze event log: " + data.error);
      } else {
        console.log("Analysis result:", data.analyzed_result);
      }
    } catch (error) {
      console.error("Error analyzing event log:", error);
      alert("Failed to analyze event log");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="flex gap-4">
      <button
        onClick={analyzeEventLog}
        disabled={isAnalyzing}
        className={
          "flex gap-2 text-sm items-center rounded-lg px-2 py-1 cursor-pointer border-2 border-white/10 bg-white/10 hover:bg-white/20 text-white font-medium"
        }
      >
        {isAnalyzing ? "Analyzing..." : "Analyze Event Log"}
      </button>
    </div>
  );
};

export default LearningSectionControls;
