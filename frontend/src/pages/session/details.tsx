import { Layout } from "@/components/ui/layout/page";
import { Container } from "@magnetic/container";
import InteractiveVNC from "@/components/interactive-vnc";
import ChatSection from "@/components/chat-section";
import TabbedTerminalContainer from "@/components/terminal/terminal-tab";

const SessionPage = () => {
  return (
    <Layout>
      <Container className="h-full">
        <div className="flex h-full gap-3">
          <div className="w-[70%] flex flex-col gap-2">
            <div
              className="rounded-lg border border-white/10 bg-[#32363c] overflow-hidden"
              style={{ height: "65" }}
            >
              <InteractiveVNC />
            </div>

            <div
              className="rounded-lg overflow-hidden"
              style={{ height: "35%" }}
            >
              <TabbedTerminalContainer />
            </div>
          </div>

          <div className="w-[30%]">
            <ChatSection />
          </div>
        </div>
      </Container>
    </Layout>
  );
};

export default SessionPage;
