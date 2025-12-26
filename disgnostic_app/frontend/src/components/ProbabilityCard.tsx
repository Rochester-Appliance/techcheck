import { useCallback, useEffect, useMemo, useState } from "react";
import { clsx } from "clsx";
import axios from "axios";

import { DiagramBundleResponse, OutcomeStatus, ProbabilityItem } from "../types";
import {
  extractPartNumbersFromList,
  getUniqueDiagramsFromMatches,
  matchPartsToDiagrams,
  sanitizeRichText,
} from "../utils";
import LinkedPartsCard from "./LinkedPartsCard";
import DiagramThumbnailCard from "./DiagramThumbnailCard";
import { VideoCardGrid, YouTubeVideo } from "./VideoCard";
import RepairStepList from "./RepairStepList";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

interface ProbabilityCardProps {
  item: ProbabilityItem;
  index: number;
  isLastCard?: boolean;
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

const truncateChip = (value: string, limit = 64) =>
  value.length > limit ? `${value.slice(0, limit - 1)}…` : value;

export const ProbabilityCard = ({
  item,
  index,
  isLastCard = false,
  outcome,
  onOutcomeChange,
  diagramBundle,
}: ProbabilityCardProps) => {
  const [activeSection, setActiveSection] = useState<"verify" | "parts" | "video" | "repair" | null>(
    null,
  );
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showContactModal, setShowContactModal] = useState(false);

  // Video fetching state
  const [videos, setVideos] = useState<YouTubeVideo[]>([]);
  const [videosLoading, setVideosLoading] = useState(false);
  const [videosError, setVideosError] = useState<string | null>(null);
  const [videosFetched, setVideosFetched] = useState(false);

  const details = item.details;

  // Build the search query for videos
  const videoSearchQuery = useMemo(() => {
    if (details?.video_searches?.length) {
      return details.video_searches[0]; // Use the first suggested search
    }
    return `${item.title} appliance repair`;
  }, [details?.video_searches, item.title]);

  // Fetch videos from backend
  const fetchVideos = useCallback(async () => {
    if (videosFetched || videosLoading) return;
    
    setVideosLoading(true);
    setVideosError(null);
    
    try {
      const response = await axios.get(`${API_BASE}/api/youtube/search`, {
        params: { q: videoSearchQuery, max_results: 3 },
      });
      setVideos(response.data.videos || []);
      setVideosFetched(true);
    } catch (err) {
      console.error("Failed to fetch videos:", err);
      setVideosError("Unable to load video previews");
      setVideosFetched(true);
    } finally {
      setVideosLoading(false);
    }
  }, [videoSearchQuery, videosFetched, videosLoading]);

  // Fetch videos when video section is opened
  useEffect(() => {
    if (activeSection === "video" && !videosFetched) {
      fetchVideos();
    }
  }, [activeSection, videosFetched, fetchVideos]);

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

  const handleNoClick = () => {
    onOutcomeChange(item.title, outcome === "unresolved" ? null : "unresolved");
    // For the last card, show contact modal instead of collapsing
    if (isLastCard) {
      if (outcome !== "unresolved") {
        setShowContactModal(true);
      }
    } else {
      // Collapse the card when user clicks "No, not yet"
      if (outcome !== "unresolved") {
        setIsCollapsed(true);
        setActiveSection(null);
      }
    }
  };

  const handleExpandCard = () => {
    setIsCollapsed(false);
  };

  return (
    <article className={clsx("probability-card", severityClass, { "card-collapsed": isCollapsed })}>
      <div className="prob-header">
        <div className="prob-badge">
          <span className="prob-value">{item.percent}%</span>
          <span className="prob-label">Probability</span>
        </div>
        <div className="prob-content">
          <h3>
            <span className="prob-index">#{index + 1}</span> {item.title}
          </h3>
          {!isCollapsed && (
            <>
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
            </>
          )}
          {isCollapsed && (
            <button
              type="button"
              className="btn btn-link expand-card-btn"
              onClick={handleExpandCard}
            >
              Show details again
            </button>
          )}
        </div>
      </div>

      {!isCollapsed && (
        <>
          {details?.explanation && (
            <div className="prob-section insight-section">
              <h4>Diagnostic Insight</h4>
              <ul className="insight-list">
                {sanitizeRichText(details.explanation)
                  .split(/\n|(?:^|\s)-\s/)
                  .filter((line) => line.trim())
                  .map((point, idx) => (
                    <li key={idx} className="insight-item">
                      <span className="insight-icon">💡</span>
                      <span className="insight-text">{point.trim()}</span>
                    </li>
                  ))}
              </ul>
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
                <RepairStepList steps={details.verify_steps} type="verify" />
              ) : (
                <p className="muted">No specific verification steps provided.</p>
              )}

              {details?.safety_warnings?.length ? (
                <div className="warning-box">
                  <h5>⚠️ Safety Warnings</h5>
                  <ul className="safety-list">
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
              <VideoCardGrid
                videos={videos}
                loading={videosLoading}
                error={videosError}
                fallbackQuery={videoSearchQuery}
              />
            </div>
          )}

          {activeSection === "repair" && (
            <div className="prob-section">
              <h4>Repair Playbook</h4>
              {details?.repair_steps?.length ? (
                <RepairStepList steps={details.repair_steps} type="repair" />
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
                onClick={handleNoClick}
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
        </>
      )}

      {isCollapsed && outcome === "unresolved" && (
        <p className="outcome-message warning collapsed-message">
          Bummer. Try the next option below for your best odds of repair.
        </p>
      )}

      {/* Contact modal for last card */}
      {showContactModal && (
        <div
          className="contact-modal-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowContactModal(false);
            }
          }}
        >
          <div className="contact-modal">
            <h3>Need More Help?</h3>
            <p>
              If none of the suggested solutions resolved your issue, our team is here to help.
            </p>
            <div className="contact-modal-info">
              <span className="contact-icon">📧</span>
              <div>
                <p className="contact-label">Contact us at:</p>
                <a href="mailto:dean@rochesterappliance.com" className="contact-email">
                  dean@rochesterappliance.com
                </a>
              </div>
            </div>
            <button
              type="button"
              className="btn btn-secondary contact-modal-close"
              onClick={() => setShowContactModal(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </article>
  );
};

export default ProbabilityCard;

