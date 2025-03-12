import { Layout } from "@/components/ui/layout/page";
import { Container } from "@magnetic/container";
import { useState } from "react";
import InteractiveVNC from "@/components/interactive-vnc";
import ChatSection from "@/components/chat-section";
import TabbedTerminalContainer from "@/components/terminal/terminal-tab";

const SessionPage = () => {
  // Terminal state
  const [terminalContent, setTerminalContent] = useState<string>("");
  const [isTerminal, setIsTerminal] = useState<boolean>(false);
  const [hasEmptyThought, setHasEmptyThought] = useState<boolean>(false);
  const [isDone, setIsDone] = useState<boolean>(false);
  const [terminalId, setTerminalId] = useState<string>("");
  const [workingDirectory, setWorkingDirectory] = useState<string>("");

  // Function to handle terminal content updates from ChatSection
  const handleTerminalUpdate = (
    content: string,
    isTerminal: boolean,
    hasEmptyThought: boolean,
    isDone: boolean,
    terminalId?: string,
    workingDirectory?: string
  ) => {
    console.log("Terminal update received:", {
      content: content.substring(0, 50) + "...",
      isTerminal,
      hasEmptyThought,
      isDone,
      terminalId,
      workingDirectory,
    });

    setTerminalContent(content);
    setIsTerminal(isTerminal);
    setHasEmptyThought(hasEmptyThought);
    setIsDone(isDone);
    setTerminalId(terminalId || "");
    setWorkingDirectory(workingDirectory || "");
  };

  return (
    <Layout>
      <Container className="h-full">
        <div className="flex h-full gap-3">
          <div className="w-[70%] flex flex-col gap-2">
            <div
              className="rounded-lg border border-white/10 bg-[#32363c] overflow-hidden"
              style={{ height: "60%" }}
            >
              <InteractiveVNC />
            </div>

            <div
              className="rounded-lg overflow-hidden"
              style={{ height: "40%" }}
            >
              <TabbedTerminalContainer
                isTerminalOutput={isTerminal}
                hasEmptyThought={hasEmptyThought}
                isDone={isDone}
                terminalContent={terminalContent}
                terminalId={terminalId}
                workingDirectory={workingDirectory}
              />
            </div>
          </div>

          <div className="w-[30%]">
            <ChatSection onTerminalUpdate={handleTerminalUpdate} />
          </div>
        </div>
      </Container>
    </Layout>
  );
};

export default SessionPage;
