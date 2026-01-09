import { useMemo } from "react";
import { clsx } from "clsx";

interface RepairStepListProps {
  steps: string[];
  type?: "repair" | "verify";
}

// Icon mapping for step types based on content
const getStepIcon = (step: string): string => {
  const lowerStep = step.toLowerCase();
  
  if (lowerStep.includes("unplug") || lowerStep.includes("disconnect") || lowerStep.includes("power off") || lowerStep.includes("safety")) {
    return "⚠️";
  }
  if (lowerStep.includes("multimeter") || lowerStep.includes("ohm") || lowerStep.includes("volt") || lowerStep.includes("test") || lowerStep.includes("measure")) {
    return "🔬";
  }
  if (lowerStep.includes("remove") || lowerStep.includes("unscrew") || lowerStep.includes("disconnect")) {
    return "🔧";
  }
  if (lowerStep.includes("install") || lowerStep.includes("replace") || lowerStep.includes("attach") || lowerStep.includes("connect")) {
    return "🔩";
  }
  if (lowerStep.includes("check") || lowerStep.includes("inspect") || lowerStep.includes("look") || lowerStep.includes("verify")) {
    return "👁️";
  }
  if (lowerStep.includes("reassemble") || lowerStep.includes("put back") || lowerStep.includes("secure")) {
    return "✅";
  }
  return "•";
};

// Clean up common LLM formatting issues - keep it simple, don't over-filter
const cleanStepText = (text: string): string => {
  return text
    // Remove leading numbers with period or parenthesis (1. or 1))
    .replace(/^[\d]+[.)]\s*/, "")
    // Remove leading bullets
    .replace(/^[-•*]\s*/, "")
    // Clean up markdown bold
    .replace(/\*\*/g, "")
    // Convert markdown links to just the text: [text](url) -> text
    .replace(/\[([^\]]+)\]\s*\([^)]+\)/g, "$1")
    // Remove standalone full URLs (but keep partial references)
    .replace(/https?:\/\/[^\s)]+/g, "")
    // Clean up empty parentheses left over
    .replace(/\(\s*\)/g, "")
    // Clean up excessive whitespace
    .replace(/\s+/g, " ")
    .trim();
};

// Check if a step is valid content (not a header or artifact)
const isValidStep = (text: string): boolean => {
  const cleaned = text.trim().toLowerCase();
  // Filter out headers and artifacts
  if (cleaned.startsWith("/ remedy") || cleaned.startsWith("remedy:")) return false;
  if (cleaned.startsWith("/ repair") || cleaned.startsWith("repair:")) return false;
  if (cleaned.length < 10) return false;
  return true;
};

const RepairStepList = ({ steps, type = "repair" }: RepairStepListProps) => {
  const processedSteps = useMemo(() => {
    return steps
      .filter(step => isValidStep(step)) // Filter out headers and artifacts first
      .map((step, index) => {
        const cleaned = cleanStepText(step);
        const icon = getStepIcon(cleaned);
        const isSafetyStep = cleaned.toLowerCase().includes("unplug") || 
                            cleaned.toLowerCase().includes("disconnect") ||
                            cleaned.toLowerCase().includes("power off") ||
                            cleaned.toLowerCase().includes("safety");
        
        return {
          index,
          icon,
          text: cleaned,
          isSafetyStep,
        };
      })
      .filter(step => step.text.length > 0); // Remove any that cleaned to empty
  }, [steps]);

  if (processedSteps.length === 0) {
    return <p className="muted">No {type === "verify" ? "verification" : "repair"} steps provided for this issue.</p>;
  }

  return (
    <ol className={clsx("enhanced-step-list", `step-list-${type}`)}>
      {processedSteps.map((step) => (
        <li 
          key={step.index} 
          className={clsx("enhanced-step-item", { "step-safety": step.isSafetyStep })}
        >
          <span className="step-icon" aria-hidden="true">{step.icon}</span>
          <span className="step-number">{step.index + 1}</span>
          <span className="step-content">{step.text}</span>
        </li>
      ))}
    </ol>
  );
};

export default RepairStepList;


