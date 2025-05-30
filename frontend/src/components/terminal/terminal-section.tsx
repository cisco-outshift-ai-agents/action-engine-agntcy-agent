/*
# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0"
*/
import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal as XTerm } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import { extractHostname } from "@/utils";

interface TerminalComponentProps {
  isVisible: boolean;
  terminalId?: string;
  workingDirectory?: string;
  contentBuffer: string;
  onContentUpdate?: (content: string) => void;
}

// Create a persistent terminal instance cache
const terminalInstances: Record<
  string,
  {
    term: XTerm;
    fitAddon: FitAddon;
    mounted: boolean;
    processedContents: Set<string>;
    lastProcessedBuffer: string;
  }
> = {};

const TerminalSection = ({
  isVisible,
  terminalId,
  workingDirectory,
  contentBuffer,
  onContentUpdate,
}: TerminalComponentProps): JSX.Element => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const instanceIdRef = useRef<string>(terminalId || "default");
  const [domReady, setDomReady] = useState(false);
  const currentInputRef = useRef("");
  const cursorPosRef = useRef(0);
  const commandHistoryRef = useRef<string[]>([]);
  const historyPosRef = useRef(-1);
  const previousBufferRef = useRef<string>("");
  const prevTerminalIdRef = useRef<string | undefined>(terminalId);

  // Update instance ID when terminalId changes
  useEffect(() => {
    if (terminalId && instanceIdRef.current !== terminalId) {
      console.log(
        `Updating terminal instance ID from ${instanceIdRef.current} to ${terminalId}`
      );

      // Check if we already have an instance for this terminal ID and don't create a new instance if there's an existing one
      if (terminalInstances[terminalId]) {
        console.log(`Found existing instance for terminal ID ${terminalId}`);
      } else if (terminalInstances[instanceIdRef.current]) {
        console.log(
          `Migrating instance from ${instanceIdRef.current} to ${terminalId}`
        );
        terminalInstances[terminalId] =
          terminalInstances[instanceIdRef.current];
        delete terminalInstances[instanceIdRef.current];
      }
      instanceIdRef.current = terminalId;
      prevTerminalIdRef.current = terminalId;
    }
  }, [terminalId]);

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

    if (
      terminalInstances[id] &&
      terminalInstances[id].term &&
      terminalInstances[id].fitAddon &&
      terminalInstances[id].mounted
    ) {
      return terminalInstances[id];
    }

    console.log(`Creating new terminal instance for ID: ${id}`);

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
      lastProcessedBuffer: "",
    };

    return terminalInstances[id];
  }, []);

  // Handle user input and special keys and history management
  const handleUserInput = (data: string, term: XTerm) => {
    if (data === "\r") {
      const command = currentInputRef.current.trim();
      if (command.length > 0) {
        commandHistoryRef.current.push(command);
        historyPosRef.current = -1;

        term.write("\r\n");
        if (onContentUpdate) {
          onContentUpdate(command);
        }
        currentInputRef.current = "";

        cursorPosRef.current = 0;
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
        const hostname = extractHostname(contentBuffer || "");
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
        const hostname = extractHostname(contentBuffer || "");
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
      }
      // Left Arrow Key
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
          if (terminalRef.current) {
            terminalRef.current.innerHTML = "";
            terminalRef.current.appendChild(term.element);
          }
        }

        setTimeout(() => {
          if (fitAddon && terminalRef.current) {
            fitAddon.fit();
          }
        }, 100);

        return;
      }
      (term as any)._lastCommandTime = 0;
      (term as any)._lastCommandTimeout = null;

      term.open(terminalRef.current);

      term.onData((data) => {
        handleUserInput(data, term);
      });

      // Write initial buffer content if available
      if (contentBuffer && contentBuffer.trim()) {
        const lines = contentBuffer.split("\n");
        let processedContent = "";
        let lastLineWasPrompt = false;

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          const isPrompt = /^root@[^:]+:[^#]+#\s*/.test(line);

          if (isPrompt && lastLineWasPrompt) {
            continue;
          }

          if (processedContent && !lastLineWasPrompt) {
            processedContent += "\r\n";
          }

          processedContent += line;
          lastLineWasPrompt = isPrompt;
        }

        term.write(processedContent);
        instance.lastProcessedBuffer = contentBuffer;

        if (terminalId && workingDirectory) {
          const lastLine = lines[lines.length - 1] || "";
          const promptPattern = /^root@[^:]+:[^#]+#\s*$/;

          if (!promptPattern.test(lastLine)) {
            const hostname = extractHostname(contentBuffer || "");
            term.write(`${hostname}:${workingDirectory}# `);
          }
        }
      } else {
        const hostname = extractHostname(contentBuffer || "");
        term.write(`${hostname}:${workingDirectory}# `);
      }

      instance.mounted = true;

      setTimeout(() => {
        if (fitAddon && terminalRef.current) {
          fitAddon.fit();
          term.scrollToBottom();
        }
      }, 100);

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
    terminalId,
    workingDirectory,
    contentBuffer,
  ]);

  // Process new content, skip if already procesed
  useEffect(() => {
    if (!contentBuffer || !isVisible || !domReady) return;
    if (previousBufferRef.current === contentBuffer) {
      return;
    }

    previousBufferRef.current = contentBuffer;

    const instance = getTerminalInstance();
    if (!instance || !instance.term) return;

    const { term, lastProcessedBuffer } = instance;

    if (lastProcessedBuffer === contentBuffer) {
      return;
    }

    const wasProcessingCommand = currentInputRef.current.length > 0;

    const parseCommandOutput = (buffer: string) => {
      const commandMatch = buffer.match(/(.+?#\s*)([^\n]+)[\r\n]+(.*)/s);
      if (commandMatch) {
        const [_, promptPart, commandPart, outputPart] = commandMatch;
        return {
          prompt: promptPart,
          command: commandPart,
          output: outputPart,
        };
      }
      return null;
    };

    let newContent = contentBuffer;

    if (lastProcessedBuffer) {
      if (contentBuffer.startsWith(lastProcessedBuffer)) {
        newContent = contentBuffer.substring(lastProcessedBuffer.length);
        if (newContent.startsWith("\n")) {
          newContent = newContent.substring(1);
        }
      } else {
        term.clear();
        newContent = contentBuffer;
      }
    }

    if (newContent.trim()) {
      const commandOutput = parseCommandOutput(newContent);

      if (commandOutput && wasProcessingCommand) {
        if (commandOutput.output.trim()) {
          term.write(`\r\n${commandOutput.output}`);
        }
      } else {
        const promptPattern = /^root@[^:]+:[^#]+#\s*/m;
        const hasPrompt = promptPattern.test(newContent);

        if (hasPrompt) {
          const lines = newContent.split("\n");
          let lastWasPrompt = false;

          for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const isPromptLine = promptPattern.test(line);

            if (isPromptLine && lastWasPrompt) {
              continue;
            }

            if (line.trim()) {
              term.write(line);
              if (i < lines.length - 1) {
                term.write("\r\n");
              }
            }

            lastWasPrompt = isPromptLine;
          }
        } else {
          term.write(newContent);
        }
      }

      setTimeout(() => {
        term.scrollToBottom();
        const buffer = term.buffer.active;
        const lastLine =
          buffer.getLine(buffer.length - 1)?.translateToString() || "";

        const serverPrompt = `${extractHostname(contentBuffer || "")}:${
          workingDirectory || "~"
        }# `;

        if (!lastLine.trim().endsWith("#")) {
          term.write(`\r\n${serverPrompt}`);
        }
      }, 100);
    }

    instance.lastProcessedBuffer = contentBuffer;
  }, [
    contentBuffer,
    isVisible,
    domReady,
    getTerminalInstance,
    terminalId,
    workingDirectory,
  ]);

  return (
    <div className="flex flex-col h-full bg-[#1a1a1a] rounded-b-lg overflow-hidden">
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
  terminalId?: string | null;
}
