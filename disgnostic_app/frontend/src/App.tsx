import { useCallback, useMemo, useState } from "react";

import { api } from "./api";
import DiagnosisForm from "./components/DiagnosisForm";
import DiagramGallery from "./components/DiagramGallery";
import LoadingOverlay from "./components/LoadingOverlay";
import ProbabilityCard from "./components/ProbabilityCard";
import StatsSummary from "./components/StatsSummary";
import WebResearchList from "./components/WebResearchList";
import {
  DiagnosisFormValues,
  DiagnosisRequest,
  DiagnosisResponse,
  DiagramBundleResponse,
  OutcomeStatus,
} from "./types";
import { createReportContent, downloadReport, sleep } from "./utils";

import "./styles.css";

const emptyForm: DiagnosisFormValues = {
  techName: "",
  jobNumber: "",
  modelNumber: "",
  problemDescription: "",
};

const trimSymptom = (value: string, length = 160) =>
  value.length > length ? `${value.slice(0, length)}…` : value;

type DiagramLookupState = {
  status: "idle" | "loading" | "error" | "ready";
  data: DiagramBundleResponse | null;
  error: string | null;
  requestedModel: string | null;
};

const initialDiagramState: DiagramLookupState = {
  status: "idle",
  data: null,
  error: null,
  requestedModel: null,
};

