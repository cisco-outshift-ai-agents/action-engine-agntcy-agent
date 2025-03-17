import { twMerge } from "tailwind-merge";
import { type ClassValue, clsx } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const extractHostname = (summary: string): string => {
  const match = summary.match(/^(\S+@\S+):/);
  return match ? match[1] : "unknown";
};
