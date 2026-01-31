import { useCallback, useEffect, useMemo, useState } from "react";
import { clsx } from "clsx";
import axios from "axios";

import { AIProvider, DiagramBundleResponse, OutcomeStatus, ProbabilityItem } from "../types";
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
  onRetryParts?: () => void;
  partsLoading?: boolean;
  modelNumber?: string;
  symptoms?: string;
  aiProvider?: AIProvider;
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
  onRetryParts,
  partsLoading = false,
  modelNumber,
  aiProvider = "openai",
  symptoms,
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

  // Sub-query states for verify/repair retry
  const [verifyStepsOverride, setVerifyStepsOverride] = useState<string[] | null>(null);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [repairStepsOverride, setRepairStepsOverride] = useState<string[] | null>(null);
  const [repairLoading, setRepairLoading] = useState(false);
  const [safetyWarningsOverride, setSafetyWarningsOverride] = useState<string[] | null>(null);

  // Parts sub-query states
  const [partsOverride, setPartsOverride] = useState<Array<{part_number: string; description: string}> | null>(null);
  const [partsSubQueryLoading, setPartsSubQueryLoading] = useState(false);
  const [noPartsRequired, setNoPartsRequired] = useState(false);
  const [noPartsMessage, setNoPartsMessage] = useState<string | null>(null);

  // Reset video state when item changes (e.g., new diagnosis)
  useEffect(() => {
    setVideos([]);
    setVideosFetched(false);
    setVideosError(null);
    // Also reset sub-query overrides
    setVerifyStepsOverride(null);
    setRepairStepsOverride(null);
    setSafetyWarningsOverride(null);
    setPartsOverride(null);
    setNoPartsRequired(false);
    setNoPartsMessage(null);
  }, [item.title]);

  const details = item.details;

  // Clean up search query - remove curly quotes and special chars from LLM output
  const cleanSearchQuery = (query: string): string => {
    return query
      // Replace curly quotes with nothing
      .replace(/[""„‟❝❞〝〞＂]/g, "")
      // Replace curly apostrophes
      .replace(/[''‚‛❛❜]/g, "'")
      // Remove other special unicode punctuation
      .replace(/[«»‹›]/g, "")
      // Clean up extra whitespace
      .replace(/\s+/g, " ")
      .trim();
  };

  // Build the search query for videos
  const videoSearchQuery = useMemo(() => {
    if (details?.video_searches?.length) {
      // Clean up the LLM-provided search query
      return cleanSearchQuery(details.video_searches[0]);
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

  // Retry video fetch (resets state and re-fetches)
  const retryVideos = useCallback(() => {
    setVideos([]);
    setVideosFetched(false);
    setVideosError(null);
    setVideosLoading(true);
    
    axios.get(`${API_BASE}/api/youtube/search`, {
      params: { q: videoSearchQuery, max_results: 3 },
    })
      .then((response) => {
        setVideos(response.data.videos || []);
        setVideosFetched(true);
      })
      .catch((err) => {
        console.error("Failed to fetch videos:", err);
        setVideosError("Unable to load video previews");
        setVideosFetched(true);
      })
      .finally(() => {
        setVideosLoading(false);
      });
  }, [videoSearchQuery]);

  // Retry verification steps with focused sub-query
  const retryVerify = useCallback(() => {
    if (!modelNumber || !symptoms) return;
    
    setVerifyLoading(true);
    axios.post(`${API_BASE}/diagnose/verify`, {
      model_number: modelNumber,
      issue_title: item.title,
      symptoms: symptoms,
      ai_provider: aiProvider,
    })
      .then((response) => {
        setVerifyStepsOverride(response.data.verify_steps || []);
        if (response.data.safety_warnings?.length) {
          setSafetyWarningsOverride(response.data.safety_warnings);
        }
      })
      .catch((err) => {
        console.error("Failed to regenerate verification steps:", err);
      })
      .finally(() => {
        setVerifyLoading(false);
      });
  }, [modelNumber, symptoms, item.title]);

  // Retry repair steps with focused sub-query
  const retryRepair = useCallback(() => {
    if (!modelNumber || !symptoms) return;
    
    setRepairLoading(true);
    axios.post(`${API_BASE}/diagnose/repair`, {
      model_number: modelNumber,
      issue_title: item.title,
      symptoms: symptoms,
      ai_provider: aiProvider,
    })
      .then((response) => {
        setRepairStepsOverride(response.data.repair_steps || []);
        if (response.data.safety_warnings?.length) {
          setSafetyWarningsOverride(response.data.safety_warnings);
        }
      })
      .catch((err) => {
        console.error("Failed to regenerate repair steps:", err);
      })
      .finally(() => {
        setRepairLoading(false);
      });
  }, [modelNumber, symptoms, item.title]);

  // Filter out garbage parts entries (DIAGRAM, APPROVED, OPTIONAL, etc.)
  const filterValidParts = useCallback((parts: string[]): string[] => {
    return parts.filter((part) => {
      const lower = part.toLowerCase().trim();
      // Reject entries that are clearly not part numbers
      if (lower.startsWith("diagram")) return false;
      if (lower.startsWith("approved")) return false;
      if (lower.startsWith("optional")) return false;
      if (lower.startsWith("check parts")) return false;
      if (lower.startsWith("check the parts")) return false;
      if (lower.includes("no replacement parts")) return false;
      if (lower.includes("no parts typically")) return false;
      if (lower.includes("not typically required")) return false;
      // Must contain a 7+ digit/char alphanumeric code to be valid
      return /\b[A-Z0-9]{7,}\b/i.test(part);
    });
  }, []);

  // Check if parts indicate "no parts required"
  const checkNoPartsRequired = useCallback((parts: string[]): boolean => {
    if (!parts || parts.length === 0) return false;
    const combined = parts.join(" ").toLowerCase();
    return (
      combined.includes("no replacement parts") ||
      combined.includes("no parts typically") ||
      combined.includes("not typically required") ||
      combined.includes("cleaning only") ||
      combined.includes("adjustment only")
    );
  }, []);

  // Retry parts with sub-query then V&V lookup
  const retryPartsWithSubQuery = useCallback(() => {
    if (!modelNumber || !symptoms) return;
    
    setPartsSubQueryLoading(true);
    setNoPartsRequired(false);
    setNoPartsMessage(null);
    
    axios.post(`${API_BASE}/diagnose/parts`, {
      model_number: modelNumber,
      issue_title: item.title,
      symptoms: symptoms,
      ai_provider: aiProvider,
    })
      .then((response) => {
        const { parts, no_parts_required, message } = response.data;
        
        if (no_parts_required) {
          setNoPartsRequired(true);
          setNoPartsMessage(message || "This repair typically doesn't require replacement parts.");
          setPartsOverride([]);
        } else if (parts && parts.length > 0) {
          setPartsOverride(parts);
          // Trigger V&V retry with new parts via the parent callback
          if (onRetryParts) {
            onRetryParts();
          }
        } else {
          setPartsOverride([]);
        }
      })
      .catch((err) => {
        console.error("Failed to regenerate parts list:", err);
      })
      .finally(() => {
        setPartsSubQueryLoading(false);
      });
  }, [modelNumber, symptoms, item.title, onRetryParts]);

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
              <div className="section-header-row">
                <h4>Verification Steps</h4>
                {modelNumber && symptoms && !verifyLoading && (
                  <button type="button" onClick={retryVerify} className="btn-retry btn-retry-small">
                    🔄 Regenerate
                  </button>
                )}
              </div>
              
              {verifyLoading ? (
                <div className="section-loading">
                  <span className="spinner-small" />
                  <span>Generating verification steps...</span>
                </div>
              ) : (verifyStepsOverride || details?.verify_steps)?.length ? (
                <RepairStepList steps={verifyStepsOverride || details?.verify_steps || []} type="verify" />
              ) : (
                <div className="section-empty-state">
                  <p className="muted">No specific verification steps provided.</p>
                  {modelNumber && symptoms && (
                    <button type="button" onClick={retryVerify} className="btn-retry">
                      🔄 Generate Verification Steps
                    </button>
                  )}
                </div>
              )}

              {(safetyWarningsOverride || details?.safety_warnings)?.length ? (
                <div className="warning-box">
                  <h5>⚠️ Safety Warnings</h5>
                  <ul className="safety-list">
                    {(safetyWarningsOverride || details?.safety_warnings || []).map((warning) => (
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

              {/* Show loading state when fetching parts */}
              {(partsLoading || partsSubQueryLoading) ? (
                <div className="section-loading">
                  <span className="spinner-small" />
                  <span>{partsSubQueryLoading ? "Finding part numbers..." : "Loading parts diagrams..."}</span>
                </div>
              ) : hasMatches ? (
                /* Show linked parts and diagram cards when V&V matches exist */
                <div className="parts-diagrams-row">
                  <LinkedPartsCard matchedParts={matchedParts} />
                  <DiagramThumbnailCard diagrams={matchedDiagrams} />
                </div>
              ) : noPartsRequired ? (
                /* Clean "no parts required" state */
                <div className="parts-no-required-card">
                  <div className="parts-no-required-icon">✅</div>
                  <div className="parts-no-required-content">
                    <h5>No Parts Typically Required</h5>
                    <p>{noPartsMessage || "This repair usually doesn't need replacement parts."}</p>
                  </div>
                </div>
              ) : partsOverride && partsOverride.length > 0 ? (
                /* Show sub-query parts in styled cards */
                <div className="parts-subquery-list">
                  {partsOverride.map((part, idx) => (
                    <div key={`${part.part_number}-${idx}`} className="parts-subquery-item">
                      <span className="parts-subquery-number">{part.part_number}</span>
                      <span className="parts-subquery-desc">{part.description}</span>
                    </div>
                  ))}
                </div>
              ) : (() => {
                /* Filter and show valid parts from original diagnosis */
                const filteredParts = filterValidParts(details?.parts || []);
                const isNoPartsNeeded = checkNoPartsRequired(details?.parts || []);
                
                if (isNoPartsNeeded) {
                  return (
                    <div className="parts-no-required-card">
                      <div className="parts-no-required-icon">✅</div>
                      <div className="parts-no-required-content">
                        <h5>No Parts Typically Required</h5>
                        <p>This repair usually doesn't need replacement parts.</p>
                      </div>
                    </div>
                  );
                }

                if (filteredParts.length > 0) {
                  return (
                    <div className="parts-text-fallback">
                      <ul className="parts-text-list">
                        {filteredParts.map((part, idx) => {
                          const formatted = formatPartLine(part);
                          const partNumMatch = formatted.match(/^([A-Z0-9]{7,})\s*[-—]/i);
                          const partNum = partNumMatch ? partNumMatch[1] : null;
                          const description = partNum
                            ? formatted.replace(/^[A-Z0-9]{7,}\s*[-—]\s*/i, '')
                            : formatted;

                          return (
                            <li key={`${part}-${idx}`} className="parts-text-item">
                              {partNum && (
                                <span className="parts-text-number">{partNum}</span>
                              )}
                              <span className="parts-text-desc">{sanitizeRichText(description)}</span>
                            </li>
                          );
                        })}
                      </ul>
                      <div className="parts-fallback-footer">
                        <p className="parts-text-note muted">
                          💡 Diagram data temporarily unavailable.
                        </p>
                        {modelNumber && symptoms && (
                          <button type="button" onClick={retryPartsWithSubQuery} className="btn-retry">
                            🔄 Retry Parts Lookup
                          </button>
                        )}
                      </div>
                    </div>
                  );
                }

                return (
                  <div className="parts-empty-state">
                    <p className="muted">No specific part numbers found.</p>
                    {modelNumber && symptoms && (
                      <button type="button" onClick={retryPartsWithSubQuery} className="btn-retry">
                        🔄 Find Parts
                      </button>
                    )}
                  </div>
                );
              })()}
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
                onRetry={retryVideos}
              />
            </div>
          )}

          {activeSection === "repair" && (
            <div className="prob-section">
              <div className="section-header-row">
                <h4>Repair Playbook</h4>
                {modelNumber && symptoms && !repairLoading && (
                  <button type="button" onClick={retryRepair} className="btn-retry btn-retry-small">
                    🔄 Regenerate
                  </button>
                )}
              </div>
              
              {repairLoading ? (
                <div className="section-loading">
                  <span className="spinner-small" />
                  <span>Generating repair steps...</span>
                </div>
              ) : (repairStepsOverride || details?.repair_steps)?.length ? (
                <RepairStepList steps={repairStepsOverride || details?.repair_steps || []} type="repair" />
              ) : (
                <div className="section-empty-state">
                  <p className="muted">No detailed repair steps were provided for this issue.</p>
                  {modelNumber && symptoms && (
                    <button type="button" onClick={retryRepair} className="btn-retry">
                      🔄 Generate Repair Steps
                    </button>
                  )}
                </div>
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

