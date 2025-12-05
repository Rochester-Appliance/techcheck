import jsPDF from "jspdf";

import {
  DiagnosisFormValues,
  DiagnosisResponse,
  ProbabilityItem,
  SourceLink,
  VNVDiagramSummary,
  VNVPartSummary,
} from "./types";

// ---------------------------------------------------------------------------
// Part Number Extraction & Matching Utilities
// ---------------------------------------------------------------------------

/**
 * Extract part numbers from diagnosis text.
 * Matches patterns like EDR1RXD1, WPW10179146, W11700250
 */
export const extractPartNumbers = (text: string): string[] => {
  if (!text) return [];
  // Match alphanumeric part numbers: optional 1-3 letter prefix + 6-12 alphanumeric chars
  const pattern = /\b([A-Z]{1,3})?[A-Z0-9]{6,12}\b/gi;
  const matches = text.match(pattern) || [];
  // Dedupe and normalize to uppercase
  return [...new Set(matches.map((p) => p.toUpperCase()))];
};

/**
 * Extract all part numbers from an array of part description strings.
 */
export const extractPartNumbersFromList = (parts: string[]): string[] => {
  const allNumbers: string[] = [];
  parts.forEach((part) => {
    allNumbers.push(...extractPartNumbers(part));
  });
  return [...new Set(allNumbers)];
};

/**
 * Represents a part from the diagnosis matched to V&V data.
 */
export interface MatchedPart {
  partNumber: string;
  vnvPart: VNVPartSummary;
  diagram: VNVDiagramSummary;
}

/**
 * Match extracted part numbers against V&V diagram data.
 * Returns matched parts with their V&V info and diagram section.
 */
export const matchPartsToDiagrams = (
  partNumbers: string[],
  diagrams: VNVDiagramSummary[],
): MatchedPart[] => {
  const matches: MatchedPart[] = [];
  const seen = new Set<string>();

  for (const partNumber of partNumbers) {
    const normalized = partNumber.toUpperCase().replace(/-/g, "");

    for (const diagram of diagrams) {
      for (const vnvPart of diagram.parts) {
        const vnvNormalized = (vnvPart.part_number || "").toUpperCase().replace(/-/g, "");

        if (vnvNormalized === normalized && !seen.has(partNumber)) {
          matches.push({
            partNumber,
            vnvPart,
            diagram,
          });
          seen.add(partNumber);
          break; // Found match for this part, move to next
        }
      }
      if (seen.has(partNumber)) break; // Already matched, skip remaining diagrams
    }
  }

  return matches;
};

/**
 * Get unique diagrams from matched parts (for diagram thumbnail display).
 */
export const getUniqueDiagramsFromMatches = (matches: MatchedPart[]): VNVDiagramSummary[] => {
  const seen = new Set<number>();
  const unique: VNVDiagramSummary[] = [];

  for (const match of matches) {
    if (!seen.has(match.diagram.diagram_id)) {
      seen.add(match.diagram.diagram_id);
      unique.push(match.diagram);
    }
  }

  return unique;
};

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

const markdownLinkPattern = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/gi;
const bareUrlPattern = /https?:\/\/[^\s)]+/gi;
const domainPattern = /^[\w.-]+\.[a-z]{2,}$/i;

const normalizeWhitespace = (text: string) =>
  text
    .split("\n")
    .map((line) => line.replace(/\s{2,}/g, " ").trimEnd())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

const cleanDomainLabel = (label: string) => label.replace(/[\[\]\(\)]/g, "").trim();

export const extractMarkdownLinks = (text?: string | null) => {
  if (!text) return [];
  const matches: { label: string; url: string }[] = [];
  const cloned = text;
  let match: RegExpExecArray | null;
  while ((match = markdownLinkPattern.exec(cloned)) !== null) {
    matches.push({ label: match[1].trim(), url: match[2].trim() });
  }
  return matches;
};

export const sanitizeRichText = (text?: string) => {
  if (!text) return "";
  const withoutMarkdown = text.replace(markdownLinkPattern, (_, label: string) => {
    const trimmed = cleanDomainLabel(label);
    return domainPattern.test(trimmed) ? "" : trimmed;
  });
  const withoutUrls = withoutMarkdown.replace(bareUrlPattern, "");
  const withoutEmptyParens = withoutUrls.replace(/\(\s*\)/g, "");
  return normalizeWhitespace(withoutEmptyParens);
};

const addSourceLink = (
  collection: Map<string, SourceLink>,
  label: string | null | undefined,
  url: string,
  origin: SourceLink["origin"],
  snippet?: string | null,
) => {
  if (!url) return;
  const key = url.trim();
  if (!collection.has(key)) {
    const fallbackLabel = label?.trim() || (() => {
      try {
        const { hostname } = new URL(url);
        return hostname;
      } catch {
        return url;
      }
    })();
    collection.set(key, {
      label: fallbackLabel,
      url: key,
      origin,
      snippet: snippet ?? null,
    });
  }
};

