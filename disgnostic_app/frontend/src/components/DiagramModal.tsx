import { useState } from "react";
import type { VNVDiagramSummary, VNVPartSummary } from "../types";
import { addToCart } from "../cartStore";

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

const formatPrice = (price?: number | null, listPrice?: number | null) => {
  const value = price ?? listPrice;
  if (value === null || value === undefined) return null;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
};

const formatAvailability = (qty?: number | null) => {
  if (qty === null || qty === undefined) return null;
  if (qty > 0) return `In stock (${qty})`;
  if (qty === 0) return "Out of stock";
  return null;
};

const DiagramModal = ({ diagram, onClose }: DiagramModalProps) => {
  const [partsExpanded, setPartsExpanded] = useState(false);
  const [addedParts, setAddedParts] = useState<Set<string>>(new Set());

  if (!diagram) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleAddToCart = (part: VNVPartSummary) => {
    const price = part.price ?? part.list_price ?? 0;

    addToCart({
      partNumber: part.part_number,
      description: part.description || "Appliance Part",
      price,
      imageUrl: part.image_urls?.[0],
    });

    // Show "Added!" feedback
    setAddedParts((prev) => new Set(prev).add(part.part_number));
    setTimeout(() => {
      setAddedParts((prev) => {
        const next = new Set(prev);
        next.delete(part.part_number);
        return next;
      });
    }, 1500);
  };

  const parts = diagram.parts || [];
  const hasPartss = parts.length > 0;

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

        {/* Collapsible Parts Drawer */}
        {hasPartss && (
          <div className="diagram-parts-drawer">
            <button
              type="button"
              className="diagram-parts-toggle"
              onClick={() => setPartsExpanded(!partsExpanded)}
            >
              <span className={`drawer-arrow ${partsExpanded ? "expanded" : ""}`}>▶</span>
              <span>View Parts ({parts.length})</span>
            </button>

            {partsExpanded && (
              <ul className="diagram-parts-list">
                {parts.map((part) => {
                  const priceStr = formatPrice(part.price, part.list_price);
                  const availStr = formatAvailability(part.qty_available);
                  const isAdded = addedParts.has(part.part_number);
                  const isOutOfStock = part.qty_available === 0;

                  return (
                    <li key={`${part.item_number}-${part.part_number}`} className="diagram-part-item">
                      <div className="diagram-part-main">
                        <span className="diagram-part-item-num">#{part.item_number}</span>
                        <div className="diagram-part-details">
                          <span className="diagram-part-number">{part.part_number}</span>
                          {part.description && (
                            <span className="diagram-part-desc">{part.description}</span>
                          )}
                        </div>
                      </div>
                      <div className="diagram-part-meta">
                        {priceStr && <span className="diagram-part-price">{priceStr}</span>}
                        {availStr && <span className="diagram-part-avail">{availStr}</span>}
                      </div>
                      <button
                        type="button"
                        className={`btn-sm diagram-part-add ${isAdded ? "added" : ""}`}
                        onClick={() => handleAddToCart(part)}
                        disabled={isOutOfStock}
                      >
                        {isAdded ? "✓ Added" : isOutOfStock ? "Unavailable" : "Add to Cart"}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DiagramModal;

