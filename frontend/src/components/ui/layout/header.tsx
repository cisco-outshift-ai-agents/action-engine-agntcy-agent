/*
# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
*/
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
              Agentic Computer-use Assistant
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
