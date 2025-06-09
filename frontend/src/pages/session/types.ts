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
import { z } from "zod";

export const BrowserActionZod = z.enum([
  "navigate",
  "click",
  "input_text",
  "screenshot",
  "get_html",
  "get_text",
  "execute_js",
  "scroll",
  "switch_tab",
  "new_tab",
  "close_tab",
  "refresh",
]);
export type BrowserAction = z.infer<typeof BrowserActionZod>;

export const BaseToolMessagePropsZod = z.object({
  className: z.string().optional(),
});
export type BaseToolMessageProps = z.infer<typeof BaseToolMessagePropsZod>;

export const BrowserToolPropsZod = BaseToolMessagePropsZod.extend({
  action: BrowserActionZod,
  url: z.string().optional(),
  index: z.number().optional(),
  text: z.string().optional(),
  script: z.string().optional(),
  scroll_amount: z.number().optional(),
  tab_id: z.number().optional(),
});
export type BrowserToolProps = z.infer<typeof BrowserToolPropsZod>;

export const TerminalToolPropsZod = BaseToolMessagePropsZod.extend({
  action: z.enum(["create", "run", "switch", "close", "list"]).optional(),
  script: z.string().optional(),
  terminal_id: z.string().optional(),
  message: z.string().optional(),
});
export type TerminalToolProps = z.infer<typeof TerminalToolPropsZod>;

export const TerminateToolPropsZod = BaseToolMessagePropsZod.extend({
  status: z.enum(["success", "failure"]),
  reason: z.string().optional(),
});
export type TerminateToolProps = z.infer<typeof TerminateToolPropsZod>;

export const ToolResultPropsZod = BaseToolMessagePropsZod.extend({
  content: z.string(),
});
export type ToolResultProps = z.infer<typeof ToolResultPropsZod>;

export const StopDataZod = z.object({
  summary: z.string(),
  stopped: z.boolean(),
});
export type StopData = z.infer<typeof StopDataZod>;

export const PlanZod = z.object({
  plan_id: z.string().nullish(),
  steps: z.array(
    z.object({
      content: z.string(),
      notes: z.string().nullish(),
      status: z.union([
        z.literal("not_started"),
        z.literal("in_progress"),
        z.literal("completed"),
        z.literal("blocked"),
      ]),
      substeps: z.array(
        z.object({
          content: z.string(),
          notes: z.string().nullish(),
          status: z.union([
            z.literal("not_started"),
            z.literal("in_progress"),
            z.literal("completed"),
            z.literal("blocked"),
          ]),
        })
      ),
    })
  ),
});
export type Plan = z.infer<typeof PlanZod>;

export const GraphDataZod = z.object({
  node_type: z.union([
    z.literal("thinking"),
    z.literal("planning"),
    z.literal("executor"),
    z.literal("human_approval"),
    z.literal("approval_request"),
    z.literal("tool_selection"),
    z.literal("tool_generator"),
    z.literal("base"),
  ]),

  brain: z
    .object({
      future_plans: z.string().optional(),
      important_contents: z.string().optional(),
      prev_action_evaluation: z.string().optional(),
      task_progress: z.string().optional(),
      summary: z.string().optional(),
      thought: z.string().optional(),
    })
    .default({}),
  context: z.object({}).optional().default({}),
  error: z.any().optional(),
  exiting: z.boolean().optional().default(false),
  plan: PlanZod.nullish(),
  messages: z
    .array(
      z.object({
        type: z.union([
          z.literal("AIMessage"),
          z.literal("ToolMessage"),
          z.literal("HumanMessage"),
          z.literal("SystemMessage"),
        ]),
        content: z.string().nullish(),
        tool_calls: z
          .array(
            z.object({
              id: z.string(),
              name: z.string(),
              type: z.string(),
              args: z.record(z.unknown()),
            })
          )
          .nullish(),
      })
    )
    .optional()
    .default([]),
  next_node: z.string().nullish(),
  summary: z.string().nullish(),
  task: z.string(),
  thought: z.string().nullish(),
  tools_used: z.array(z.unknown()).optional().default([]),
  pending_approval: z.record(z.unknown()).optional(),
  tool_calls: z.array(z.unknown()).optional(),
});
export type GraphData = z.infer<typeof GraphDataZod>;

