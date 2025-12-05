import type { VNVDiagramSummary } from "../types";

interface DiagramModalProps {
  diagram: VNVDiagramSummary | null;
  onClose: () => void;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/** Build a proxied image URL to bypass CORS restrictions on V&V images. */
const proxyImageUrl = (url: string | null | undefined): string | null => {
  if (!url) return null;
  return `${API_BASE}/proxy/image?url=${encodeURIComponent(url)}`;
};

const DiagramModal = ({ diagram, onClose }: DiagramModalProps) => {
  if (!diagram) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="diagram-modal"
      role="dialog"
      aria-modal="true"
      onClick={handleBackdropClick}
    >
      <div className="diagram-modal-content">
        <button
          className="btn btn-secondary diagram-modal-close"
          type="button"
          onClick={onClose}
        >
          Close
        </button>
        <h4>{diagram.section_name}</h4>
        {diagram.large_image_url ? (
          <img
            src={proxyImageUrl(diagram.large_image_url) ?? ""}
            alt={`${diagram.section_name} diagram`}
            loading="lazy"
            decoding="async"
          />
        ) : (
          <p className="muted">Large diagram unavailable for this section.</p>
        )}
      </div>
    </div>
  );
};

export default DiagramModal;

