import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal as XTerm } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import { extractHostname } from "@/utils";
interface TerminalComponentProps {
  content?: string;
  isVisible: boolean;
  terminalId?: string;
  workingDirectory?: string;
  contentBuffer: string;
  onContentUpdate?: (id: string, content: string) => void;
}

// Create a persistent terminal instance cache
const terminalInstances: Record<
  string,
  {
    term: XTerm;
    fitAddon: FitAddon;
    mounted: boolean;
    processedContents: Set<string>;
  }
> = {};

const TerminalSection = ({
  content,
  isVisible,
  terminalId,
  workingDirectory,
  contentBuffer,
  onContentUpdate,
}: TerminalComponentProps): JSX.Element => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const instanceIdRef = useRef<string>(terminalId || "unknown");
  const [domReady, setDomReady] = useState(false);
  const currentInputRef = useRef("");
  const cursorPosRef = useRef(0);
  const commandHistoryRef = useRef<string[]>([]);
  const historyPosRef = useRef(-1);

  // Wait for DOM to be ready
  useEffect(() => {
    if (isVisible && terminalRef.current) {
      const timer = setTimeout(() => {
        setDomReady(true);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isVisible]);

  // Get current terminal instance from cache or create a new one
  const getTerminalInstance = useCallback(() => {
    const id = instanceIdRef.current;
    if (!terminalInstances[id]) {
      console.log(`Creating new terminal instance for ${id}`);
      const term = new XTerm({
        cursorBlink: true,
        scrollback: 10000,
        theme: {
          background: "#1a1a1a",
          foreground: "#00ff00",
          cursor: "#00ff00",
        },
        fontSize: 14,
        fontFamily: "Menlo, Monaco, Consolas, monospace",
        lineHeight: 1.2,
        convertEol: true,
        cols: 80,
        rows: 24,
      });

      const fitAddon = new FitAddon();
      term.loadAddon(fitAddon);

      terminalInstances[id] = {
        term,
        fitAddon,
        mounted: false,
        processedContents: new Set(),
      };
    }

    return terminalInstances[id];
  }, []);

  console.log("Updated currentInput:", currentInputRef.current);

  // Handle user input and special keys and history management
  const handleUserInput = (data: string, term: XTerm) => {
    if (data === "\r") {
      const command = currentInputRef.current.trim();
      if (command.length > 0) {
        commandHistoryRef.current.push(command);
        historyPosRef.current = -1;

        term.write("\r\n");
        term.write(`Command entered: ${command}`);
        term.write("\r\n");
        if (onContentUpdate) {
          onContentUpdate(terminalId || "terminal", command);
        }
        currentInputRef.current = "";

        cursorPosRef.current = 0;

        const hostname = extractHostname(content || "");
        term.write(`${hostname}:${workingDirectory}# `);
      }
      // Backspace key
    } else if (data === "\u007F") {
      if (cursorPosRef.current > 0) {
        const newInput =
          currentInputRef.current.substring(0, cursorPosRef.current - 1) +
          currentInputRef.current.substring(cursorPosRef.current);
        currentInputRef.current = newInput;
        cursorPosRef.current--;

        term.write("\b \b");

        term.write("\u001b[K");
        term.write(newInput.substring(cursorPosRef.current));

        const moveBack = newInput.length - cursorPosRef.current;
        if (moveBack > 0) {
          term.write(`\u001b[${moveBack}D`);
        }
      }
      // Up Arrow Key
    } else if (data === "\u001b[A") {
      if (commandHistoryRef.current.length > 0) {
        const newPos =
          historyPosRef.current === -1
            ? commandHistoryRef.current.length - 1
            : Math.max(0, historyPosRef.current - 1);

        historyPosRef.current = newPos;
        const historyCommand = commandHistoryRef.current[newPos];

        term.write("\u001b[2K\r");
        const hostname = extractHostname(content || "");
        term.write(`${hostname}:${workingDirectory}# ` + historyCommand);
        currentInputRef.current = historyCommand;

        cursorPosRef.current = historyCommand.length;
      }
      // Down Arrow Key
    } else if (data === "\u001b[B") {
      if (commandHistoryRef.current.length > 0 && historyPosRef.current >= 0) {
        const newPos =
          historyPosRef.current + 1 >= commandHistoryRef.current.length
            ? -1
            : historyPosRef.current + 1;

        term.write("\r");
        const hostname = extractHostname(content || "");
        term.write(`${hostname}:${workingDirectory}# `);
        term.write("\u001b[K");

        if (newPos === -1) {
          currentInputRef.current = "";
          cursorPosRef.current = 0;
        } else {
          const historyCommand = commandHistoryRef.current[newPos];
          term.write(historyCommand);
          currentInputRef.current = historyCommand;

          cursorPosRef.current = historyCommand.length;
        }

        historyPosRef.current = newPos;
      }
      // Right Arrow Key
    } else if (data === "\u001b[C") {
      if (cursorPosRef.current < currentInputRef.current.length) {
        term.write("\u001b[C");
        cursorPosRef.current++;
      } else {
        console.warn("Cursor at the end, cannot move right!");
      }
      //Left Arrow Key
    } else if (data === "\u001b[D") {
      if (cursorPosRef.current > 0) {
        term.write("\u001b[D");
        cursorPosRef.current--;
      }
      // Character input
    } else if (data >= " " && data <= "~") {
      const newInput =
        currentInputRef.current.substring(0, cursorPosRef.current) +
        data +
        currentInputRef.current.substring(cursorPosRef.current);

      currentInputRef.current = newInput;
      term.write("\u001b[K");
      term.write(newInput.substring(cursorPosRef.current));

      const moveBack = newInput.length - cursorPosRef.current - 1;
      if (moveBack > 0) {
        term.write(`\u001b[${moveBack}D`);
      }

      cursorPosRef.current++;
    }
  };

  // Terminal initialization
  useEffect(() => {
    if (!isVisible || !terminalRef.current || !domReady) return;

    const id = instanceIdRef.current;
    console.log(`Setting up terminal ${id}`);

    try {
      const instance = getTerminalInstance();
      const { term, fitAddon } = instance;

      // If already mounted, just reattach
      if (instance.mounted) {
        if (term.element && term.element.parentNode !== terminalRef.current) {
          console.log(`Reattaching terminal ${id} to DOM`);
          if (terminalRef.current) {
            terminalRef.current.innerHTML = "";
            terminalRef.current.appendChild(term.element);
          }
        }
      } else {
        // First time initialization
        console.log(`Mounting terminal ${id} to DOM`);
        term.open(terminalRef.current);

        term.onData((data) => {
          handleUserInput(data, term);
        });

        // Write initial buffer content if available
        if (contentBuffer && contentBuffer.trim()) {
          const contentLines = contentBuffer.split("\n");
          contentLines.forEach((line, index) => {
            // Extract content without timestamp if present
            const actualLine = line.includes("_")
              ? line.substring(0, line.lastIndexOf("_"))
              : line;

            if (actualLine.trim()) {
              term.write(`${actualLine}`);
              if (index < contentLines.length - 1) {
                term.write("\r\n");
              }
            }
          });

          if (terminalId && workingDirectory && !contentBuffer.endsWith("#")) {
            term.write(`\r\nroot@${terminalId}:${workingDirectory}# `);
          }
        } else {
          // Just write the initial prompt
          const hostname = extractHostname(content || "");
          term.write(`${hostname}:${workingDirectory}# `);
        }

        instance.mounted = true;
      }

      // Fit terminal to container
      setTimeout(() => {
        if (fitAddon && terminalRef.current) {
          fitAddon.fit();
          term.scrollToBottom();
        }
      }, 100);

      // Handle window resize
      const handleResize = () => {
        if (fitAddon) fitAddon.fit();
      };

      window.addEventListener("resize", handleResize);

      return () => {
        window.removeEventListener("resize", handleResize);
      };
    } catch (err) {
      console.error("Error initializing terminal:", err);
    }
  }, [
    isVisible,
    domReady,
    getTerminalInstance,
    contentBuffer,
    terminalId,
    workingDirectory,
  ]);

  // Process new content
  useEffect(() => {
    if (!content || !isVisible || !domReady) return;

    const instance = getTerminalInstance();
    const { term, processedContents } = instance;

    if (!term) return;

    // Extract actual content and create a unique key that includes the timestamp
    const contentKey = content;
    const actualContent = content.includes("_")
      ? content.substring(0, content.lastIndexOf("_"))
      : content;

    // Skip if already processed this exact content with this exact timestamp
    if (processedContents.has(contentKey)) {
      return;
    }

    // Mark as processed
    processedContents.add(contentKey);

    // Write to terminal
    console.log("Writing content to terminal:", actualContent);
    term.write(`\r\n${actualContent}`);

    // Add prompt if needed
    setTimeout(() => {
      term.scrollToBottom();
      const hostname = extractHostname(content || "");
      term.write(`\r\n${hostname}:${workingDirectory || "~"}# `);
    }, 50);
  }, [
    content,
    isVisible,
    domReady,
    getTerminalInstance,
    terminalId,
    workingDirectory,
  ]);

  return (
    <div className="flex flex-col h-full bg-[#1a1a1a] rounded-b-lg">
      <div ref={terminalRef} className="flex-1 overflow-auto p-1" />
    </div>
  );
};

export default TerminalSection;

export interface TerminalTabConfig {
  id: string;
  title: string;
  workingDirectory: string;
  isActive: boolean;
}
