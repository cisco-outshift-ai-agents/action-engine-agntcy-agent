import { useEffect, RefObject } from "react";

export const useChatScroll = (
  bottomRef: RefObject<HTMLDivElement>,
  containerRef: RefObject<HTMLDivElement>,
  dependencies: any[]
) => {
  const scrollToBottom = () => {
    if (bottomRef.current && containerRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, dependencies);

  return { scrollToBottom };
};
