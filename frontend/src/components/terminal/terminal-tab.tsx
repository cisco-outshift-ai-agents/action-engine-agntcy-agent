import React, { useState, useEffect } from "react";
import { Tabs } from "@magnetic/tabs";
import TerminalSection from "./terminal-section";

const TabbedTerminalContainer: React.FC<TabbedTerminalContainerProps> = ({
  isTerminalOutput,

  terminalContent,
  terminalId,
  workingDirectory,
}) => {
  const [activeTab, setActiveTab] = useState<string>("terminal");

  useEffect(() => {
    if (isTerminalOutput) {
      setActiveTab("terminal");
    }
  }, [isTerminalOutput]);

  return (
    <div className="flex flex-col h-full rounded-lg border border-white/10 mt-2 bg-[#32363c]">
      <div className="px-2 ">
        <Tabs kind="primary">
          <Tabs.Link
            href="#/terminal"
            selected={activeTab === "terminal"}
            onClick={(e: React.MouseEvent<HTMLAnchorElement>) => {
              e.preventDefault();
              setActiveTab("terminal");
            }}
            className="text-[#D0D4D9] font-bold text-base leading-[22px] text-[#D0D4D9]"
          >
            Terminal
          </Tabs.Link>
        </Tabs>
      </div>

      {activeTab === "terminal" && (
        <div
          className="flex-1 m-2 mt-0 overflow-hidden rounded-b-xl border border-white/10 bg-[#272a30]"
          style={{ height: "calc(100% -60px)" }}
        >
          <TerminalSection
            content={terminalContent}
            isVisible={true}
            terminalId={terminalId}
            workingDirectory={workingDirectory}
          />
        </div>
      )}
    </div>
  );
};

export default TabbedTerminalContainer;

export interface TabbedTerminalContainerProps {
  isTerminalOutput: boolean;
  hasEmptyThought: boolean;
  isDone: boolean;
  terminalContent?: string;
  terminalId?: string;
  workingDirectory?: string;
}
