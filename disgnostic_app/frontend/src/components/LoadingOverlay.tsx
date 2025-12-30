import { clsx } from "clsx";
import { useEffect, useState } from "react";

interface LoadingOverlayProps {
  stage: string;
  visible: boolean;
}

const stages = [
  { icon: "☁️", label: "Searching repair databases...", key: "web" },
  { icon: "🧠", label: "AI analyzing symptoms...", key: "brain" },
  { icon: "🔧", label: "Gathering repair insights...", key: "tools" },
  { icon: "📋", label: "Compiling parts & steps...", key: "docs" },
];

export const LoadingOverlay = ({ stage, visible }: LoadingOverlayProps) => {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!visible) {
      setActiveIndex(0);
      return;
    }

    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % stages.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [visible]);

  return (
    <div className={clsx("loading-overlay", { visible })} role="status" aria-live="assertive">
      <div className="loading-card loading-card-animated">
        {/* Animated Flow Diagram */}
        <div className="loading-flow">
          {/* Top: Cloud/Internet */}
          <div className="loading-flow-row">
            <div className={clsx("loading-node", { active: activeIndex === 0 })}>
              <span className="loading-node-icon">☁️</span>
            </div>
          </div>

          {/* Connector: Top to Middle */}
          <div className="loading-connector vertical">
            <div className={clsx("loading-pulse", { active: activeIndex === 0 })} />
          </div>

          {/* Middle Row: Brain - Center - Tools */}
          <div className="loading-flow-row loading-flow-middle">
            <div className={clsx("loading-node", { active: activeIndex === 1 })}>
              <span className="loading-node-icon">🧠</span>
            </div>
            
            <div className="loading-connector horizontal">
              <div className={clsx("loading-pulse", { active: activeIndex === 1 })} />
            </div>
            
            <div className="loading-node-center">
              <div className="loading-center-ring" />
              <span className="loading-center-icon">⚡</span>
            </div>
            
            <div className="loading-connector horizontal">
              <div className={clsx("loading-pulse reverse", { active: activeIndex === 2 })} />
            </div>
            
            <div className={clsx("loading-node", { active: activeIndex === 2 })}>
              <span className="loading-node-icon">🔧</span>
            </div>
          </div>

          {/* Connector: Middle to Bottom */}
          <div className="loading-connector vertical">
            <div className={clsx("loading-pulse", { active: activeIndex === 2 || activeIndex === 3 })} />
          </div>

          {/* Bottom: Document/Results */}
          <div className="loading-flow-row">
            <div className={clsx("loading-node", { active: activeIndex === 3 })}>
              <span className="loading-node-icon">📋</span>
            </div>
          </div>
        </div>

        {/* Stage Text */}
        <p className="loading-stage-text">{stages[activeIndex].label}</p>
        
        {/* Progress dots */}
        <div className="loading-progress-dots">
          {stages.map((s, i) => (
            <span 
              key={s.key} 
              className={clsx("loading-dot", { active: i === activeIndex, completed: i < activeIndex })}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default LoadingOverlay;
