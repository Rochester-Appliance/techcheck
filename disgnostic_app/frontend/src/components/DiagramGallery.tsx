import { useMemo, useState } from "react";

import { DiagramBundleResponse } from "../types";

type DiagramGalleryStatus = "idle" | "loading" | "error" | "ready";

interface DiagramGalleryProps {
  status: DiagramGalleryStatus;
  bundle: DiagramBundleResponse | null;
  error: string | null;
  requestedModel: string | null;
  onRetry: () => void;
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const formatPrice = (value?: number | null) => {
  if (value === undefined || value === null) return "—";
  try {
    return currencyFormatter.format(value);
  } catch {
    return "—";
  }
};

const formatAvailability = (qty?: number | null) => {
  if (qty === null || qty === undefined) return "Not available";
  if (qty > 0) return `In stock (${qty})`;
  if (qty === 0) return "Out of stock";
  return "Check availability";
};

const DiagramGallery = ({ status, bundle, error, requestedModel, onRetry }: DiagramGalleryProps) => {
  const [expanded, setExpanded] = useState(false);
  const [activeDiagramId, setActiveDiagramId] = useState<number | null>(null);

  const model = bundle?.model;
  const diagrams = bundle?.diagrams ?? [];
  const activeDiagram = useMemo(
    () => diagrams.find((diagram) => diagram.diagram_id === activeDiagramId),
    [activeDiagramId, diagrams],
  );

  if (status === "idle") return null;

  return (
    <section className="card diagram-card collapsible" aria-live="polite">
      <details
        className="diagram-disclosure"
        open={expanded}
        onToggle={(event) => setExpanded(event.currentTarget.open)}
      >
        <summary>
          <div>
            <h3>Diagrams &amp; Parts</h3>
            {model ? (
              <p>
                <strong>{model.model_number}</strong>
                {model.model_description ? ` • ${model.model_description}` : ""}
                {model.manufacturer ? ` • ${model.manufacturer}` : ""}
              </p>
            ) : requestedModel ? (
              <p>
                Showing data for <strong>{requestedModel}</strong>
              </p>
            ) : null}
          </div>
          {status === "loading" && <span className="muted">Loading…</span>}
        </summary>

        <div className="diagram-body">
          {status === "loading" && (
            <div className="diagram-status">
              <div className="spinner" aria-hidden="true" />
              <p>Loading diagrams and parts…</p>
            </div>
          )}

          {status === "error" && (
            <div className="diagram-status diagram-error" role="alert">
              <p>Unable to load diagrams right now.</p>
              {error ? <p className="muted">{error}</p> : null}
              <button className="btn btn-secondary diagram-retry" onClick={onRetry} type="button">
                Retry
              </button>
            </div>
          )}

          {status === "ready" && diagrams.length === 0 && (
            <div className="diagram-status">
              <p>No diagrams were returned for this model.</p>
            </div>
          )}

          {status === "ready" && diagrams.length > 0 && (
            <div className="diagram-list">
              {diagrams.map((diagram) => (
                <details className="diagram-row" key={diagram.diagram_id}>
                  <summary>
                    <div>
                      <strong>{diagram.section_name}</strong>
                      <span className="diagram-count">
                        {diagram.parts.length} part{diagram.parts.length === 1 ? "" : "s"}
                      </span>
                    </div>
                    {diagram.large_image_url ? (
                      <button
                        className="btn btn-link"
                        type="button"
                        onClick={() => setActiveDiagramId(diagram.diagram_id)}
                      >
                        Open large diagram
                      </button>
                    ) : (
                      <span className="muted">Large diagram unavailable</span>
                    )}
                  </summary>
                  {diagram.parts.length ? (
                    <div className="diagram-parts">
                      <table className="diagram-parts-table">
                        <thead>
                          <tr>
                            <th scope="col">Item</th>
                            <th scope="col">Part #</th>
                            <th scope="col">Description</th>
                            <th scope="col">Availability</th>
                            <th scope="col">Price</th>
                            <th scope="col" className="diagram-col-link">
                              Link
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {diagram.parts.map((part) => (
                            <tr key={`${diagram.diagram_id}-${part.part_number}-${part.item_number}`}>
                              <td data-label="Item">{part.item_number || "—"}</td>
                              <td data-label="Part #">{part.part_number || "—"}</td>
                              <td data-label="Description">{part.description || "—"}</td>
                              <td data-label="Availability">{formatAvailability(part.qty_available)}</td>
                              <td data-label="Price">{formatPrice(part.price ?? part.list_price)}</td>
                              <td data-label="Link" className="diagram-link-cell">
                                {part.url ? (
                                  <a href={part.url} target="_blank" rel="noreferrer">
                                    View ↗
                                  </a>
                                ) : (
                                  <span className="muted">—</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="muted">No parts listed for this diagram.</p>
                  )}
                </details>
              ))}
            </div>
          )}
        </div>
      </details>

      {activeDiagram && (
        <div className="diagram-modal" role="dialog" aria-modal="true">
          <div className="diagram-modal-content">
            <button
              className="btn btn-secondary diagram-modal-close"
              type="button"
              onClick={() => setActiveDiagramId(null)}
            >
              Close
            </button>
            <h4>{activeDiagram.section_name}</h4>
            {activeDiagram.large_image_url ? (
              <img
                src={activeDiagram.large_image_url}
                alt={`${activeDiagram.section_name} diagram`}
                loading="lazy"
                decoding="async"
              />
            ) : (
              <p className="muted">Large diagram unavailable for this section.</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
};

export default DiagramGallery;





