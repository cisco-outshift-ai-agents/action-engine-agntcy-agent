import { NavBar } from "./header";

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="flex bg-background text-foreground ">
      <NavBar />
      <main className="min-h-screen flex-1 pt-[56px]">
        <div
          style={{
            borderRadius: "0",
            height: "calc(100vh - 56px)",
            padding: "4px 12px",
          }}
        >
          {children}
        </div>
      </main>
    </div>
  );
};
