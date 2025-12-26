export interface IssueDetails {
  difficulty?: string | null;
  time?: string | null;
  explanation?: string | null;
  parts: string[];
  verify_steps: string[];
  repair_steps: string[];
  safety_warnings: string[];
  video_searches: string[];
}

export interface ProbabilityItem {
  percent: number;
  title: string;
  description: string;
  details?: IssueDetails | null;
}

export interface WebResult {
  title: string;
  url: string;
  snippet: string;
}

export interface DiagnosisResponse {
  message: string;
  full_analysis: string;
  probabilities: ProbabilityItem[];
  web_results: WebResult[];
  timestamp: string;
  model_number: string;
  problem: string;
  tech_name?: string | null;
  job_number?: string | null;
}

export interface VNVPartSummary {
  item_number: string;
  part_number: string;
  description?: string | null;
  qty_available?: number | null;
  price?: number | null;
  list_price?: number | null;
  url?: string | null;
  image_urls: string[];
}

export interface VNVDiagramSummary {
  diagram_id: number;
  section_name: string;
  small_image_url?: string | null;
  large_image_url?: string | null;
  parts: VNVPartSummary[];
}

export interface VNVModelSummary {
  model_number: string;
  model_description?: string | null;
  manufacturer?: string | null;
  model_id: number;
}

export interface DiagramBundleResponse {
  model: VNVModelSummary;
  diagrams: VNVDiagramSummary[];
}

export interface DiagnosisRequest {
  tech_name: string;
  job_number: string;
  model_number: string;
  problem_description: string;
}

export interface DiagnosisFormValues {
  techName: string;
  jobNumber: string;
  modelNumber: string;
  problemDescription: string;
}

export type OutcomeStatus = "resolved" | "unresolved" | null;

export interface SourceLink {
  label: string;
  url: string;
  snippet?: string | null;
  origin?: "inline" | "web";
}
