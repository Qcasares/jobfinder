export type ApiHealthStatus = {
  state: "healthy" | "unconfigured" | "unreachable";
  label: string;
  detail: string;
  checkedUrl?: string;
};

export async function getApiHealth(): Promise<ApiHealthStatus> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    return {
      state: "unconfigured",
      label: "API not configured",
      detail: "Set NEXT_PUBLIC_API_BASE_URL to enable the FastAPI health check."
    };
  }

  const healthUrl = new URL("/health", apiBaseUrl).toString();

  try {
    const response = await fetch(healthUrl, {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });

    if (!response.ok) {
      return {
        state: "unreachable",
        label: "API returned an error",
        detail: `Health endpoint responded with HTTP ${response.status}.`,
        checkedUrl: healthUrl
      };
    }

    return {
      state: "healthy",
      label: "API health check passed",
      detail: "FastAPI /health responded successfully.",
      checkedUrl: healthUrl
    };
  } catch {
    return {
      state: "unreachable",
      label: "API unreachable",
      detail: "Dashboard is running with local mock data only.",
      checkedUrl: healthUrl
    };
  }
}