const gatherLinksFromProbability = (item: ProbabilityItem, store: Map<string, SourceLink>) => {
  [item.description, item.details?.explanation].forEach((section) => {
    extractMarkdownLinks(section).forEach(({ label, url }) =>
      addSourceLink(store, label, url, "inline"),
    );
  });

  if (!item.details) return;

  const listSections = [
    item.details.parts,
    item.details.verify_steps,
    item.details.repair_steps,
    item.details.safety_warnings,
    item.details.video_searches,
  ];

  listSections.forEach((section) => {
    section?.forEach((entry) => {
      extractMarkdownLinks(entry).forEach(({ label, url }) =>
        addSourceLink(store, label, url, "inline"),
      );
    });
  });
};

export const collectSourceLinks = (diagnosis?: DiagnosisResponse) => {
  if (!diagnosis) return [];

  const store = new Map<string, SourceLink>();

  diagnosis.probabilities.forEach((prob) => gatherLinksFromProbability(prob, store));
  extractMarkdownLinks(diagnosis.full_analysis).forEach(({ label, url }) =>
    addSourceLink(store, label, url, "inline"),
  );

  return Array.from(store.values());
};

const PAGE_MARGIN = 48;
const LINE_HEIGHT = 16;

const addWrappedText = (doc: jsPDF, text: string, cursor: number) => {
  const pageWidth = doc.internal.pageSize.getWidth() - PAGE_MARGIN * 2;
  const chunks = doc.splitTextToSize(text, pageWidth);
  const lines = Array.isArray(chunks) ? chunks : [chunks];
  let y = cursor;
  lines.forEach((line) => {
    if (y > doc.internal.pageSize.getHeight() - PAGE_MARGIN) {
      doc.addPage();
      y = PAGE_MARGIN;
    }
    doc.text(line, PAGE_MARGIN, y);
    y += LINE_HEIGHT;
  });
  return y;
};

const addSectionHeading = (doc: jsPDF, text: string, cursor: number, size = 13) => {
  let y = cursor;
  if (y > doc.internal.pageSize.getHeight() - PAGE_MARGIN) {
    doc.addPage();
    y = PAGE_MARGIN;
  }
  doc.setFont("helvetica", "bold");
  doc.setFontSize(size);
  doc.text(text, PAGE_MARGIN, y);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);
  return y + LINE_HEIGHT;
};

export const downloadReport = (
  formValues: DiagnosisFormValues,
  diagnosis: DiagnosisResponse,
  sources: SourceLink[] = [],
) => {
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  let cursor = PAGE_MARGIN;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  cursor = addWrappedText(doc, "TechCheck Beta – Diagnostic Report", cursor);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);
  const summaryLines = [
    `Generated: ${formatTimestamp(diagnosis.timestamp)}`,
    `Technician: ${formValues.techName || diagnosis.tech_name || "—"}`,
    `Job #: ${formValues.jobNumber || diagnosis.job_number || "—"}`,
    `Model: ${diagnosis.model_number}`,
    `Symptoms: ${sanitizeRichText(formValues.problemDescription || diagnosis.problem || "")}`,
  ];
  summaryLines.forEach((line) => {
    cursor = addWrappedText(doc, line, cursor);
  });
  cursor += LINE_HEIGHT;

  diagnosis.probabilities.forEach((prob, index) => {
    cursor = addSectionHeading(
      doc,
      `#${index + 1} ${prob.title} (${prob.percent}%)`,
      cursor,
    );
    cursor = addWrappedText(doc, sanitizeRichText(prob.description), cursor);

    if (prob.details?.difficulty || prob.details?.time) {
      const diff = prob.details?.difficulty ? `Difficulty ${prob.details.difficulty}` : null;
      const time = prob.details?.time ? `Time ${prob.details.time}` : null;
      const chips = [diff, time].filter(Boolean).join(" • ");
      cursor = addWrappedText(doc, chips, cursor);
    }

    if (prob.details?.explanation) {
      cursor = addWrappedText(
        doc,
        `Why it matters: ${sanitizeRichText(prob.details.explanation)}`,
        cursor,
      );
    }

    const listBlocks: Array<[string, string[] | undefined]> = [
      ["Verification", prob.details?.verify_steps],
      ["Parts", prob.details?.parts],
      ["Repair", prob.details?.repair_steps],
      ["Safety", prob.details?.safety_warnings],
    ];

    listBlocks.forEach(([label, items]) => {
      if (items?.length) {
        cursor = addWrappedText(doc, `${label}:`, cursor);
        items.forEach((entry, itemIndex) => {
          cursor = addWrappedText(doc, `${itemIndex + 1}. ${sanitizeRichText(entry)}`, cursor);
        });
      }
    });

    cursor += LINE_HEIGHT;
  });

  if (sources.length) {
    cursor = addSectionHeading(doc, "Sources & References", cursor);
    sources.forEach((source, index) => {
      cursor = addWrappedText(
        doc,
        `${index + 1}. ${source.label} — ${source.url}`,
        cursor,
      );
    });
  }

  const filename = `techcheck_${diagnosis.model_number}_${Date.now()}.pdf`;
  doc.save(filename);
};

