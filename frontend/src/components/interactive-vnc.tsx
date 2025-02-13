import React, { useEffect, useRef } from "react";

import RFB from "@novnc/novnc";

const InteractiveVNC: React.FC = () => {
  const vncContainerRef = useRef<HTMLDivElement>(null);
  const rfbRef = useRef<RFB | null>(null);

  useEffect(() => {
    if (!vncContainerRef.current) {
      return;
    }

    const rfb = new RFB(vncContainerRef.current, "http://localhost:6080", {
      credentials: { password: "youvncpassword" },
    });

    rfb.clipViewport = true;
    rfb.scaleViewport = true;
    rfb.focusOnClick = true;
    rfb.viewOnly = false; // Allows user input

    rfb.addEventListener("connect", () => {
      console.log("Connected to VNC server");
    });

    rfb.addEventListener("disconnect", () => {
      console.log("Disconnected from VNC server");
    });
    rfbRef.current = rfb;

    return () => {
      if (rfbRef.current) {
        rfbRef.current.disconnect();
      }
    };
  });

  return (
    <div
      ref={vncContainerRef}
      className="min-w-4xl bg-gray-900 h-[600px] px-2 py-1 w-full"
    >
      {/* VNC will render here */}
    </div>
  );
};

export default InteractiveVNC;
