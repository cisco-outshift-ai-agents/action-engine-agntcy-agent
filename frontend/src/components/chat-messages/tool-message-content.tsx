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
