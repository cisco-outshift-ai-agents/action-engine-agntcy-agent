import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
} from "react";
import { Tabs } from "@magnetic/tabs";
import TerminalSection, { TerminalTabConfig } from "./terminal-section";
import { PlusCircle, X } from "lucide-react";
import { TerminalDataZod } from "@/pages/session/types";

const TabbedTerminalContainer: React.FC = ({}) => {
  const [activeTab, setActiveTab] = useState<string>("terminal");
  const [tabs, setTabs] = useState<TerminalTabConfig[]>([
    {
      id: "terminal",
      title: "Terminal",
      workingDirectory: "~",
      isActive: true,
    },
  ]);
  const [terminalContent, setTerminalContent] = useState<string>("");
  const [terminalId, setTerminalId] = useState<string>("");
  const [workingDirectory, setWorkingDirectory] = useState<string>("");

  const [terminalBuffers, setTerminalBuffers] = useState<
    Record<string, string>
  >({
    terminal: "",
  });

  const [contentTimestamps, setContentTimestamps] = useState<
    Record<string, number>
  >({
    terminal: Date.now(),
  });

  const wsTerminalRef = useRef<WebSocket | null>(null);

  // Websocket connection terminal
  useEffect(() => {
    if (
      wsTerminalRef.current &&
      wsTerminalRef.current.readyState === WebSocket.OPEN
    ) {
      console.warn("WebSocket terminal is already connected");
      return;
    }
    const useLocal = true;
    const url = useLocal ? "localhost:7788" : window.location.host;
    const connectWebsocket = () => {
      const ws = new WebSocket(`ws://${url}/ws/terminal`);
      wsTerminalRef.current = ws;

      ws.onopen = () => {
        console.log("Connected to terminal websocket");
      };

      ws.onmessage = (event: MessageEvent) => {
        console.log("Received WebSocket terminal message:", event.data);
        const parsedData = TerminalDataZod.safeParse(JSON.parse(event.data));

        if (!parsedData.success) {
          console.error("Invalid terminal data:", parsedData.error);
          return;
        }

        const { summary, working_directory, terminal_id } = parsedData.data;

        setWorkingDirectory((prev) =>
          prev !== working_directory ? working_directory : prev
        );
        setTerminalId(terminal_id);

        // setTimeout(() => {
        //   setTerminalContent(`${summary}_${Date.now()}`);
        // }, 10);

        requestAnimationFrame(() => {
          setTerminalContent(`${summary}_${Date.now()}`);
        });

        setTerminalBuffers((prev) => ({
          ...prev,
          terminal: prev.terminal ? `${prev.terminal}\n${summary}` : summary,
        }));

        setContentTimestamps((prev) => ({
          ...prev,
          terminal: Date.now(),
        }));

        setTabs((prevTabs) =>
          prevTabs.map((tab) =>
            tab.id === "terminal"
              ? { ...tab, workingDirectory: working_directory }
              : tab
          )
        );
      };

      ws.onerror = (error) => console.error("WebSocket terminal error:", error);
      ws.onclose = () => {
        console.warn("Disconnected from terminal WebSocket");
        setTimeout(connectWebsocket, 3000);
      };
    };
    connectWebsocket();

    return () => {
      wsTerminalRef.current?.close();
    };
  }, []);

  // Update tabs when working directory changes

  useEffect(() => {
    console.log("initial TerminalID:", terminalId);
  }, []);
  0;
  useEffect(() => {
    if (workingDirectory) {
      setTabs((prevTabs) =>
        prevTabs.map((tab) =>
          tab.id === "terminal" ? { ...tab, workingDirectory } : tab
        )
      );
    }
  }, [workingDirectory]);

  useEffect(() => {
    if (terminalContent && terminalContent.trim()) {
      setTerminalBuffers((prev) => ({
        ...prev,
        terminal: prev.terminal
          ? `${prev.terminal}\n${terminalContent}`
          : terminalContent,
      }));

      setContentTimestamps((prev) => ({
        ...prev,
        terminal: Date.now(),
      }));
    }
  }, [terminalContent]);

  const createNewTab = useCallback(() => {
    const newTabId = `terminal-${tabs.length + 1}`;

    const updatedTabs = tabs.map((tab) => ({ ...tab, isActive: false }));

    setTabs([
      ...updatedTabs,
      {
        id: newTabId,
        title: `Terminal ${tabs.length + 1}`,
        workingDirectory: "~",
        isActive: true,
      },
    ]);

    setTerminalBuffers((prev) => ({
      ...prev,
      [newTabId]: "",
    }));

    setContentTimestamps((prev) => ({
      ...prev,
      [newTabId]: Date.now(),
    }));

    setActiveTab(newTabId);
  }, [tabs]);

  const switchTab = useCallback(
    (tabId: string) => {
      if (activeTab !== tabId) {
        setActiveTab(tabId);

        setTabs((prevTabs) =>
          prevTabs.map((tab) => ({
            ...tab,
            isActive: tab.id === tabId,
          }))
        );
      }
    },
    [activeTab]
  );

  //Close tab (We can't add the close button directly in Tabs.link because of the Magnetic framework, so we have one close button which works for the active tab )
  const closeTab = useCallback(
    (tabId: string) => {
      if (tabId === "terminal") {
        return;
      }

      const updatedTabs = tabs.filter((tab) => tab.id !== tabId);
      if (activeTab === tabId) {
        const newActiveTab = "terminal";
        setActiveTab(newActiveTab);

        updatedTabs.forEach((tab) => {
          tab.isActive = tab.id === newActiveTab;
        });
      }
      setTabs(updatedTabs);
      setTerminalBuffers((prev) => {
        const newBuffers = { ...prev };
        delete newBuffers[tabId];
        return newBuffers;
      });
      setContentTimestamps((prev) => {
        const newTimestamps = { ...prev };
        delete newTimestamps[tabId];
        return newTimestamps;
      });
    },
    [activeTab, tabs]
  );
  const handleContentUpdate = useCallback((id: string, content: string) => {
    if (!content.trim()) return;
    console.log("handle content update called with:", content);

    setTerminalBuffers((prev) => ({
      ...prev,
      [id]: prev[id] ? `${prev[id]}\n${content}` : content,
    }));

    setContentTimestamps((prev) => ({
      ...prev,
      [id]: Date.now(),
    }));

    if (!wsTerminalRef.current) {
      console.warn("WebSocket terminal is not connected");
      return;
    }

    if (wsTerminalRef.current.readyState !== WebSocket.OPEN) {
      console.warn("WebSocket is not open. Storing message in buffer.");
      setTimeout(() => {
        if (wsTerminalRef.current?.readyState === WebSocket.OPEN) {
          console.log("Sending buffered command:", content);
          wsTerminalRef.current.send(JSON.stringify({ command: content }));
        } else {
          console.error("WebSocket still not open. Command not sent.");
        }
      }, 500);
      return;
    }

    // Send the message if WebSocket is open
    wsTerminalRef.current.send(JSON.stringify({ command: content }));
  }, []);

  const terminalProps = useMemo(() => {
    return tabs.map((tab) => {
      const isActive = activeTab === tab.id;
      const isMainTerminal = tab.id === "terminal";
      return {
        key: tab.id,
        id: tab.id,
        isActive,
        isMainTerminal,
        currentContent:
          isMainTerminal && isActive ? terminalContent : undefined,
        buffer: terminalBuffers[tab.id] || "",
        tabWorkingDirectory: tab.workingDirectory,
        terminalIdentifier: isMainTerminal ? terminalId : tab.id,
        timestamp: contentTimestamps[tab.id] || Date.now(),
      };
    });
  }, [
    activeTab,
    tabs,
    terminalContent,
    terminalBuffers,
    terminalId,
    contentTimestamps,
  ]);

  const TabBar = () => (
    <div className="px-2 flex items-center justify-between">
      <div className="flex-1 flex">
        <Tabs kind="primary" className="flex-1">
          {tabs.map((tab) => (
            <Tabs.Link
              key={tab.id}
              href={`#/${tab.id}`}
              selected={activeTab === tab.id}
              onClick={(e: React.MouseEvent<HTMLAnchorElement>) => {
                e.preventDefault();
                switchTab(tab.id);
              }}
              className="text-[#D0D4D9] font-bold text-base leading-[22px] text-[#D0D4D9]"
            >
              {tab.title}
            </Tabs.Link>
          ))}
        </Tabs>
      </div>

      <div className="flex items-center">
        {tabs.map((tab) =>
          tab.id !== "terminal" && activeTab === tab.id ? (
            <button
              key={`close-${tab.id}`}
              onClick={() => closeTab(tab.id)}
              className="mx-1 text-[#D0D4D9] hover:text-white p-1 rounded"
              title={`Close ${tab.title}`}
            >
              <X size={18} />
            </button>
          ) : null
        )}

        <button
          className="text-[#D0D4D9] hover:text-white p-1 rounded"
          title="Add new Tab"
          onClick={createNewTab}
        >
          <PlusCircle size={18} />
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full rounded-lg border border-white/10 mt-2 bg-[#32363c]">
      <TabBar />

      {terminalProps.map((props) => (
        <div
          key={props.id}
          className={`flex-1 m-2 mt-0 overflow-hidden rounded-b-xl border border-white/10 bg-[#272a30] ${
            props.isActive ? "block" : "hidden"
          }`}
          style={{ height: "calc(100% - 48px)" }}
        >
          <TerminalSection
            key="main-terminal"
            content={props.currentContent}
            isVisible={props.isActive}
            terminalId={props.terminalIdentifier}
            workingDirectory={props.tabWorkingDirectory}
            contentBuffer={props.buffer}
            onContentUpdate={handleContentUpdate}
          />
        </div>
      ))}
    </div>
  );
};

export default TabbedTerminalContainer;
