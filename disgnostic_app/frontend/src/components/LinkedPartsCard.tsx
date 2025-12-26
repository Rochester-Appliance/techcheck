import { useState } from "react";
import type { MatchedPart } from "../utils";
import { addToCart } from "../cartStore";

interface LinkedPartsCardProps {
  matchedParts: MatchedPart[];
}

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
  if (qty === 0) return "Factory Order";
  return null;
};

const getDeliveryEstimate = (qty?: number | null) => {
  if (qty && qty > 0) return "Est. 1-2 business days";
  return "Est. 3-4 weeks";
};

const LinkedPartsCard = ({ matchedParts }: LinkedPartsCardProps) => {
  const [addedParts, setAddedParts] = useState<Set<string>>(new Set());

  if (!matchedParts.length) return null;

  const handleAddToCart = (match: MatchedPart) => {
    const { vnvPart, partNumber } = match;
    const price = vnvPart.price ?? vnvPart.list_price ?? 0;

    addToCart({
      partNumber: vnvPart.part_number || partNumber,
      description: vnvPart.description || "Appliance Part",
      price,
      imageUrl: vnvPart.image_urls?.[0],
    });

    // Show "Added!" feedback
    setAddedParts((prev) => new Set(prev).add(partNumber));
    setTimeout(() => {
      setAddedParts((prev) => {
        const next = new Set(prev);
        next.delete(partNumber);
        return next;
      });
    }, 1500);
  };

  return (
    <div className="linked-parts-card">
      <h5 className="linked-parts-header">
        <span className="linked-parts-icon">🔩</span> Linked Parts
      </h5>
      <ul className="linked-parts-list">
        {matchedParts.map((match) => {
          const { vnvPart } = match;
          const priceStr = formatPrice(vnvPart.price, vnvPart.list_price);
          const availStr = formatAvailability(vnvPart.qty_available);
          const isAdded = addedParts.has(match.partNumber);
          const isOutOfStock = vnvPart.qty_available === 0;

          const deliveryEstimate = getDeliveryEstimate(vnvPart.qty_available);

          // Get diagram reference info
          const itemNum = vnvPart.item_number;
          const diagramName = match.diagram?.section_name;
          // Extract just the name part (e.g., "04 - Shelves" -> "Shelves")
          const shortDiagramName = diagramName?.replace(/^\d+\s*-\s*/, "") || diagramName;

          return (
            <li key={match.partNumber} className="linked-part-item">
              <div className="linked-part-number">{vnvPart.part_number || match.partNumber}</div>
              {vnvPart.description && (
                <div className="linked-part-description">{vnvPart.description}</div>
              )}
              <div className="linked-part-meta">
                {priceStr && <span className="linked-part-price">{priceStr}</span>}
                {priceStr && availStr && <span className="linked-part-sep">•</span>}
                {availStr && <span className="linked-part-avail">{availStr}</span>}
              </div>
              {itemNum && shortDiagramName && (
                <div className="linked-part-diagram-ref">
                  🔍 Find as <strong>#{itemNum}</strong> on "{shortDiagramName}" diagram
                </div>
              )}
              <div className="linked-part-delivery">
                <span className={`delivery-badge ${isOutOfStock ? "delayed" : "fast"}`}>
                  🚚 {deliveryEstimate}
                </span>
              </div>
              <button
                type="button"
                className={`linked-part-add-btn ${isAdded ? "added" : ""}`}
                onClick={() => handleAddToCart(match)}
              >
                {isAdded ? "✓ Added!" : "Add to Cart"}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default LinkedPartsCard;

