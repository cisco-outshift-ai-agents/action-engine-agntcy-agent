import { Layout } from "@/components/ui/layout/page";
import { Container } from "@magnetic/container";

import InteractiveVNC from "@/components/interactive-vnc";
import ChatSection from "@/components/chat-section";

const SessionPage = () => {
  return (
    <Layout>
      <Container className="h-full">
        <div className="flex h-full gap-8">
          <div className="flex-grow rounded-lg border border-white/10 bg-[#32363c]">
            <InteractiveVNC />
          </div>
          <ChatSection />
        </div>
      </Container>
    </Layout>
  );
};

export default SessionPage;
