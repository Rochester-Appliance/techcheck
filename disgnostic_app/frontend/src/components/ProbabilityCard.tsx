import { useMemo, useState } from "react";
import { clsx } from "clsx";

import { DiagramBundleResponse, OutcomeStatus, ProbabilityItem } from "../types";
import {
  extractPartNumbersFromList,
  getUniqueDiagramsFromMatches,
  matchPartsToDiagrams,
  sanitizeRichText,
} from "../utils";
import LinkedPartsCard from "./LinkedPartsCard";
import DiagramThumbnailCard from "./DiagramThumbnailCard";

interface ProbabilityCardProps {
  item: ProbabilityItem;
  index: number;
  outcome: OutcomeStatus;
  onOutcomeChange: (title: string, outcome: OutcomeStatus) => void;
  diagramBundle: DiagramBundleResponse | null;
}

const severityMap = (percent: number) => {
  if (percent >= 40) return "severity-high";
  if (percent >= 20) return "severity-medium";
  return "severity-low";
};

const formatPartLine = (line: string) => {
  const partPattern = /(\b[A-Z0-9]{7,}\b)(\s*[–—-]\s*)?(.*)/i;
  const match = line.match(partPattern);
  if (!match) return line;

  const [, partNumber, , rest] = match;
  if (!rest) return partNumber.toUpperCase();
  return `${partNumber.toUpperCase()} — ${rest.trim()}`;
};

