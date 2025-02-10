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
    <div>
      <div
        ref={vncContainerRef}
        style={{
          width: "100%",
          height: "600px",
          background: "rgb(40,40,40)",
        }}
      >
        {/* VNC will render here */}
      </div>
    </div>
  );
};

export default InteractiveVNC;
