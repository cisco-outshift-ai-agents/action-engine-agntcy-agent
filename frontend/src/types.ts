import { z } from "zod";

export type TodoFixAny = any;

export const LTOEventZod = z.object({
  action_reprs: z
    .object({
      action: z.array(
        z.object({
          click_element: z
            .object({
              index: z.number(),
              xpath: z.string().nullish(),
            })
            .nullish(),
          go_to_url: z
            .object({
              url: z.string(),
            })
            .nullish(),
          input_text: z
            .object({
              index: z.number(),
              text: z.string(),
              xpath: z.string().nullish(),
            })
            .nullish(),
          scroll_down: z
            .object({
              amount: z.number().nullish(),
            })
            .nullish(),
          send_keys: z
            .object({
              keys: z.string(),
            })
            .nullish(),
        })
      ),
      current_state: z.object({
        future_plans: z.string().nullish(),
        important_contents: z.string().nullish(),
        prev_action_evaluation: z.string(),
        summary: z.string(),
        task_progress: z.string().nullish(),
        thought: z.string(),
      }),
    })
    .nullish(),
  action_uid: z.string(),
  annotation_id: z.string().nullish(),
  cleaned_html: z.string().nullish(),
  confirmed_task: z.string().nullish(),
  domain: z.string(),
  neg_candidates: z
    .array(
      z.object({
        attributes: z.record(z.union([z.string(), z.number(), z.boolean()])),
        tag: z.string(),
      })
    )
    .nullish(),
  operation: z
    .object({
      op: z.string(),
      original_op: z.string(),
      target: z.string(),
      value: z.string().nullish(),
    })
    .nullish(),
  pos_candidates: z
    .array(
      z.object({
        attributes: z.record(z.union([z.string(), z.number(), z.boolean()])),
        tag: z.string(),
      })
    )
    .nullish(),
  raw_html: z.string(),
  screenshot: z.string().nullish(),
  subdomain: z.string(),
  target_action: z.string().nullish(),
  target_action_index: z.string().nullish(),
  website: z.string(),
});

export type LTOEvent = z.infer<typeof LTOEventZod>;
