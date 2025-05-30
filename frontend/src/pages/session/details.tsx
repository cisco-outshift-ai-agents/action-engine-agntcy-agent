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
# SPDX-License-Identifier: Apache-2.0"
*/
import { Layout } from "@/components/ui/layout/page";
import InteractiveVNC from "@/components/interactive-vnc";
import ChatSection from "@/components/chat-section";
import LearningSection from "@/components/learning-section";
import TabbedTerminalContainer from "@/components/terminal/tabbed-terminal-container";
import { MessageCircleIcon, BookCopyIcon } from "lucide-react";
import { useState } from "react";
import { cn } from "@/utils";

const SessionPage = () => {
  const [section, setSection] = useState<"chat" | "learning">("chat");

  const sections = [
    {
      id: "chat",
      title: "Chat",
      icon: <MessageCircleIcon />,
      content: <ChatSection />,
    },
    {
      id: "learning",
      title: "Learning",
      icon: <BookCopyIcon />,
      content: <LearningSection />,
    },
  ];

  return (
    <Layout>
      <div className="h-full p-3 rounded-xl shadow-md">
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

          <div className="w-[30%] flex flex-col">
            <div className="flex justify-end">
              <div className="flex gap-4 mb-2 text-white [&_svg]:h-4">
                {sections.map(({ id, title, icon }) => (
                  <button
                    key={id}
                    onClick={() => setSection(id as any)}
                    className={cn(
                      "flex gap-2 text-sm items-center rounded-lg px-2 py-1 cursor-pointer border-2 border-transparent",
                      {
                        "border-white/10 bg-white/10 hover:bg-white/20":
                          section === id,
                        "hover:bg-white/10": section !== id,
                      }
                    )}
                  >
                    {icon}
                    {title}
                  </button>
                ))}
              </div>
            </div>
            {section === "chat" ? <ChatSection /> : <LearningSection />}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default SessionPage;
