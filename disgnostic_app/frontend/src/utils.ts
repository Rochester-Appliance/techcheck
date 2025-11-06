import { DiagnosisFormValues, DiagnosisResponse } from "./types";

export const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const formatTimestamp = (iso?: string) => {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString();
};

export const createReportContent = (
  formValues: DiagnosisFormValues,
  diagnosis: DiagnosisResponse,
): string => {
  const lines = [
    "TECHCHECK DIAGNOSTIC REPORT",
    `Generated: ${formatTimestamp(diagnosis.timestamp)}`,
    "",
    `Tech: ${formValues.techName}`,
    `Job: ${formValues.jobNumber}`,
    `Model: ${diagnosis.model_number}`,
    `Symptoms: ${formValues.problemDescription}`,
    "",
    "PROBABILITY DISTRIBUTION:",
  ];

  diagnosis.probabilities.forEach((item) => {
    lines.push(`- [${item.percent}%] ${item.title} — ${item.description}`);
    const details = item.details;
    if (details) {
      if (details.explanation) {
        lines.push(`  Explanation: ${details.explanation}`);
      }
      if (details.parts?.length) {
        lines.push(`  Parts:`);
        details.parts.forEach((part) => lines.push(`    • ${part}`));
      }
      if (details.verify_steps?.length) {
        lines.push(`  Verification Steps:`);
        details.verify_steps.forEach((step, index) =>
          lines.push(`    ${index + 1}. ${step}`),
        );
      }
      if (details.repair_steps?.length) {
        lines.push(`  Repair Steps:`);
        details.repair_steps.forEach((step, index) =>
          lines.push(`    ${index + 1}. ${step}`),
        );
      }
    }
    lines.push("");
  });

  if (diagnosis.web_results.length) {
    lines.push("WEB SOURCES:");
    diagnosis.web_results.forEach((result, index) => {
      lines.push(`${index + 1}. ${result.title}`);
      lines.push(`   ${result.url}`);
      if (result.snippet) {
        lines.push(`   ${result.snippet}`);
      }
      lines.push("");
    });
  }

  lines.push("FULL RAW ANALYSIS:");
  lines.push(diagnosis.full_analysis);

  return lines.join("\n");
};

export const downloadReport = (
  content: string,
  filename = "diagnostic_report.txt",
) => {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
};

