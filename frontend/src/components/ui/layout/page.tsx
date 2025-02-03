import { NavBar } from "./header";

import { Container } from "@magnetic/container";

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="flex ">
      <NavBar />
      <div className="flex flex-1 flex-col">
        <main className="h-full pt-[56px]">
          <Container
            style={{
              borderRadius: "0",
              height: "calc(100vh - 56px)",
              padding: "16px 24px",
            }}
          >
            {children}
          </Container>
        </main>
      </div>
    </div>
  );
};
