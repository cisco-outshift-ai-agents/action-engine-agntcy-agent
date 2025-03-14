import { useEffect, useRef, useState } from "react";
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

const TerminalSection = ({
  content,
  isVisible,
  terminalId,
  workingDirectory,
  contentBuffer,
  onContentUpdate,
}: TerminalComponentProps): JSX.Element => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const previousContentRef = useRef<string>("");
  const terminalMountedRef = useRef<boolean>(false);
  const [domReady, setDomReady] = useState(false);
  const [currentInput, setCurrentInput] = useState("");
  const cursorPosRef = useRef(0);
  const commandHistoryRef = useRef<string[]>([]);
  const historyPosRef = useRef(-1);

  //   // Wait for DOM to be ready
  useEffect(() => {
    if (isVisible && terminalRef.current) {
      const timer = setTimeout(() => {
        setDomReady(true);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isVisible]);

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

  // Initialize terminal (    // Only initialize if visible, DOM is ready, and terminal not already mounted)
  useEffect(() => {
    if (
      isVisible &&
      terminalRef.current &&
      domReady &&
      !terminalMountedRef.current
    ) {
      console.log(`Initializing terminal ${terminalId}`);
      try {
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

        term.open(terminalRef.current);

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);

        term.onData((data) => {
          handleUserInput(data, term);
        });

        xtermRef.current = term;
        fitAddonRef.current = fitAddon;
        terminalMountedRef.current = true;

        setTimeout(() => {
          try {
            if (fitAddonRef.current && terminalRef.current) {
              fitAddonRef.current.fit();

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
            }
          } catch (err) {
            console.error("Error fitting terminal:", err);
          }
        }, 500);

        const handleResize = () => {
          try {
            if (fitAddonRef.current && terminalMountedRef.current) {
              fitAddonRef.current.fit();
            }
          } catch (err) {
            console.error("Error during resize:", err);
          }
        };

        window.addEventListener("resize", handleResize);

        return () => {
          window.removeEventListener("resize", handleResize);
          term.dispose();
          xtermRef.current = null;
          fitAddonRef.current = null;
          terminalMountedRef.current = false;
          console.log(`Terminal ${terminalId} cleaned up`);
        };
      } catch (err) {
        console.error("Error initializing terminal:", err);
      }
    }
  }, [isVisible, domReady, terminalId, workingDirectory, contentBuffer]);

  useEffect(() => {
    if (
      !content ||
      !xtermRef.current ||
      !isVisible ||
      !terminalMountedRef.current
    ) {
      return;
    }

    requestAnimationFrame(() => {
      //   if (content !== previousContentRef.current) {
      previousContentRef.current = content;
      const term = xtermRef.current;
      if (!term) return;

      term.write(`\r\n${content}`);

      // if (onContentUpdate) {
      //   onContentUpdate(terminalId || "terminal", content);
      // }

      setTimeout(() => {
        term.scrollToBottom();
        term.write("\r\n");

        if (terminalId && workingDirectory) {
          term.write(`root@${terminalId}:${workingDirectory}# `);
        }
      }, 50);
    });
  }, [content, isVisible, terminalId, workingDirectory]);

  useEffect(() => {
    if (isVisible && xtermRef.current && terminalMountedRef.current) {
      try {
        const resizeObserver = new ResizeObserver(() => {
          const fitAddon = fitAddonRef.current;
          const term = xtermRef.current;

          if (fitAddon && term) {
            setTimeout(() => {
              if (fitAddon && term) {
                fitAddon.fit();
                term.scrollToBottom();
              }
            }, 100);
          }
        });

        if (terminalRef.current) {
          resizeObserver.observe(terminalRef.current);
        }

        setTimeout(() => {
          const fitAddon = fitAddonRef.current;
          const term = xtermRef.current;

          if (fitAddon && term) {
            fitAddon.fit();
            term.scrollToBottom();
          }
        }, 100);

        // Cleanup observer on unmount
        return () => {
          resizeObserver.disconnect();
        };
      } catch (err) {
        console.error("Error fitting terminal after size change:", err);
      }
    }
  }, [isVisible]);

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
