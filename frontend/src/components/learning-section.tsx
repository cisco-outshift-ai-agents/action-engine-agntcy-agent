import React, { useState, useEffect, useRef } from "react";
import { LTOEvent, LTOEventZod } from "@/types";
import LearningSectionControls from "./learning-section-controls";

const LearningSection: React.FC = () => {
  const [events, setEvents] = useState<LTOEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const getWsRef = useRef<WebSocket | null>(null);
  const reconnectIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const connectWebSocket = () => {
    const getWs = new WebSocket(`ws://localhost:7788/ws/get-events`);
    getWsRef.current = getWs;

    getWs.onopen = () => {
      setIsConnected(true);
      console.log("Connected to LTO events socket");
      if (reconnectIntervalRef.current) {
        clearInterval(reconnectIntervalRef.current);
        reconnectIntervalRef.current = null;
      }
    };

    getWs.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        const newEvents = Array.isArray(data) ? data : [data];

        const parsedEvents = newEvents
          .map((event) => {
            const safeParse = LTOEventZod.safeParse(
              typeof event === "string" ? JSON.parse(event) : event
            );

            if (!safeParse.success) {
              console.error("Failed to parse event:", safeParse.error);
            }

            return safeParse.success ? safeParse.data : null;
          })
          .filter((event): event is LTOEvent => event !== null);

        setEvents(parsedEvents);
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    getWs.onclose = () => {
      setIsConnected(false);
      console.log("Disconnected from get events server");
      if (!reconnectIntervalRef.current) {
        reconnectIntervalRef.current = setInterval(connectWebSocket, 5000);
      }
    };
  };

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (getWsRef.current) {
        getWsRef.current.close();
      }
      if (reconnectIntervalRef.current) {
        clearInterval(reconnectIntervalRef.current);
      }
    };
  }, []);

  const formatEvent = (data: LTOEvent) => {
    return `${data.operation?.original_op}: ${data.operation?.target} ${data.operation?.value} [pos_candidates: ${data.pos_candidates?.length}]`;
  };

  return (
    <div className="h-full rounded-lg  bg-[#32363c] w-full px-2 py-4 flex flex-col border-white/10 border">
      <div className="flex items-center justify-end w-full mb-1">
        <div className="flex items-center">
          <div>
            <div
              className={`rounded-full aspect-square h-2 w-2 ${
                isConnected ? "bg-green-500" : "bg-red-500"
              }`}
            />
          </div>
          <p className="ml-2 text-xs text-white font-semibold">
            {isConnected
              ? "Connected to LTO events socket"
              : "Disconnected from LTO events socket"}
          </p>
        </div>
      </div>
      <LearningSectionControls />
      <div className="flex-1 overflow-hidden text-white text-sm">
        <span>
          {events.length} event{events.length !== 1 && "s"} received
        </span>
        <div className="flex flex-col h-full overflow-auto p-4 bg-gray-800 rounded text-xs max-h-[150px]">
          {events.map((event) => (
            <code>{formatEvent(event)}</code>
          ))}
        </div>
      </div>
    </div>
  );
};

export default LearningSection;
