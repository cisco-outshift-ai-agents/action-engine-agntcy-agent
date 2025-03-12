import React, { useEffect, useRef } from "react";
import { Terminal as XTerm } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import { Terminal as TerminalIcon } from "lucide-react";

interface TerminalComponentProps {
  content?: string;
  isVisible: boolean;
  terminalId?: string;
  workingDirectory?: string;
}

const TerminalSection: React.FC<TerminalComponentProps> = ({
  content,
  isVisible,
  terminalId,
  workingDirectory,
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const previousContentRef = useRef<string>("");

  useEffect(() => {
    if (isVisible && terminalRef.current) {
      if (!xtermRef.current) {
        const term = new XTerm({
          cursorBlink: true,
          theme: {
            background: "#1a1a1a",
            foreground: "#00ff00",
            cursor: "#00ff00",
          },
          fontSize: 14,
          fontFamily: "Menlo, Monaco, Consolas, monospace",
          lineHeight: 1.2,
          convertEol: true,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);
        term.open(terminalRef.current);

        setTimeout(() => {
          fitAddon.fit();
        }, 100);

        xtermRef.current = term;
        fitAddonRef.current = fitAddon;

        const handleResize = () => {
          if (fitAddonRef.current) {
            fitAddonRef.current.fit();
          }
        };

        window.addEventListener("resize", handleResize);

        return () => {
          window.removeEventListener("resize", handleResize);
          term.dispose();
          xtermRef.current = null;
        };
      }
    }
  }, [isVisible]);

  useEffect(() => {
    if (xtermRef.current && isVisible) {
      if (content && content !== previousContentRef.current) {
        previousContentRef.current = content;

        xtermRef.current.clear();

        const lines = content.split("\n");
        lines.forEach((line, index) => {
          xtermRef.current?.write(`${line}`);
          if (index < lines.length - 1) {
            xtermRef.current?.write("\r\n");
          }
        });

        if (fitAddonRef.current) {
          setTimeout(() => {
            fitAddonRef.current?.fit();
          }, 50);
        }
      }
    }
  }, [content, isVisible]);

  const headerText = workingDirectory || "Terminal Session";

  return (
    <div className="flex flex-col h-full bg-[#1a1a1a] rounded-b-lg">
      <div className="flex items-center justify-between bg-[#272a30] px-3 py-2 border-b border-gray-700">
        <div className="flex items-center">
          <TerminalIcon className="w-4 h-4 mr-2 text-green-400" />
          <span className="text-green-400 font-mono text-xs">
            {headerText}
            {terminalId && (
              <span className="text-gray-500 ml-2">#{terminalId}</span>
            )}
          </span>
        </div>
      </div>
      <div ref={terminalRef} className="flex-1 overflow-hidden p-1" />
    </div>
  );
};

export default TerminalSection;
