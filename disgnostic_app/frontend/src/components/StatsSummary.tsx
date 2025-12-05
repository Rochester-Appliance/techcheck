import { ProbabilityItem } from "../types";

interface StatsSummaryProps {
  probabilities: ProbabilityItem[];
  sourceCount: number;
}

export const StatsSummary = ({ probabilities, sourceCount }: StatsSummaryProps) => {
  if (!probabilities.length) return null;

  const issuesCount = probabilities.length;
  const topProbability = probabilities[0]?.percent ?? 0;

  return (
    <section className="card">
      <div className="card-header">
        <h2>Diagnosis Snapshot</h2>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{issuesCount}</span>
          <span className="stat-label">Probable Causes</span>
        </div>
        <div className="stat-card highlight-red">
          <span className="stat-value">{topProbability}%</span>
          <span className="stat-label">Top Probability</span>
        </div>
        <div className="stat-card highlight-green">
          <span className="stat-value">{sourceCount}</span>
          <span className="stat-label">Source Links</span>
        </div>
      </div>
    </section>
  );
};

export default StatsSummary;

