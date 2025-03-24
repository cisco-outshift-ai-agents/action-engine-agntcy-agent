import { Button } from "@magnetic/button";
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
    <div className="flex gap-4 p-4">
      <Button
        onClick={analyzeEventLog}
        disabled={isAnalyzing}
        className="bg-green-500 hover:bg-green-600 text-white"
      >
        {isAnalyzing ? "Analyzing..." : "Analyze Event Log"}
      </Button>
    </div>
  );
};

export default LearningSectionControls;
