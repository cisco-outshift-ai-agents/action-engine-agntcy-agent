import CiscoLogo from "@/assets/images/cisco-logo.svg?react";
import ActionEngineLogo from "@/assets/images/action-engine-logo.png";
import { Menu, Settings, Info, Users, User } from "lucide-react";
import { Button } from "@/components/ui/button";

export const NavBar = () => {
  return (
    <header className="fixed z-[970] flex items-center justify-between w-full h-14 px-4 bg-gradient-to-r from-[#1f1f1f] to-[#2c2c2c] border-b border-white/10">
      <div className="flex items-center gap-4">
        <CiscoLogo className="w-12 h-12 fill-white" />
        <div className="h-10 w-px bg-white/20" />
        <div className="flex items-center gap-2">
          <img
            src={ActionEngineLogo}
            alt="ActionEngine"
            className="w-8 h-auto"
          />
          <div className="flex flex-col leading-tight">
            <span className="text-white font-semibold text-sm">
              ActionEngine
            </span>
            <span className="text-gray-400 text-xs">
              Agentic AI Networking Assistant
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-[4px]">
        <Button
          variant="ghost"
          size="icon"
          className="text-white hover:text-gray-300 h-9 w-9"
        >
          <Menu className="w-[28px] h-[28px] " strokeWidth={3} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="text-white hover:text-gray-300 h-9 w-9"
        >
          <Settings className="w-[28px] h-[28px]" strokeWidth={3} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="text-white hover:text-gray-300 h-9 w-9"
        >
          <Info className="w-[28px] h-[28px]" strokeWidth={3} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="text-white hover:text-gray-300 h-9 w-9"
        >
          <Users className="w-[28px] h-[28px]" strokeWidth={3} />
        </Button>

        <div className="h-6 w-px bg-white/40 mx-[6px]" />

        <Button
          variant="ghost"
          size="icon"
          className="text-white hover:text-gray-300 h-9 w-9"
        >
          <User className="w-[28px] h-[28px]" strokeWidth={3} />
        </Button>
      </div>
    </header>
  );
};
