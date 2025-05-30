import { createContext, useContext } from "react";

type ThemeProviderProps = {
  children: React.ReactNode;
};

const ThemeProviderContext = createContext({ theme: "dark" });

export function ThemeProvider({ children }: ThemeProviderProps) {
  if (typeof window !== "undefined") {
    document.documentElement.classList.add("dark");
  }

  return (
    <ThemeProviderContext.Provider value={{ theme: "dark" }}>
      {children}
    </ThemeProviderContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeProviderContext);