function App() {
  const [formValues, setFormValues] = useState<DiagnosisFormValues>(emptyForm);
  const [diagnosis, setDiagnosis] = useState<DiagnosisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState("Analyzing symptoms...");
  const [error, setError] = useState<string | null>(null);
  const [outcomes, setOutcomes] = useState<Record<string, OutcomeStatus>>({});
  const [diagramState, setDiagramState] = useState<DiagramLookupState>({
    ...initialDiagramState,
  });

  const hasResults = Boolean(diagnosis);

  const jobSummary = useMemo(() => {
    if (!diagnosis) return null;
    return {
      tech: diagnosis.tech_name || formValues.techName,
      job: diagnosis.job_number || formValues.jobNumber,
      model: diagnosis.model_number,
      symptoms: trimSymptom(formValues.problemDescription),
    };
  }, [diagnosis, formValues]);

  const handleFormChange = (values: DiagnosisFormValues) => {
    setFormValues(values);
  };

  const resetDiagramState = () => {
    setDiagramState({ ...initialDiagramState });
  };

  const loadDiagramData = useCallback(async (modelNumber: string) => {
    const trimmed = modelNumber.trim();
    if (!trimmed) {
      setDiagramState({ ...initialDiagramState });
      return;
    }

    setDiagramState({
      status: "loading",
      data: null,
      error: null,
      requestedModel: trimmed,
    });

    try {
      const bundle = await api.fetchDiagramBundle(trimmed);
      setDiagramState({
        status: "ready",
        data: bundle,
        error: null,
        requestedModel: trimmed,
      });
    } catch (err) {
      setDiagramState({
        status: "error",
        data: null,
        error: err instanceof Error ? err.message : "Failed to load diagrams",
        requestedModel: trimmed,
      });
    }
  }, []);

  const handleOutcomeChange = (title: string, status: OutcomeStatus) => {
    setOutcomes((prev) => ({ ...prev, [title]: status }));
  };

  const handleSubmit = async (values: DiagnosisFormValues) => {
    setFormValues(values);
    setError(null);
    setLoading(true);
    setLoadingStage("Analyzing symptoms & failure modes...");
    resetDiagramState();

    const trimmedTech = values.techName.trim();
    const trimmedJob = values.jobNumber.trim();
    const trimmedModel = values.modelNumber.trim();
    const trimmedProblem = values.problemDescription.trim();

    void loadDiagramData(trimmedModel);

    const payload: DiagnosisRequest = {
      tech_name: trimmedTech,
      job_number: trimmedJob,
      model_number: trimmedModel,
      problem_description: trimmedProblem,
    };

    try {
      await sleep(350);
      setLoadingStage("Gathering repair insights & part data...");
      const response = await api.diagnose(payload);
      await sleep(250);
      setLoadingStage("Polishing recommendations...");
      await sleep(200);
      setDiagnosis(response);
      setOutcomes({});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
      setDiagnosis(null);
      resetDiagramState();
    } finally {
      setLoading(false);
      setLoadingStage("Analyzing symptoms...");
    }
  };

  const handleReset = () => {
    setDiagnosis(null);
    setOutcomes({});
    setFormValues(emptyForm);
    setError(null);
    resetDiagramState();
  };

  const handleDownloadReport = () => {
    if (!diagnosis) return;
    const content = createReportContent(formValues, diagnosis);
    const filename = `diagnostic_${diagnosis.model_number}_${Date.now()}.txt`;
    downloadReport(content, filename);
  };

  return (
    <div className="app">
      <LoadingOverlay stage={loadingStage} visible={loading} />

      <header className="hero">
        <div className="hero-content">
          <span className="hero-tag">TechCheck Pilot</span>
          <h1>Pro Diagnostics for Appliance Repair Teams</h1>
          <p>
            Run deep appliance diagnostics with probability scoring, actionable part numbers, and
            field-ready repair playbooks — optimized for desktop and mobile.
          </p>
        </div>
      </header>

      <main className="page">
        {error && (
          <div className="alert alert-error" role="alert">
            <strong>We hit a snag:</strong> {error}
          </div>
        )}

        <DiagnosisForm
          values={formValues}
          onChange={handleFormChange}
          onSubmit={handleSubmit}
          loading={loading}
        />

      <DiagramGallery
        status={diagramState.status}
        bundle={diagramState.data}
        error={diagramState.error}
        requestedModel={diagramState.requestedModel}
        onRetry={() => {
          const model = diagnosis?.model_number || formValues.modelNumber.trim();
          if (model) {
            void loadDiagramData(model);
          }
        }}
      />

        {hasResults && diagnosis && jobSummary && (
          <>
            <section className="card highlight">
              <div className="highlight-header">
                <h2>Diagnostic Results</h2>
                <p>
                  Tech <strong>{jobSummary.tech}</strong> • Job <strong>{jobSummary.job}</strong>
                </p>
              </div>
              <div className="highlight-body">
                <p>
                  <span className="pill">Model</span> {jobSummary.model}
                </p>
                <p>
                  <span className="pill">Symptoms</span> {jobSummary.symptoms}
                </p>
              </div>
            </section>

            <StatsSummary
              probabilities={diagnosis.probabilities}
              webResults={diagnosis.web_results}
            />

            <section className="probability-stack">
              {diagnosis.probabilities.map((prob, index) => (
                <ProbabilityCard
                  key={prob.title}
                  item={prob}
                  index={index}
                  outcome={outcomes[prob.title] ?? null}
                  onOutcomeChange={handleOutcomeChange}
                />
              ))}
            </section>

            {diagnosis.probabilities.length > 3 && (
              <section className="card warning-card">
                <h3>Additional Technical Possibilities</h3>
                <p>
                  There may be less common, higher technical issues beyond the top results shown
                  above. Escalate to a senior technician if the leading recommendations do not
                  resolve the problem.
                </p>
              </section>
            )}

            <WebResearchList results={diagnosis.web_results} />

            <section className="card">
              <details className="disclosure" open>
                <summary>View Full Diagnostic Narrative</summary>
                <pre className="analysis-block">{diagnosis.full_analysis}</pre>
              </details>
            </section>

            <div className="action-row">
              <button className="btn btn-secondary" onClick={handleReset} type="button">
                Start New Diagnosis
              </button>
              <button className="btn btn-primary" onClick={handleDownloadReport} type="button">
                Download Report
              </button>
              <a className="btn btn-contact" href="tel:5858806144">
                Call Dean • 585-880-6144
              </a>
            </div>
          </>
        )}
      </main>

      <footer className="footer">
        <p>
          <strong>TechCheckPilot</strong> — Diagnostic insights are AI assisted. Confirm complex
          repairs with a certified technician.
        </p>
      </footer>
    </div>
  );
}

export default App;

