import { useMemo } from "react";
import LoaderGIF from "@/components/newsroom/newsroom-assets/loader.gif";

interface PlanRendererProps {
  plan: string;
}

interface ParsedStep {
  number: number;
  status: "not_started" | "in_progress" | "completed" | "blocked";
  text: string;
}

const PlanRenderer: React.FC<PlanRendererProps> = ({ plan }) => {
  const parsedPlan = useMemo(() => {
    const lines = plan.split("\n");
    const title = lines[0];
    const progress = lines.find((l) => l.startsWith("Progress:"));
    const status = lines.find((l) => l.startsWith("Status:"));

    const steps = lines
      .filter((line) => /^\d+\..*/.test(line))
      .map((line) => {
        const [numberPart, ...rest] = line.split("] ");
        return {
          number: parseInt(numberPart),
          status: line.includes("[→]")
            ? "in_progress"
            : line.includes("[✓]")
            ? "completed"
            : line.includes("[!]")
            ? "blocked"
            : "not_started",
          text: rest.join("] ").trim(),
        } as ParsedStep;
      });

    return { title, progress, status, steps };
  }, [plan]);

  const nextStep = parsedPlan.steps.find(
    (s) => s.status === "in_progress" || s.status === "not_started"
  );

  return (
    <div>
      <p className="text-sm text-gray-400 mb-2">Currently working on:</p>
      <details className="group bg-[#373C42] mb-4 rounded-lg shadow-md">
        <summary className="flex items-center justify-between p-4 cursor-pointer list-none">
          <div className="flex items-center gap-2">
            {plan && nextStep?.status !== "completed" ? (
              <img src={LoaderGIF} alt="Loading..." className="w-5 h-5" />
            ) : (
              <span className="text-gray-400">○</span>
            )}
            <span className="text-gray-100">
              {nextStep?.text || "No active steps"}
            </span>
          </div>
          <svg
            className="w-5 h-5 transition-transform group-open:rotate-180"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="white"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </summary>
        <div className="p-4 border-t border-gray-700">
          <h2 className="text-lg font-bold text-gray-100">
            {parsedPlan.title}
          </h2>
          <p className="text-sm text-gray-400">{parsedPlan.progress}</p>
          <p className="text-sm text-gray-400">{parsedPlan.status}</p>
          <ul className="mt-2 space-y-2">
            {parsedPlan.steps.map((step) => (
              <li key={step.number} className="flex items-start">
                <span
                  className={`mr-2 ${
                    step.status === "completed"
                      ? "text-green-500"
                      : step.status === "in_progress"
                      ? "text-blue-500"
                      : step.status === "blocked"
                      ? "text-red-500"
                      : "text-gray-400"
                  }`}
                >
                  {step.status === "completed"
                    ? "✓"
                    : step.status === "in_progress"
                    ? "→"
                    : step.status === "blocked"
                    ? "!"
                    : "○"}
                </span>
                <span className="text-gray-100">{step.text}</span>
              </li>
            ))}
          </ul>
        </div>
      </details>
    </div>
  );
};

export default PlanRenderer;