export const ApprovalMessageZod = z.object({
  type: z.string().nullish(),
  run_id: z.string().nullish(),
  status: z.string().nullish(),
  values: z.object({
    tool_call: z.object({
      name: z.string(),
      args: z.record(z.unknown()),
      id: z.string(),
      type: z.string(),
    }),
    message: z.string(),
  }),
});

export type ApprovalMessage = z.infer<typeof ApprovalMessageZod>;

export const NodeUpdateZod = z.object({
  thinking: GraphDataZod.optional(),
  planning: GraphDataZod.optional(),
  executor: GraphDataZod.optional(),
});
export type NodeUpdate = z.infer<typeof NodeUpdateZod>;

export const GraphDataWrapperZod = z.union([GraphDataZod, NodeUpdateZod]);
export type GraphDataWrapper = z.infer<typeof GraphDataWrapperZod>;

export const isNodeUpdate = (data: GraphDataWrapper): data is NodeUpdate => {
  return "thinking" in data || "planning" in data || "executor" in data;
};

export const TerminalDataZod = z.object({
  summary: z.string(),
  working_directory: z.string(),
  terminal_id: z.string(),
  marker_id: z.number(),
});

export type TerminalData = z.infer<typeof TerminalDataZod>;

export const ToolCallZod = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(),
  args: z.record(z.unknown()),
});
export type ToolCall = z.infer<typeof ToolCallZod>;

export const GraphInterruptDataZod = z.object({
  tool_call: z.object({
    args: z.record(z.unknown()),
    id: z.string(),
    name: z.string(),
    type: z.string(),
  }),
  message: z.string(),
});
export type GraphInterruptData = z.infer<typeof GraphInterruptDataZod>;

export const SSEMessageWrapperZod = z.object({
  type: z.string(),
  run_id: z.string(),
  status: z.string(),
});

export const PendingApprovalValuesZod = z.object({
  pending_approval: z.object({
    tool_call: ToolCallZod,
    approved: z.boolean().optional(),
  }),
});
export type PendingApprovalValues = z.infer<typeof PendingApprovalValuesZod>;

export const GraphDataSSEMessage = z.object({
  type: z.string().nullish(),
  run_id: z.string().nullish(),
  status: z.string().nullish(),
  values: GraphDataZod.optional(),
  values: z.union([
    GraphDataZod,
    PendingApprovalValuesZod,
  ]).optional(),
});
export type SSEMessage = z.infer<typeof GraphDataSSEMessage>;

export const InterruptSSEMessage = z.object({
  type: z.string().nullish(),
  run_id: z.string().nullish(),
  status: z.string().nullish(),
  values: GraphInterruptDataZod,
});
export type InterruptSSEMessage = z.infer<typeof InterruptSSEMessage>;

export const BrowserUseArgsZod = z.object({
  action: BrowserActionZod,
  url: z.string().optional(),
  index: z.number().optional(),
  text: z.string().optional(),
  script: z.string().optional(),
  scroll_amount: z.number().optional(),
  tab_id: z.number().optional(),
});
export type BrowserUseArgs = z.infer<typeof BrowserUseArgsZod>;

export const TerminalUseArgsZod = z.object({
  action: z.enum(["create", "run", "switch", "close", "list"]),
  script: z.string().optional(),
  terminal_id: z.string().optional(),
});
export type TerminalUseArgs = z.infer<typeof TerminalUseArgsZod>;

export const TerminateUseArgsZod = z.object({
  status: z.enum(["success", "failure"]),
  reason: z.string().optional(),
});
export type TerminateUseArgs = z.infer<typeof TerminateUseArgsZod>;
