import { Header } from "@magnetic/header";
import CiscoLogo from "@/assets/images/cisco-logo.svg?react";
import ActionEngineLogo from "@/assets/images/action-engine-logo.png";
import { Divider } from "@magnetic/divider";
import { Link } from "react-router-dom";

export const NavBar = () => {
  return (
    <Header
      logo={
        <div className="flex items-center gap-2">
          <CiscoLogo className="w-12 h-12 fill-white" />
          <Divider direction="vertical" style={{ height: "20px" }} size="md" />

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
      }
      productName=""
      href="/"
      profileAndTenant={{
        icon: "user",
        profile: {
          heading: "User",
        },
        content: (
          <Header.UserProfile
            profile={{
              user: { email: "User", name: "User" },
            }}
          ></Header.UserProfile>
        ),
      }}
      style={{ zIndex: 970 }}
    >
      <Link to={""} target="_blank">
        <Header.Button icon="hamburger" label="menu" onClick={() => {}} />
      </Link>
      <Link to={""} target="_blank">
        <Header.Button icon="settings" label="menu" onClick={() => {}} />
      </Link>
      <Link to={""} target="_blank">
        <Header.Button icon="info" label="menu" onClick={() => {}} />
      </Link>
      <Link to={""} target="_blank">
        <Header.Button icon="organization" label="menu" onClick={() => {}} />
      </Link>
    </Header>
  );
};
