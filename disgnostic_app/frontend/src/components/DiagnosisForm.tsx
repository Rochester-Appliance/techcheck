import { ChangeEvent, FormEvent } from "react";

import { DiagnosisFormValues } from "../types";
import { clsx } from "clsx";

interface DiagnosisFormProps {
  values: DiagnosisFormValues;
  onChange: (values: DiagnosisFormValues) => void;
  onSubmit: (values: DiagnosisFormValues) => void;
  loading: boolean;
}

const fieldDescriptions = [
  "Provide detailed symptoms: sounds, smells, leaks, and timing.",
  "Mention error codes or display messages if shown.",
  "Share what you've already tested or replaced.",
];

export const DiagnosisForm = ({
  values,
  onChange,
  onSubmit,
  loading,
}: DiagnosisFormProps) => {
  const handleChange = (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = event.target;
    onChange({ ...values, [name]: value });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(values);
  };

  const isDisabled = loading;

  return (
    <section className="card form-card" aria-labelledby="diagnosis-form-heading">
      <div className="card-header">
        <h2 id="diagnosis-form-heading">Diagnostic Intake</h2>
      </div>

      <form onSubmit={handleSubmit} className="form-grid">
        <div className="input-group">
          <label htmlFor="techName">Tech Name *</label>
          <input
            id="techName"
            name="techName"
            autoComplete="name"
            placeholder="e.g., John Smith"
            value={values.techName}
            onChange={handleChange}
            disabled={isDisabled}
            required
          />
        </div>

        <div className="input-group">
          <label htmlFor="jobNumber">Job Name / Number *</label>
          <input
            id="jobNumber"
            name="jobNumber"
            placeholder="e.g., JOB-2024-001"
            value={values.jobNumber}
            onChange={handleChange}
            disabled={isDisabled}
            required
          />
        </div>

        <div className="input-group">
          <label htmlFor="modelNumber">Model Number *</label>
          <input
            id="modelNumber"
            name="modelNumber"
            placeholder="e.g., FRFS2823AD, WRS325SDHZ, GDT665SSNSS"
            value={values.modelNumber}
            onChange={handleChange}
            disabled={isDisabled}
            required
          />
        </div>

        <div className="input-group input-wide">
          <label htmlFor="problemDescription">Symptoms *</label>
          <textarea
            id="problemDescription"
            name="problemDescription"
            placeholder="Describe the issue, sounds, timing, leaks, and any error codes."
            value={values.problemDescription}
            onChange={handleChange}
            disabled={isDisabled}
            rows={5}
            maxLength={600}
            required
          />
        </div>

        <div className="input-wide">
          <details className="disclosure">
            <summary>Need inspiration? Explore tips and examples.</summary>
            <div className="tips-grid">
              <div>
                <h3>Helpful Examples</h3>
                <ul>
                  <li>Leaking water from bottom front after defrost cycle</li>
                  <li>Not cooling, compressor runs constantly, frost in freezer</li>
                  <li>Making loud grinding noise when dispensing ice</li>
                  <li>Display shows E1 error, not heating</li>
                </ul>
              </div>
              <div>
                <h3>Avoid Vague Notes</h3>
                <ul className="list-muted">
                  <li>"It's broken"</li>
                  <li>"Not working"</li>
                  <li>"Makes noise"</li>
                  <li>"Has a problem"</li>
                </ul>
              </div>
              <div>
                <h3>Pro Tips</h3>
                <ul>
                  {fieldDescriptions.map((tip) => (
                    <li key={tip}>{tip}</li>
                  ))}
                </ul>
              </div>
            </div>
          </details>
        </div>

        <div className="actions input-wide">
          <button
            className={clsx("btn", "btn-primary", { "btn-disabled": isDisabled })}
            type="submit"
            disabled={isDisabled}
          >
            {loading ? "Analyzing..." : "Run Diagnosis"}
          </button>
        </div>
      </form>
    </section>
  );
};

export default DiagnosisForm;

