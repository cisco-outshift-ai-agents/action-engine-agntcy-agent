import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
} from "react";
import { Tabs } from "@magnetic/tabs";
import TerminalSection from "./terminal-section";
import { PlusCircle, X } from "lucide-react";
import { TerminalDataZod } from "@/pages/session/types";

// Store all active WebSocket connections globally
const globalWebSocketMap: Record<string, WebSocket> = {};

const TabbedTerminalContainer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("terminal");

  const [tabs, setTabs] = useState<TerminalTabConfig[]>([
    {
      id: "terminal",
      title: "Terminal",
      workingDirectory: "~",
      terminalId: null,
      isActive: true,
    },
  ]);

  // Track terminal buffers by tab ID and track timestamps to avoid duplicate content

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

  // Track WebSocket connections per tab and their associated terminal IDs and connect a WebSocket for a specific tab/terminal
  const webSocketMapRef = useRef<Record<string, WebSocket>>({});
  const terminalIdMapRef = useRef<Record<string, string>>({});
  const initialSetupDoneRef = useRef<boolean>(false);

  const connectWebsocketForTab = useCallback(
    (tabId: string, initialTerminalId: string | null = null) => {
      if (
        webSocketMapRef.current[tabId] &&
        webSocketMapRef.current[tabId].readyState <= WebSocket.OPEN
      ) {
        console.log(
          `WebSocket for tab ${tabId} is already connecting/connected`
        );
        return webSocketMapRef.current[tabId];
      }

      console.log(`Creating new WebSocket connection for tab ${tabId}`);

      const useLocal = true;
      const url = useLocal ? "localhost:7788" : window.location.host;
      const ws = new WebSocket(`ws://${url}/ws/terminal`);

      webSocketMapRef.current[tabId] = ws;
      globalWebSocketMap[tabId] = ws;

      ws.onopen = () => {
        console.log(`Connected to terminal websocket for tab ${tabId}`);

        if (initialTerminalId) {
          terminalIdMapRef.current[tabId] = initialTerminalId;
          console.log(
            `Associating terminal ID ${initialTerminalId} with tab ${tabId}`
          );
        }
      };

      ws.onmessage = (event: MessageEvent) => {
        console.log(`Received terminal message for tab ${tabId}:`, event.data);
        try {
          const parsedData = TerminalDataZod.safeParse(JSON.parse(event.data));

          if (!parsedData.success) {
            console.error("Invalid terminal data:", parsedData.error);
            return;
          }

          const { summary, working_directory, terminal_id } = parsedData.data;

          if (terminal_id) {
            const isInitialTerminalAssignment =
              tabId === "terminal" &&
              !terminalIdMapRef.current[tabId] &&
              !initialSetupDoneRef.current;

            if (isInitialTerminalAssignment) {
              initialSetupDoneRef.current = true;

              terminalIdMapRef.current[tabId] = terminal_id;

              console.log(
                `Initial terminal ID ${terminal_id} assigned to tab ${tabId}`
              );

              setTabs((prevTabs) =>
                prevTabs.map((tab) =>
                  tab.id === tabId
                    ? {
                        ...tab,
                        terminalId: terminal_id,
                        workingDirectory: working_directory,
                      }
                    : tab
                )
              );
            } else {
              const existingTab = Object.entries(terminalIdMapRef.current).find(
                ([_, tid]) => tid === terminal_id
              )?.[0];

              const targetTabId = existingTab || tabId;

              setTabs((prevTabs) =>
                prevTabs.map((tab) =>
                  tab.id === targetTabId
                    ? {
                        ...tab,
                        terminalId: terminal_id,
                        workingDirectory: working_directory,
                      }
                    : tab
                )
              );

              if (!existingTab && !terminalIdMapRef.current[targetTabId]) {
                terminalIdMapRef.current[targetTabId] = terminal_id;
                console.log(
                  `Assigned terminal ID ${terminal_id} to tab ${targetTabId}`
                );
              }
            }

            if (summary) {
              const targetTabForContent =
                Object.entries(terminalIdMapRef.current).find(
                  ([_, tid]) => tid === terminal_id
                )?.[0] || tabId;

              setTerminalBuffers((prev) => ({
                ...prev,
                [targetTabForContent]: prev[targetTabForContent]
                  ? `${prev[targetTabForContent]}\n${summary}`
                  : summary,
              }));

              setContentTimestamps((prev) => ({
                ...prev,
                [targetTabForContent]: Date.now(),
              }));
            }
          }
        } catch (error) {
          console.error("Error processing message:", error);
        }
      };

      ws.onerror = (error) => {
        console.error(`WebSocket error for tab ${tabId}:`, error);
      };

      ws.onclose = () => {
        console.warn(`WebSocket for tab ${tabId} disconnected`);

        // Clean up references
        delete webSocketMapRef.current[tabId];
        delete globalWebSocketMap[tabId];

        // Try to reconnect only if the tab still exists
        setTimeout(() => {
          setTabs((prevTabs) => {
            if (prevTabs.some((tab) => tab.id === tabId)) {
              connectWebsocketForTab(tabId, terminalIdMapRef.current[tabId]);
            }
            return prevTabs;
          });
        }, 3000);
      };

      return ws;
    },
    []
  );

  // Initialize the default terminal tab only once
  useEffect(() => {
    if (webSocketMapRef.current["terminal"] || initialSetupDoneRef.current) {
      console.log(
        "WebSocket for default terminal tab already exists or setup is complete"
      );
      return;
    }

    console.log("Initializing WebSocket for default terminal tab");
    connectWebsocketForTab("terminal");

    // Cleanup WebSocket connections
    return () => {
      console.log("Cleaning up WebSocket connections");
      Object.values(globalWebSocketMap).forEach((socket) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          console.log("Closing WebSocket connection");
          socket.close();
        }
      });
    };
  }, [connectWebsocketForTab]);

  const createNewTab = useCallback(async () => {
    try {
      const newTabId = `terminal-${Date.now()}`;

      setTabs((prevTabs) => {
        const updatedTabs = prevTabs.map((tab) => ({
          ...tab,
          isActive: false,
        }));
        return [
          ...updatedTabs,
          {
            id: newTabId,
            title: `Terminal ${updatedTabs.length + 1}`,
            workingDirectory: "~",
            terminalId: null,
            isActive: true,
          },
        ];
      });

      setActiveTab(newTabId);

      setTerminalBuffers((prev) => ({
        ...prev,
        [newTabId]: "",
      }));

      setContentTimestamps((prev) => ({
        ...prev,
        [newTabId]: Date.now(),
      }));

      // Connect a WebSocket for this new tab and associate with terminal ID
      connectWebsocketForTab(newTabId);
    } catch (error) {
      console.error("Error creating new terminal tab:", error);
    }
  }, [connectWebsocketForTab]);

  // Switch between tabs
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

  // Close a tab and update the titles of the remaining tabs to maintain sequence
  const closeTab = useCallback(
    (tabId: string) => {
      if (tabId === "terminal") {
        return;
      }

      if (webSocketMapRef.current[tabId]) {
        webSocketMapRef.current[tabId].close();
        delete webSocketMapRef.current[tabId];
        delete globalWebSocketMap[tabId];
      }

      if (activeTab === tabId) {
        setActiveTab("terminal");
      }

      setTabs((prevTabs) => {
        const filteredTabs = prevTabs.filter((tab) => tab.id !== tabId);

        const updatedTabs = filteredTabs.map((tab, index) => ({
          ...tab,
          title: index === 0 ? "Terminal" : `Terminal ${index + 1}`,
        }));

        return updatedTabs;
      });

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

      delete terminalIdMapRef.current[tabId];
    },
    [activeTab]
  );

  // Handle command input
  const handleContentUpdate = useCallback(
    (tabId: string, content: string) => {
      if (!content.trim()) return;

      // Get the terminal ID for this tab from our mapping
      const terminalId = terminalIdMapRef.current[tabId];
      if (!terminalId) {
        console.warn(`No terminal ID found for tab ${tabId}`);
        return;
      }

      console.log(
        `Sending command "${content}" for tab ${tabId} with terminal ID ${terminalId}`
      );

      // Get the WebSocket for this tab
      const ws = webSocketMapRef.current[tabId];
      if (!ws) {
        console.warn(`No WebSocket found for tab ${tabId}`);
        return;
      }

      if (ws.readyState !== WebSocket.OPEN) {
        console.warn(
          `WebSocket for tab ${tabId} is not open (state: ${ws.readyState})`
        );

        if (ws.readyState === WebSocket.CLOSED) {
          connectWebsocketForTab(tabId, terminalId);
        }

        setTimeout(() => {
          const ws = webSocketMapRef.current[tabId];
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(
              JSON.stringify({
                command: content,
                terminal_id: terminalId,
              })
            );
          } else {
            console.error(`Still unable to send command for tab ${tabId}`);
          }
        }, 1000);

        return;
      }

      ws.send(
        JSON.stringify({
          command: content,
          terminal_id: terminalId,
        })
      );
    },
    [connectWebsocketForTab]
  );

  const terminalProps = useMemo(() => {
    return tabs.map((tab) => {
      const isActive = activeTab === tab.id;
      return {
        key: tab.id,
        id: tab.id,
        isActive,
        buffer: terminalBuffers[tab.id] || "",
        tabWorkingDirectory: tab.workingDirectory,
        terminalIdentifier: tab.terminalId || tab.id,
        timestamp: contentTimestamps[tab.id] || Date.now(),
      };
    });
  }, [activeTab, tabs, terminalBuffers, contentTimestamps]);

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
              className="text-[#D0D4D9] font-bold text-base leading-[22px]"
            >
              {`${tab.title}${tab.terminalId ? ` (${tab.terminalId})` : ""}`}
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
            key={props.id}
            isVisible={props.isActive}
            terminalId={props.terminalIdentifier}
            workingDirectory={props.tabWorkingDirectory}
            contentBuffer={props.buffer}
            onContentUpdate={(content) =>
              handleContentUpdate(props.id, content)
            }
          />
        </div>
      ))}
    </div>
  );
};

export default TabbedTerminalContainer;

export interface TerminalTabConfig {
  id: string;
  title: string;
  workingDirectory: string;
  isActive: boolean;
  terminalId?: string | null;
}
