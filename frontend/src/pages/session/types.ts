import { z } from "zod";

export const StopDataZod = z.object({
  summary: z.string(),
  stopped: z.boolean(),
});
export type StopData = z.infer<typeof StopDataZod>;

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
