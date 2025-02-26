import { z } from "zod";

export const StopDataZod = z.object({
  summary: z.string(),
  stopped: z.boolean(),
});
export type StopData = z.infer<typeof StopDataZod>;
