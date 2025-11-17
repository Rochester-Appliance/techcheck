import axios from "axios";

import {
  DiagnosisRequest,
  DiagnosisResponse,
  DiagramBundleResponse,
  IssueDetails,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 1800000,
});

const extractErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    return (
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "Request failed"
    );
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error";
};

export const diagnose = async (
  payload: DiagnosisRequest,
): Promise<DiagnosisResponse> => {
  try {
    const { data } = await client.post<DiagnosisResponse>("/diagnose", payload);
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const fetchIssueDetails = async (
  issue: string,
  full_analysis: string,
): Promise<IssueDetails> => {
  try {
    const { data } = await client.post<{ details: IssueDetails }>(
      "/diagnose/issue-details",
      { issue, full_analysis },
    );
    return data.details;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const fetchDiagramBundle = async (
  model_number: string,
  max_diagrams = 6,
  max_parts_per_diagram = 12,
): Promise<DiagramBundleResponse> => {
  try {
    const { data } = await client.post<DiagramBundleResponse>("/parts/diagrams", {
      model_number,
      max_diagrams,
      max_parts_per_diagram,
    });
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const api = { diagnose, fetchIssueDetails, fetchDiagramBundle };

