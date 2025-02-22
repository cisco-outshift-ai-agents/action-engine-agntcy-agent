import { Layout } from "@/components/ui/layout/page";
import { Container } from "@magnetic/container";

import InteractiveVNC from "@/components/interactive-vnc";
import ChatSection from "@/components/chat-section";

const SessionPage = () => {
  return (
    <Layout>
      <Container className="h-full">
        <div className="flex h-full gap-6">
          <div className="flex-1 rounded-lg border border-white/10 bg-[#32363c]">
            <InteractiveVNC />
          </div>
          <div className="flex-grow basis-1/4 flex-shrink-0">
            <ChatSection />
          </div>
        </div>
      </Container>
    </Layout>
  );
};

export default SessionPage;
