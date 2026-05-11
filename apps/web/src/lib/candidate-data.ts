export type CandidateDataSource = "api" | "local";

export type CandidateProfile = {
  id: string;
  userId: string;
  profileName: string;
  summary: string | null;
  synthetic: boolean;
};

export type CandidateEvidence = {
  id: string;
  evidenceType: "skill" | "project" | "experience" | "credential";
  title: string;
  description: string | null;
  sourceUrl: string | null;
  verifiedAt: string | null;
  synthetic: boolean;
};

export type SearchCriteria = {
  id: string;
  name: string;
  query: string;
  location: string | null;
  remoteType: "remote" | "hybrid" | "onsite" | "unknown";
  salaryMin: number | null;
  salaryMax: number | null;
  synthetic: boolean;
};

export type CandidateWorkspaceSnapshot = {
  source: CandidateDataSource;
  detail: string;
  checkedUrl?: string;
  safetyNote: string;
  profile: CandidateProfile;
  evidence: CandidateEvidence[];
  searchCriteria: SearchCriteria[];
};

type ApiCandidateWorkspace = {
  profile: {
    id: string;
    user_id: string;
    profile_name: string;
    summary: string | null;
    synthetic: boolean;
  };
  evidence: Array<{
    id: string;
    evidence_type: CandidateEvidence["evidenceType"];
    title: string;
    description: string | null;
    source_url: string | null;
    verified_at: string | null;
    synthetic: boolean;
  }>;
  search_criteria: Array<{
    id: string;
    name: string;
    query: string;
    location: string | null;
    remote_type: SearchCriteria["remoteType"];
    salary_min: number | null;
    salary_max: number | null;
    synthetic: boolean;
  }>;
  safety_note: string;
};

export async function getCandidateWorkspaceSnapshot(): Promise<CandidateWorkspaceSnapshot> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    return localCandidateWorkspaceSnapshot(
      "NEXT_PUBLIC_API_BASE_URL is not configured; no connected candidate profile is shown."
    );
  }

  const workspaceUrl = new URL("/candidate/workspace", apiBaseUrl).toString();

  try {
    const response = await fetch(workspaceUrl, {
      cache: "no-store",
      headers: { accept: "application/json" }
    });

    if (!response.ok) {
      return localCandidateWorkspaceSnapshot(
        `Candidate API returned HTTP ${response.status}; no connected candidate profile is shown.`,
        workspaceUrl
      );
    }

    return mapApiCandidateWorkspace((await response.json()) as ApiCandidateWorkspace, workspaceUrl);
  } catch {
    return localCandidateWorkspaceSnapshot(
      "Candidate API is unreachable; no connected candidate profile is shown.",
      workspaceUrl
    );
  }
}

function mapApiCandidateWorkspace(
  workspace: ApiCandidateWorkspace,
  checkedUrl: string
): CandidateWorkspaceSnapshot {
  return {
    source: "api",
    detail:
      "Candidate workspace is loaded from approved profile evidence and candidate vault metadata.",
    checkedUrl,
    safetyNote: workspace.safety_note,
    profile: {
      id: workspace.profile.id,
      userId: workspace.profile.user_id,
      profileName: workspace.profile.profile_name,
      summary: workspace.profile.summary,
      synthetic: workspace.profile.synthetic
    },
    evidence: workspace.evidence.map((item) => ({
      id: item.id,
      evidenceType: item.evidence_type,
      title: item.title,
      description: item.description,
      sourceUrl: item.source_url,
      verifiedAt: item.verified_at,
      synthetic: item.synthetic
    })),
    searchCriteria: workspace.search_criteria.map((item) => ({
      id: item.id,
      name: item.name,
      query: item.query,
      location: item.location,
      remoteType: item.remote_type,
      salaryMin: item.salary_min,
      salaryMax: item.salary_max,
      synthetic: item.synthetic
    }))
  };
}

function localCandidateWorkspaceSnapshot(
  detail: string,
  checkedUrl?: string
): CandidateWorkspaceSnapshot {
  return {
    source: "local",
    detail,
    checkedUrl,
    safetyNote:
      "Candidate profile data must be connected through approved evidence or candidate vault metadata before use.",
    profile: {
      id: "profile-connection-pending",
      userId: "profile-user-pending",
      profileName: "Candidate profile not connected",
      summary: null,
      synthetic: true
    },
    evidence: [],
    searchCriteria: []
  };
}
