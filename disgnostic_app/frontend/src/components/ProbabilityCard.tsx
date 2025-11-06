import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { clsx } from "clsx";

import { OutcomeStatus, ProbabilityItem } from "../types";

interface ProbabilityCardProps {
  item: ProbabilityItem;
  index: number;
  outcome: OutcomeStatus;
  onOutcomeChange: (title: string, outcome: OutcomeStatus) => void;
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

const linkPattern = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;

const renderWithLinks = (text?: string): ReactNode => {
  if (!text) return null;

  const matches = [...text.matchAll(linkPattern)];
  if (matches.length === 0) {
    return text;
  }

  const nodes: ReactNode[] = [];
  let lastIndex = 0;

  matches.forEach((match) => {
    const [fullMatch, label, url] = match;
    const index = match.index ?? 0;

    if (index > lastIndex) {
      nodes.push(text.slice(lastIndex, index));
    }

    nodes.push(
      <a key={`${url}-${index}`} href={url} target="_blank" rel="noreferrer">
        {label}
      </a>,
    );

    lastIndex = index + fullMatch.length;
  });

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
};

export const ProbabilityCard = ({ item, index, outcome, onOutcomeChange }: ProbabilityCardProps) => {
  const [sections, setSections] = useState({
    verify: false,
    parts: false,
    video: false,
    repair: false,
  });

  const details = item.details;

  const toggleSection = (key: keyof typeof sections) => {
    setSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const severityClass = severityMap(item.percent);

  const tagline = useMemo(() => {
    if (!details) return [];
    const chips: string[] = [];
    if (details.difficulty) chips.push(`Difficulty ${details.difficulty}`);
    if (details.time) chips.push(`Time ${details.time}`);
    return chips;
  }, [details]);

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
          <p className="prob-description">{item.description}</p>
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
          <p>{renderWithLinks(details.explanation) ?? details.explanation}</p>
        </div>
      )}

      <div className="toggle-grid">
        <button
          type="button"
          className={clsx("toggle-btn", { active: sections.verify })}
          onClick={() => toggleSection("verify")}
        >
          ✅ Verify
        </button>
        <button
          type="button"
          className={clsx("toggle-btn", { active: sections.parts })}
          onClick={() => toggleSection("parts")}
        >
          🔩 Part #
        </button>
        <button
          type="button"
          className={clsx("toggle-btn", { active: sections.video })}
          onClick={() => toggleSection("video")}
        >
          🎥 Videos
        </button>
        <button
          type="button"
          className={clsx("toggle-btn", { active: sections.repair })}
          onClick={() => toggleSection("repair")}
        >
          📖 Repair
        </button>
      </div>

      {sections.verify && (
        <div className="prob-section">
          <h4>Verification Steps</h4>
          {details?.verify_steps?.length ? (
            <ol className="step-list">
              {details.verify_steps.map((step) => (
                <li key={step}>{renderWithLinks(step) ?? step}</li>
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
                  <li key={warning}>{renderWithLinks(warning) ?? warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}

      {sections.parts && (
        <div className="prob-section">
          <h4>Parts Needed</h4>
          {details?.parts?.length ? (
            <ul className="part-list">
              {details.parts.map((part) => {
                const formatted = formatPartLine(part);
                return <li key={part}>{renderWithLinks(formatted) ?? formatted}</li>;
              })}
            </ul>
          ) : (
            <p className="muted">No specific part recommendations were supplied.</p>
          )}
        </div>
      )}

      {sections.video && (
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

      {sections.repair && (
        <div className="prob-section">
          <h4>Repair Playbook</h4>
          {details?.repair_steps?.length ? (
            <ol className="step-list">
              {details.repair_steps.map((step) => (
                <li key={step}>{renderWithLinks(step) ?? step}</li>
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
      </div>
    </article>
  );
};

export default ProbabilityCard;

