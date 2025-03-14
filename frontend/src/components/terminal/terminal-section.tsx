import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal as XTerm } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";

interface TerminalComponentProps {
  content?: string;
  isVisible: boolean;
  terminalId?: string;
  workingDirectory?: string;
  contentBuffer: string;
  onContentUpdate?: (id: string, content: string) => void;
}

// Create a persistent terminal instance cache to prevent recreation
const terminalInstances: Record<
  string,
  {
    term: XTerm;
    fitAddon: FitAddon;
    mounted: boolean;
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
  const previousContentRef = useRef<string>("");
  const [domReady, setDomReady] = useState(false);
  const [currentInput, setCurrentInput] = useState("");
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
      };
    }

    return terminalInstances[id];
  }, []);

  // Handle user input and special keys and history management
  const handleUserInput = (data: string, term: XTerm) => {
    if (data === "\r") {
      const command = currentInput;
      if (command.trim()) {
        commandHistoryRef.current.push(command);
        historyPosRef.current = -1;

        term.write("\r\n");
        term.write(`Command entered: ${command}`);
        term.write("\r\n");
        if (onContentUpdate) {
          onContentUpdate(terminalId || "terminal", command);
        }
        setCurrentInput("");
        cursorPosRef.current = 0;

        const hostname = terminalId || "unknown";
        const dir = workingDirectory || "~";
        term.write(`root@${hostname}:${dir}# `);
      }
    } else if (data === "\u007F") {
      if (cursorPosRef.current > 0) {
        const newInput =
          currentInput.substring(0, cursorPosRef.current - 1) +
          currentInput.substring(cursorPosRef.current);

        term.write("\b");

        term.write("\u001b[K");
        term.write(newInput.substring(cursorPosRef.current - 1));

        const moveBack = newInput.length - cursorPosRef.current + 1;
        if (moveBack > 0) {
          term.write(`\u001b[${moveBack}D`);
        }

        setCurrentInput(newInput);
        cursorPosRef.current--;
      }
    } else if (data === "\u001b[A") {
      if (commandHistoryRef.current.length > 0) {
        const newPos =
          historyPosRef.current === -1
            ? commandHistoryRef.current.length - 1
            : Math.max(0, historyPosRef.current - 1);

        historyPosRef.current = newPos;

        term.write("\r");
        term.write(
          `root@${terminalId || "unknown"}:${workingDirectory || "~"}# `
        );
        term.write("\u001b[K");

        const historyCommand = commandHistoryRef.current[newPos];
        term.write(historyCommand);

        setCurrentInput(historyCommand);
        cursorPosRef.current = historyCommand.length;
      }
    } else if (data === "\u001b[B") {
      if (commandHistoryRef.current.length > 0 && historyPosRef.current >= 0) {
        const newPos =
          historyPosRef.current + 1 >= commandHistoryRef.current.length
            ? -1
            : historyPosRef.current + 1;

        term.write("\r");
        term.write(
          `root@${terminalId || "unknown"}:${workingDirectory || "~"}# `
        );
        term.write("\u001b[K");

        if (newPos === -1) {
          setCurrentInput("");
          cursorPosRef.current = 0;
        } else {
          const historyCommand = commandHistoryRef.current[newPos];
          term.write(historyCommand);
          setCurrentInput(historyCommand);
          cursorPosRef.current = historyCommand.length;
        }

        historyPosRef.current = newPos;
      }
    } else if (data === "\u001b[C") {
      if (cursorPosRef.current < currentInput.length) {
        term.write("\u001b[C");
        cursorPosRef.current++;
      }
    } else if (data === "\u001b[D") {
      if (cursorPosRef.current > 0) {
        term.write("\u001b[D");
        cursorPosRef.current--;
      }
    } else if (data >= " " && data <= "~") {
      const newInput =
        currentInput.substring(0, cursorPosRef.current) +
        data +
        currentInput.substring(cursorPosRef.current);

      term.write(data);
      term.write(currentInput.substring(cursorPosRef.current));

      const moveBack = currentInput.length - cursorPosRef.current;
      if (moveBack > 0) {
        term.write(`\u001b[${moveBack}D`);
      }

      setCurrentInput(newInput);
      cursorPosRef.current++;
    }
  };

  useEffect(() => {
    if (isVisible && terminalRef.current && domReady) {
      const id = instanceIdRef.current;
      console.log(`Setting up terminal ${id}`);

      try {
        const instance = getTerminalInstance();
        const { term, fitAddon } = instance;

        // Only open and setup the terminal if it's not already mounted
        if (!instance.mounted) {
          console.log(`Mounting terminal ${id} to DOM`);
          term.open(terminalRef.current);

          term.onData((data) => {
            handleUserInput(data, term);
          });

          if (contentBuffer) {
            const contentLines = contentBuffer.split("\n");
            contentLines.forEach((line, index) => {
              term.write(`${line}`);
              if (index < contentLines.length - 1) {
                term.write("\r\n");
              }
            });

            if (
              terminalId &&
              workingDirectory &&
              !contentBuffer.endsWith("#")
            ) {
              term.write(`\r\nroot@${terminalId}:${workingDirectory}# `);
            }
          } else {
            const hostname = terminalId || "unknown";
            const dir = workingDirectory || "~";
            term.write(`root@${hostname}:${dir}# `);
          }

          instance.mounted = true;
        } else {
          if (term.element && term.element.parentNode !== terminalRef.current) {
            console.log(`Reattaching terminal ${id} to DOM`);
            if (terminalRef.current) {
              terminalRef.current.innerHTML = "";
              terminalRef.current.appendChild(term.element);
            }
          }
        }

        setTimeout(() => {
          try {
            if (fitAddon && terminalRef.current) {
              fitAddon.fit();
              term.scrollToBottom();
            }
          } catch (err) {
            console.error("Error fitting terminal:", err);
          }
        }, 500);

        const handleResize = () => {
          try {
            if (fitAddon) {
              fitAddon.fit();
            }
          } catch (err) {
            console.error("Error during resize:", err);
          }
        };

        window.addEventListener("resize", handleResize);

        return () => {
          window.removeEventListener("resize", handleResize);
        };
      } catch (err) {
        console.error("Error initializing terminal:", err);
      }
    }
  }, [isVisible, domReady, getTerminalInstance]);

  useEffect(() => {
    if (!content || !isVisible || !domReady) {
      return;
    }

    const instance = getTerminalInstance();
    const { term } = instance;

    if (!term) return;

    requestAnimationFrame(() => {
      previousContentRef.current = content;
      console.log("Writing content to terminal:", content);

      // Write content to terminal
      term.write(`\r\n${content}`);

      setTimeout(() => {
        term.scrollToBottom();

        if (terminalId && workingDirectory && !content.endsWith("#")) {
          term.write("\r\n");
          term.write(`root@${terminalId}:${workingDirectory}# `);
        }
      }, 50);
    });
  }, [content, isVisible, domReady, getTerminalInstance]);

  useEffect(() => {
    if (isVisible && domReady) {
      try {
        const instance = getTerminalInstance();
        const { fitAddon, term } = instance;

        const resizeObserver = new ResizeObserver(() => {
          if (fitAddon && term) {
            setTimeout(() => {
              fitAddon.fit();
              term.scrollToBottom();
            }, 100);
          }
        });

        if (terminalRef.current) {
          resizeObserver.observe(terminalRef.current);
        }

        setTimeout(() => {
          if (fitAddon && term) {
            fitAddon.fit();
            term.scrollToBottom();
          }
        }, 100);

        return () => {
          resizeObserver.disconnect();
        };
      } catch (err) {
        console.error("Error fitting terminal after size change:", err);
      }
    }
  }, [isVisible, domReady, getTerminalInstance]);

  useEffect(() => {
    return () => {
      if (terminalRef.current === null) {
        const id = instanceIdRef.current;
        console.log(
          `Component completely unmounted, cleaning up terminal ${id}`
        );
      }
    };
  }, []);

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
