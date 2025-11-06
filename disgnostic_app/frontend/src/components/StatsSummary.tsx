import { ProbabilityItem, WebResult } from "../types";

interface StatsSummaryProps {
  probabilities: ProbabilityItem[];
  webResults: WebResult[];
}

export const StatsSummary = ({ probabilities, webResults }: StatsSummaryProps) => {
  if (!probabilities.length) return null;

  const issuesCount = probabilities.length;
  const topProbability = probabilities[0]?.percent ?? 0;
  const sourceCount = webResults.length;
  const videoCount = probabilities.reduce(
    (total, item) => total + (item.details?.video_searches?.length ?? 0),
    0,
  );
  const totalSources = sourceCount + videoCount;

  return (
    <section className="card">
      <div className="card-header">
        <h2>Diagnosis Snapshot</h2>
        <p className="card-subtitle">
          A quick glance at the analysis results and supporting research gathered for this job.
        </p>
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
          <span className="stat-value">{totalSources}</span>
          <span className="stat-label">Research Sources</span>
        </div>
      </div>
    </section>
  );
};

export default StatsSummary;

