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
# SPDX-License-Identifier: Apache-2.0
*/
import React, { useEffect, useRef, useState } from "react";
import { Loader2Icon } from "lucide-react";

import RFB from "@novnc/novnc";

const RECONNECT_DELAY = 10000; // 10 seconds

const InteractiveVNC: React.FC = () => {
  const vncContainerRef = useRef<HTMLDivElement>(null);
  const rfbRef = useRef<RFB | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const [isConnecting, setIsConnecting] = useState(true);

  const connect = () => {
    if (!vncContainerRef.current) return;

    setIsConnecting(true);

    const rfb = new RFB(vncContainerRef.current, "http://localhost:6080", {
      credentials: { password: "youvncpassword" },
    });

    rfb.clipViewport = true;
    rfb.scaleViewport = true;
    rfb.focusOnClick = true;
    rfb.viewOnly = false; // Allows user input

    rfb.addEventListener("connect", () => {
      console.log("Connected to VNC server");
      setIsConnecting(false);
      // Clear any pending reconnect attempts
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    });

    rfb.addEventListener("disconnect", () => {
      console.log("Disconnected from VNC server - attempting reconnect...");
      setIsConnecting(true);
      // Schedule reconnect
      reconnectTimeoutRef.current = setTimeout(() => {
        if (rfbRef.current) {
          rfbRef.current.disconnect();
          rfbRef.current = null;
        }
        connect();
      }, RECONNECT_DELAY);
    });

    rfbRef.current = rfb;
  };

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (rfbRef.current) {
        rfbRef.current.disconnect();
      }
    };
  }, []);

  return (
    <div className="relative">
      <div
        ref={vncContainerRef}
        className="min-w-4xl bg-gray-900 h-[585px] w-full"
      >
        {/* VNC will render here */}
      </div>
      {isConnecting && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <Loader2Icon className="w-8 h-8 animate-spin text-white" />
        </div>
      )}
    </div>
  );
};

export default InteractiveVNC;
