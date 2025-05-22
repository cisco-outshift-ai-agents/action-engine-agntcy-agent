import { z } from "zod";

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
