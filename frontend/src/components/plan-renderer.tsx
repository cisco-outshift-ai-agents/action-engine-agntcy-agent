import LoaderGIF from "@/components/newsroom/newsroom-assets/loader.gif";
import { Plan } from "@/pages/session/types";

const PlanRenderer: React.FC<PlanRendererProps> = ({ plan }) => {
  if (!plan) {
    return null;
  }
  const nextStep = plan.steps.find(
    (s) => s.status === "in_progress" || s.status === "not_started"
  );

  return (
    <div>
      <p className="text-sm text-gray-400 mb-2">Currently working on:</p>
      <details className="group bg-[#373C42] mb-4 rounded-lg shadow-md">
        <summary className="flex items-center justify-between p-4 cursor-pointer list-none">
          <div className="flex items-center gap-2">
            {nextStep?.status !== "completed" ? (
              <img src={LoaderGIF} alt="Loading..." className="w-5 h-5" />
            ) : (
              <span className="text-gray-400">○</span>
            )}
            <span className="text-gray-100">
              {nextStep?.content || "No active steps"}
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
        <div className="p-4 border-t border-gray-700 bg-[#535a63] rounded-b-lg text-sm">
          <ul className="mt-2 space-y-2">
            {plan.steps.map((step, index) => (
              <li key={index} className="flex flex-col gap-2">
                <div>
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
                  <span className="text-gray-100">{step.content}</span>
                </div>
                {step.notes && (
                  <p className="text-sm text-gray-400 ml-6">{step.notes}</p>
                )}
                {step.substeps && step.substeps.length > 0 && (
                  <ul className="ml-6 space-y-2">
                    {step.substeps.map((substep, subIndex) => (
                      <li key={subIndex} className="flex items-start">
                        <span
                          className={`mr-2 ${
                            substep.status === "completed"
                              ? "text-green-500"
                              : substep.status === "in_progress"
                              ? "text-blue-500"
                              : substep.status === "blocked"
                              ? "text-red-500"
                              : "text-gray-400"
                          }`}
                        >
                          {substep.status === "completed"
                            ? "✓"
                            : substep.status === "in_progress"
                            ? "→"
                            : substep.status === "blocked"
                            ? "!"
                            : "○"}
                        </span>
                        <div className="flex flex-col">
                          <span className="text-gray-100">
                            {substep.content}
                          </span>
                          {substep.notes && (
                            <p className="text-sm text-gray-400">
                              {substep.notes}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      </details>
    </div>
  );
};

interface PlanRendererProps {
  plan: Plan | null;
}

export default PlanRenderer;
