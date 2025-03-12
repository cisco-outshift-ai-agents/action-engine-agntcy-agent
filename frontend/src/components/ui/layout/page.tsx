import { NavBar } from "./header";

import { Container } from "@magnetic/container";

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="flex ">
      <NavBar />
      <main className="min-h-screen flex-1 pt-[56px]">
        <Container
          style={{
            borderRadius: "0",
            height: "calc(100vh - 56px)",
            padding: "4px 6px",
          }}
        >
          {children}
        </Container>
      </main>
    </div>
  );
};
