import { useMemo } from "react";
import { clsx } from "clsx";

interface RepairStepListProps {
  steps: string[];
  type?: "repair" | "verify";
}

// Patterns to identify and highlight different elements
const PATTERNS = {
  // Part numbers: alphanumeric, 7+ chars, may have dashes
  partNumber: /\b([A-Z]{0,3}[A-Z0-9]{6,}(?:-[A-Z0-9]+)?)\b/gi,
  // Tools: common tools mentioned in repairs
  tools: /\b(multimeter|ohmmeter|voltmeter|clamp meter|manometer|thermometer|screwdriver|wrench|socket|pliers|heat gun|torch|gauge|probe|tester)\b/gi,
  // Measurements: numbers with units
  measurements: /\b(\d+(?:\.\d+)?)\s*(ohms?|Ω|volts?|V|amps?|A|watts?|W|PSI|psi|°?[FC]|degrees?|minutes?|mins?|seconds?|secs?|inches?|in|mm|cm|ft-lbs?|Nm)\b/gi,
  // Safety keywords
  safety: /\b(WARNING|CAUTION|DANGER|unplug|disconnect|power off|de-energize|turn off|safety|PPE|gloves|goggles|energized)\b/gi,
  // Positive outcomes
  positive: /\b(should show|should read|expect|normal|good|correct|properly)\b/gi,
  // Negative/problem indicators
  negative: /\b(faulty|failed|broken|bad|defective|damaged|burnt|open circuit|short circuit|no continuity)\b/gi,
};

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

// Parse step text and create highlighted spans
const parseStepContent = (text: string): React.ReactNode[] => {
  const elements: React.ReactNode[] = [];
  let lastIndex = 0;
  
  // Collect all matches with their positions
  interface Match {
    start: number;
    end: number;
    text: string;
    type: "part" | "tool" | "measurement" | "safety" | "positive" | "negative";
  }
  
  const matches: Match[] = [];
  
  // Find part numbers
  let match: RegExpExecArray | null;
  const partPattern = new RegExp(PATTERNS.partNumber.source, "gi");
  while ((match = partPattern.exec(text)) !== null) {
    matches.push({ start: match.index, end: match.index + match[0].length, text: match[0], type: "part" });
  }
  
  // Find tools
  const toolPattern = new RegExp(PATTERNS.tools.source, "gi");
  while ((match = toolPattern.exec(text)) !== null) {
    matches.push({ start: match.index, end: match.index + match[0].length, text: match[0], type: "tool" });
  }
  
  // Find measurements
  const measurePattern = new RegExp(PATTERNS.measurements.source, "gi");
  while ((match = measurePattern.exec(text)) !== null) {
    matches.push({ start: match.index, end: match.index + match[0].length, text: match[0], type: "measurement" });
  }
  
  // Find safety keywords
  const safetyPattern = new RegExp(PATTERNS.safety.source, "gi");
  while ((match = safetyPattern.exec(text)) !== null) {
    matches.push({ start: match.index, end: match.index + match[0].length, text: match[0], type: "safety" });
  }
  
  // Sort by position and remove overlaps
  matches.sort((a, b) => a.start - b.start);
  const filteredMatches: Match[] = [];
  let lastEnd = 0;
  for (const m of matches) {
    if (m.start >= lastEnd) {
      filteredMatches.push(m);
      lastEnd = m.end;
    }
  }
  
  // Build elements
  for (const m of filteredMatches) {
    // Add text before this match
    if (m.start > lastIndex) {
      elements.push(<span key={`text-${lastIndex}`}>{text.slice(lastIndex, m.start)}</span>);
    }
    
    // Add highlighted match
    elements.push(
      <span key={`match-${m.start}`} className={`step-highlight step-highlight-${m.type}`}>
        {m.text}
      </span>
    );
    
    lastIndex = m.end;
  }
  
  // Add remaining text
  if (lastIndex < text.length) {
    elements.push(<span key={`text-${lastIndex}`}>{text.slice(lastIndex)}</span>);
  }
  
  return elements.length > 0 ? elements : [text];
};

// Clean up common LLM formatting issues
const cleanStepText = (text: string): string => {
  return text
    // Remove leading numbers/bullets that might be duplicated
    .replace(/^[\d]+\.\s*/, "")
    .replace(/^[-•]\s*/, "")
    // Clean up markdown bold
    .replace(/\*\*/g, "")
    // Clean up excessive whitespace
    .replace(/\s+/g, " ")
    .trim();
};

const RepairStepList = ({ steps, type = "repair" }: RepairStepListProps) => {
  const processedSteps = useMemo(() => {
    return steps.map((step, index) => {
      const cleaned = cleanStepText(step);
      const icon = getStepIcon(cleaned);
      const content = parseStepContent(cleaned);
      const isSafetyStep = cleaned.toLowerCase().includes("unplug") || 
                          cleaned.toLowerCase().includes("disconnect") ||
                          cleaned.toLowerCase().includes("power off") ||
                          cleaned.toLowerCase().includes("safety");
      
      return {
        index,
        icon,
        content,
        isSafetyStep,
        original: cleaned,
      };
    });
  }, [steps]);

  if (!steps.length) {
    return <p className="muted">No steps provided.</p>;
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
          <span className="step-content">{step.content}</span>
        </li>
      ))}
    </ol>
  );
};

export default RepairStepList;

