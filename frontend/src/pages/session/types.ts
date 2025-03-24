import { z } from "zod";

export const StopDataZod = z.object({
  summary: z.string(),
  stopped: z.boolean(),
});
export type StopData = z.infer<typeof StopDataZod>;

export const DataZod = z.object({
  action: z.array(
    z.union([
      z.string(),
      z.object({
        input_text: z
          .object({ index: z.number(), text: z.string() })
          .optional(),
        execute_terminal_command: z.object({ command: z.string() }).optional(),
        click_element: z.object({ index: z.number() }).optional(),
        prev_action_evaluation: z.string().optional(),
        important_contents: z.string().optional(),
        task_progress: z.string().optional(),
        future_plans: z.string().optional(),
        thought: z.string().optional(),
        summary: z.string().optional(),
        done: z.union([z.boolean(), z.object({ text: z.string() })]).optional(),
        terminal_id: z.string().optional(),
        working_directory: z.string().optional(),
        is_terminal: z.boolean().optional(),
      }),
    ])
  ),
  current_state: z.object({}).optional(),
  html_content: z.string(),
});
export type Data = z.infer<typeof DataZod>;

// Removes the union type
export const CleanerDataZod = z.object({
  action: z.array(
    z.object({
      input_text: z.object({ index: z.number(), text: z.string() }).optional(),
      click_element: z.object({ index: z.number() }).optional(),
      execute_terminal_command: z.object({ command: z.string() }).optional(),
      prev_action_evaluation: z.string().optional(),
      important_contents: z.string().optional(),
      task_progress: z.string().optional(),
      future_plans: z.string().optional(),
      thought: z.string().optional(),
      summary: z.string().optional(),
      done: z.boolean().optional(),
      terminal_id: z.string().optional(),
      working_directory: z.string().optional(),
      is_terminal: z.boolean().optional(),
    })
  ),
  current_state: z.object({}).optional(),
  html_content: z.string(),
});
export type CleanerData = z.infer<typeof CleanerDataZod>;

export const TerminalDataZod = z.object({
  summary: z.string(),
  working_directory: z.string(),
  terminal_id: z.string(),
});

export type TerminalData = z.infer<typeof TerminalDataZod>;
