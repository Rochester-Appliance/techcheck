import { useState } from "react";

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
  if (qty === null || qty === undefined) return "Check availability";
  if (qty > 0) return `In stock (${qty})`;
  if (qty === 0) return "Out of stock";
  return "Check availability";
};

const DiagramPreview = ({ url, sectionName }: { url?: string | null; sectionName: string }) => {
  const [errored, setErrored] = useState(false);

  if (!url || errored) {
    return <div className="diagram-placeholder">Preview unavailable</div>;
  }

  return (
    <img
      src={url}
      alt={`${sectionName} preview`}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setErrored(true)}
    />
  );
};

const DiagramLargeImage = ({ url, sectionName }: { url?: string | null; sectionName: string }) => {
  const [errored, setErrored] = useState(false);

  if (!url) {
    return null;
  }

  if (errored) {
    return <div className="diagram-placeholder">Large diagram unavailable</div>;
  }

  return (
    <img
      src={url}
      alt={`${sectionName} exploded diagram`}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setErrored(true)}
    />
  );
};

const DiagramGallery = ({ status, bundle, error, requestedModel, onRetry }: DiagramGalleryProps) => {
  if (status === "idle") return null;

  const model = bundle?.model;
  const diagrams = bundle?.diagrams ?? [];

  return (
    <section className="card diagram-card" aria-live="polite">
      <div className="diagram-header">
        <div>
          <h3>Exploded Diagrams &amp; Parts</h3>
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
        {status === "error" && (
          <button className="btn btn-secondary diagram-retry" onClick={onRetry} type="button">
            Retry
          </button>
        )}
      </div>

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
        </div>
      )}

      {status === "ready" && diagrams.length === 0 && (
        <div className="diagram-status">
          <p>No diagrams were returned for this model.</p>
        </div>
      )}

      {status === "ready" && diagrams.length > 0 && (
        <div className="diagram-grid" role="list" aria-label="Exploded diagrams">
          {diagrams.map((diagram) => (
            <article className="diagram-item" key={diagram.diagram_id} role="listitem">
              <div className="diagram-preview">
                <DiagramPreview url={diagram.small_image_url} sectionName={diagram.section_name} />
              </div>
              <div className="diagram-meta">
                <h4>{diagram.section_name}</h4>
                {diagram.large_image_url ? (
                  <a href={diagram.large_image_url} target="_blank" rel="noreferrer">
                    Open large diagram ↗
                  </a>
                ) : (
                  <span className="muted">Large diagram unavailable</span>
                )}
              </div>
              <details className="diagram-details">
                <summary>
                  Parts list ({diagram.parts.length})
                </summary>
                <div className="diagram-detail-body">
                  {diagram.large_image_url ? (
                    <div className="diagram-large">
                      <DiagramLargeImage
                        url={diagram.large_image_url}
                        sectionName={diagram.section_name}
                      />
                    </div>
                  ) : null}
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
                </div>
              </details>
            </article>
          ))}
        </div>
      )}
    </section>
  );
};

export default DiagramGallery;