const createYoutubeLink = (query: string) =>
  `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;

const truncateChip = (value: string, limit = 64) =>
  value.length > limit ? `${value.slice(0, limit - 1)}…` : value;

export const ProbabilityCard = ({
  item,
  index,
  outcome,
  onOutcomeChange,
  diagramBundle,
}: ProbabilityCardProps) => {
  const [activeSection, setActiveSection] = useState<"verify" | "parts" | "video" | "repair" | null>(
    null,
  );

  const details = item.details;

  const toggleSection = (key: "verify" | "parts" | "video" | "repair") => {
    setActiveSection((prev) => (prev === key ? null : key));
  };

  const severityClass = severityMap(item.percent);

  const tagline = useMemo(() => {
    if (!details) return [];
    const chips: string[] = [];
    if (details.difficulty) chips.push(`Difficulty ${truncateChip(details.difficulty)}`);
    if (details.time) chips.push(`Time ${truncateChip(details.time)}`);
    return chips;
  }, [details]);

  // Extract part numbers from the parts list and match against V&V diagrams
  const { matchedParts, matchedDiagrams } = useMemo(() => {
    if (!details?.parts?.length || !diagramBundle?.diagrams?.length) {
      return { matchedParts: [], matchedDiagrams: [] };
    }

    const partNumbers = extractPartNumbersFromList(details.parts);
    const matched = matchPartsToDiagrams(partNumbers, diagramBundle.diagrams);
    const diagrams = getUniqueDiagramsFromMatches(matched);

    return { matchedParts: matched, matchedDiagrams: diagrams };
  }, [details?.parts, diagramBundle?.diagrams]);

  const hasMatches = matchedParts.length > 0 || matchedDiagrams.length > 0;

  return (
    <article className={clsx("probability-card", severityClass)}>
      <div className="prob-header">
        <div className="prob-badge">
          <span className="prob-value">{item.percent}%</span>
          <span className="prob-label">Probability</span>
        </div>
        <div className="prob-content">
          <h3>
            <span className="prob-index">#{index + 1}</span> {item.title}
          </h3>
          <p className="prob-description">{sanitizeRichText(item.description)}</p>
          {tagline.length > 0 && (
            <div className="chip-row">
              {tagline.map((chip) => (
                <span className="chip" key={chip}>
                  {chip}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {details?.explanation && (
        <div className="prob-section">
          <h4>Why this matters</h4>
          <p>{sanitizeRichText(details.explanation)}</p>
        </div>
      )}

      <div className="toggle-grid">
        <button
          type="button"
          className={clsx("toggle-btn", { active: activeSection === "verify" })}
          onClick={() => toggleSection("verify")}
        >
          ✅ Verify
        </button>
        <button
          type="button"
          className={clsx("toggle-btn", { active: activeSection === "parts" })}
          onClick={() => toggleSection("parts")}
        >
          🔩 Part #
        </button>
        <button
          type="button"
          className={clsx("toggle-btn", { active: activeSection === "video" })}
          onClick={() => toggleSection("video")}
        >
          🎥 Videos
        </button>
        <button
          type="button"
          className={clsx("toggle-btn", { active: activeSection === "repair" })}
          onClick={() => toggleSection("repair")}
        >
          📖 Repair
        </button>
      </div>

      {activeSection === "verify" && (
        <div className="prob-section">
          <h4>Verification Steps</h4>
          {details?.verify_steps?.length ? (
            <ol className="step-list">
              {details.verify_steps.map((step) => (
                <li key={step}>{sanitizeRichText(step)}</li>
              ))}
            </ol>
          ) : (
            <p className="muted">No specific verification steps provided.</p>
          )}

          {details?.safety_warnings?.length ? (
            <div className="warning-box">
              <h5>Safety Warnings</h5>
              <ul>
                {details.safety_warnings.map((warning) => (
                  <li key={warning}>{sanitizeRichText(warning)}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}

      {activeSection === "parts" && (
        <div className="prob-section">
          <h4>Parts Needed</h4>

          {/* Show linked parts and diagram cards when matches exist */}
          {hasMatches && (
            <div className="parts-diagrams-row">
              <LinkedPartsCard matchedParts={matchedParts} />
              <DiagramThumbnailCard diagrams={matchedDiagrams} />
            </div>
          )}

          {/* Original text-only parts list */}
          {details?.parts?.length ? (
            <ul className="part-list">
              {details.parts.map((part) => {
                const formatted = formatPartLine(part);
                return <li key={part}>{sanitizeRichText(formatted)}</li>;
              })}
            </ul>
          ) : (
            <p className="muted">No specific part recommendations were supplied.</p>
          )}
        </div>
      )}

      {activeSection === "video" && (
        <div className="prob-section">
          <h4>Video Tutorials</h4>
          {details?.video_searches?.length ? (
            <ul className="video-list">
              {details.video_searches.map((video) => (
                <li key={video}>
                  <a href={createYoutubeLink(video)} target="_blank" rel="noreferrer">
                    {video}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">
              Try searching YouTube for “{item.title} {details?.time ? `repair ${details.time}` : "repair"}”.
            </p>
          )}
        </div>
      )}

      {activeSection === "repair" && (
        <div className="prob-section">
          <h4>Repair Playbook</h4>
          {details?.repair_steps?.length ? (
            <ol className="step-list">
              {details.repair_steps.map((step) => (
                <li key={step}>{sanitizeRichText(step)}</li>
              ))}
            </ol>
          ) : (
            <p className="muted">No detailed repair steps were provided for this issue.</p>
          )}
        </div>
      )}

      <div className="prob-section outcome-section">
        <h4>Did this solve the problem?</h4>
        <div className="outcome-buttons">
          <button
            type="button"
            className={clsx("btn", "btn-outcome", "btn-success", {
              active: outcome === "resolved",
            })}
            onClick={() => onOutcomeChange(item.title, outcome === "resolved" ? null : "resolved")}
          >
            Yes, resolved
          </button>
          <button
            type="button"
            className={clsx("btn", "btn-outcome", "btn-warning", {
              active: outcome === "unresolved",
            })}
            onClick={() =>
              onOutcomeChange(item.title, outcome === "unresolved" ? null : "unresolved")
            }
          >
            No, not yet
          </button>
        </div>
        {outcome === "resolved" && (
          <p className="outcome-message success">Great news. Thank you for your feedback.</p>
        )}
        {outcome === "unresolved" && (
          <p className="outcome-message warning">
            Bummer. Try the next option below for your best odds of repair.
          </p>
        )}
      </div>
    </article>
  );
};

export default ProbabilityCard;

