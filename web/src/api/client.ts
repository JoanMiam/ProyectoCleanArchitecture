import type {
  AuthSession,
  InspectionListResponse,
  InspectionMutationResponse,
  SyncBatch,
  SyncResponse,
} from "../types";

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH";
  token?: string;
  body?: unknown;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export class InspectionsApi {
  constructor(private readonly baseUrl: string) {}

  async login(email: string, password: string): Promise<AuthSession> {
    const response = await this.request<{ access_token: string; token_type: string }>(
      "/auth/login",
      {
        method: "POST",
        body: { email, password },
      },
    );
    return {
      accessToken: response.access_token,
      tokenType: response.token_type,
    };
  }

  async listInspections(token: string): Promise<InspectionListResponse> {
    return this.request<InspectionListResponse>("/inspections", { token });
  }

  async createInspection(
    token: string,
    title: string,
    location: string,
  ): Promise<InspectionMutationResponse> {
    return this.request<InspectionMutationResponse>("/inspections", {
      method: "POST",
      token,
      body: { title, location },
    });
  }

  async patchInspection(
    token: string,
    inspectionId: string,
    payload: { title?: string; location?: string },
  ): Promise<InspectionMutationResponse> {
    return this.request<InspectionMutationResponse>(`/inspections/${inspectionId}`, {
      method: "PATCH",
      token,
      body: payload,
    });
  }

  async syncBatch(token: string, batch: SyncBatch): Promise<SyncResponse> {
    return this.request<SyncResponse>("/sync/batch", {
      method: "POST",
      token,
      body: batch,
    });
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: options.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });

    if (!response.ok) {
      throw new ApiError(await readErrorMessage(response), response.status);
    }

    return (await response.json()) as T;
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    return response.statusText;
  }
  return response.statusText;
}

export function resolveApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
}
