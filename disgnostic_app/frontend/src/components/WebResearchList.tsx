import { WebResult } from "../types";

interface WebResearchListProps {
  results: WebResult[];
}

export const WebResearchList = ({ results }: WebResearchListProps) => {
  if (!results.length) return null;

  return (
    <section className="card">
      <div className="card-header">
        <h2>Research Sources</h2>
        <p className="card-subtitle">
          Links and reference material gathered while cross-checking the repair guidance.
        </p>
      </div>
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
    </section>
  );
};

export default WebResearchList;

