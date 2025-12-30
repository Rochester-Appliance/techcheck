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

  return (
    <>
      <div className="diagram-thumbnail-card">
        <h5 className="diagram-thumbnail-header">
          <span className="diagram-thumbnail-icon">📐</span> Related Diagram{diagrams.length > 1 ? "s" : ""}
        </h5>
        
        {/* Show all diagrams as thumbnail cards */}
        <div className="diagram-thumbnail-grid">
          {diagrams.map((diagram) => {
            const thumbnailUrl = proxyImageUrl(diagram.small_image_url || diagram.large_image_url);
            
            return (
              <button
                key={diagram.diagram_id}
                type="button"
                className="diagram-thumbnail-body-btn"
                onClick={() => setActiveDiagram(diagram)}
                aria-label={`View ${diagram.section_name} diagram`}
              >
                <div className="diagram-thumbnail-body">
                  {thumbnailUrl ? (
                    <div className="diagram-thumbnail-img-wrapper">
                      <img
                        src={thumbnailUrl}
                        alt={`${diagram.section_name} thumbnail`}
                        className="diagram-thumbnail-img"
                        loading="lazy"
                        decoding="async"
                      />
                    </div>
                  ) : (
                    <div className="diagram-thumbnail-placeholder">
                      <span>No preview</span>
                    </div>
                  )}
                  <div className="diagram-thumbnail-info">
                    <span className="diagram-thumbnail-name">{diagram.section_name}</span>
                    <span className="diagram-thumbnail-hint">Tap to view</span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Modal for large diagram view */}
      <DiagramModal diagram={activeDiagram} onClose={() => setActiveDiagram(null)} />
    </>
  );
};

export default DiagramThumbnailCard;

