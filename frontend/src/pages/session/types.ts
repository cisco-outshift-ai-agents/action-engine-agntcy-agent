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
  brain: z.object({
    future_plans: z.string().nullish(),
    important_contents: z.string().nullish(),
    prev_action_evaluation: z.string().nullish(),
    task_progress: z.string().nullish(),
    summary: z.string().nullish(),
    thought: z.string().nullish(),
  }),
  context: z.object({}),
  error: z.any(),
  exiting: z.boolean(),
  plan: PlanZod.nullish(),
  messages: z.array(
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
  ),
  next_node: z.string().nullish(),
  summary: z.string().nullish(),
  task: z.string(),
  thought: z.string().nullish(),
  tools_used: z.array(z.unknown()),
});
export type GraphData = z.infer<typeof GraphDataZod>;

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
});

export type TerminalData = z.infer<typeof TerminalDataZod>;
