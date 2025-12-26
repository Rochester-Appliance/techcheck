import { useState } from "react";

import { SourceLink, WebResult } from "../types";

interface WebResearchListProps {
  results: WebResult[];
  inlineSources: SourceLink[];
}

/** Extract domain name from URL for cleaner display */
const getDomainFromUrl = (url: string): string => {
  try {
    const hostname = new URL(url).hostname;
    // Remove www. prefix if present
    return hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
};

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
              <ul className="source-list source-list-clean">
                {inlineSources.map((source) => (
                  <li key={source.url}>
                    <a href={source.url} target="_blank" rel="noreferrer" className="source-domain-link">
                      {getDomainFromUrl(source.url)}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {results.length > 0 && (
            <div>
              <h4>Web Research</h4>
              <ul className="source-list source-list-clean">
                {results.map((result, index) => (
                  <li key={`${result.url}-${index}`}>
                    <a href={result.url} target="_blank" rel="noreferrer" className="source-domain-link">
                      {result.title || getDomainFromUrl(result.url)}
                    </a>
                    {result.snippet && <p className="muted source-snippet">{result.snippet}</p>}
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

