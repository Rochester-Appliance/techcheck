import { useState } from "react";

import type { VNVDiagramSummary } from "../types";
import DiagramModal from "./DiagramModal";

interface DiagramThumbnailCardProps {
  diagrams: VNVDiagramSummary[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/** Build a proxied image URL to bypass CORS restrictions on V&V images. */
const proxyImageUrl = (url: string | null | undefined): string | null => {
  if (!url) return null;
  return `${API_BASE}/proxy/image?url=${encodeURIComponent(url)}`;
};

const DiagramThumbnailCard = ({ diagrams }: DiagramThumbnailCardProps) => {
  const [activeDiagram, setActiveDiagram] = useState<VNVDiagramSummary | null>(null);

  if (!diagrams.length) return null;

  // Show the first diagram as the primary thumbnail
  const primaryDiagram = diagrams[0];
  const thumbnailUrl = proxyImageUrl(primaryDiagram.small_image_url || primaryDiagram.large_image_url);

  return (
    <>
      <div className="diagram-thumbnail-card">
        <h5 className="diagram-thumbnail-header">
          <span className="diagram-thumbnail-icon">📐</span> Related Diagram
        </h5>
        <div className="diagram-thumbnail-body">
          {thumbnailUrl ? (
            <button
              type="button"
              className="diagram-thumbnail-btn"
              onClick={() => setActiveDiagram(primaryDiagram)}
              aria-label={`View ${primaryDiagram.section_name} diagram`}
            >
              <img
                src={thumbnailUrl}
                alt={`${primaryDiagram.section_name} thumbnail`}
                className="diagram-thumbnail-img"
                loading="lazy"
                decoding="async"
              />
            </button>
          ) : (
            <div className="diagram-thumbnail-placeholder">
              <span>No preview</span>
            </div>
          )}
          <div className="diagram-thumbnail-info">
            <span className="diagram-thumbnail-name">{primaryDiagram.section_name}</span>
            <button
              type="button"
              className="btn btn-link diagram-thumbnail-expand"
              onClick={() => setActiveDiagram(primaryDiagram)}
            >
              View Full Diagram
            </button>
          </div>
        </div>

        {/* Show additional diagrams if more than one */}
        {diagrams.length > 1 && (
          <div className="diagram-thumbnail-more">
            <span className="muted">+{diagrams.length - 1} more diagram{diagrams.length > 2 ? "s" : ""}</span>
            <div className="diagram-thumbnail-list">
              {diagrams.slice(1).map((diagram) => (
                <button
                  key={diagram.diagram_id}
                  type="button"
                  className="btn btn-link diagram-thumbnail-link"
                  onClick={() => setActiveDiagram(diagram)}
                >
                  {diagram.section_name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Modal for large diagram view */}
      <DiagramModal diagram={activeDiagram} onClose={() => setActiveDiagram(null)} />
    </>
  );
};

export default DiagramThumbnailCard;

