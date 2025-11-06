import { clsx } from "clsx";

interface LoadingOverlayProps {
  stage: string;
  visible: boolean;
}

export const LoadingOverlay = ({ stage, visible }: LoadingOverlayProps) => (
  <div className={clsx("loading-overlay", { visible })} role="status" aria-live="assertive">
    <div className="loading-card">
      <div className="spinner" aria-hidden="true" />
      <p>{stage}</p>
    </div>
  </div>
);

export default LoadingOverlay;

