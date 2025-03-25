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
