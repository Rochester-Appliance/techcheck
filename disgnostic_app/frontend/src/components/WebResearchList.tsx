import { useState } from "react";

import { SourceLink, WebResult } from "../types";

interface WebResearchListProps {
  results: WebResult[];
  inlineSources: SourceLink[];
}

export const WebResearchList = ({ results, inlineSources }: WebResearchListProps) => {
  const [expanded, setExpanded] = useState(false);
  const totalCount = results.length + inlineSources.length;

  if (!totalCount) return null;

  return (
    <section className="card source-card">
      <details
        className="disclosure"
        open={expanded}
        onToggle={(event) => setExpanded(event.currentTarget.open)}
      >
        <summary>Source Links ({totalCount})</summary>
        <div className="source-grid">
          {inlineSources.length > 0 && (
            <div>
              <h4>Inline Citations</h4>
              <ul className="source-list">
                {inlineSources.map((source) => (
                  <li key={source.url}>
                    <strong>{source.label || source.url}</strong>
                    <div className="source-link-row">
                      <a href={source.url} target="_blank" rel="noreferrer">
                        {source.url}
                      </a>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {results.length > 0 && (
            <div>
              <h4>Web Research</h4>
              <ul className="source-list">
                {results.map((result, index) => (
                  <li key={`${result.url}-${index}`}>
                    <a href={result.url} target="_blank" rel="noreferrer">
                      {result.title || result.url}
                    </a>
                    {result.snippet && <p className="muted">{result.snippet}</p>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </details>
    </section>
  );
};

export default WebResearchList;

