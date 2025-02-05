import { Layout } from "@/components/ui/layout/page";
import { Container } from "@magnetic/container";
import { Flex } from "@magnetic/flex";

import InteractiveVNC from "@/components/interactive-vnc";
import ChatSection from "@/components/chat-section";

const SessionPage = () => {
  return (
    <Layout>
      <Container className="h-full">
        <Flex direction="horizontal" className="h-full" gap={16}>
          <Flex
            direction="vertical"
            className="!flex-grow rounded-lg border border-white/10 bg-[#32363c]"
          >
            <InteractiveVNC />
          </Flex>
          <Flex
            direction="vertical"
            className="h-full rounded-lg border border-white/10 bg-[#32363c] max-w-3xl"
          >
            <ChatSection />
          </Flex>
        </Flex>
      </Container>
    </Layout>
  );
};

export default SessionPage;
