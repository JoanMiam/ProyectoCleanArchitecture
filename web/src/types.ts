export type SyncStatus = "pending" | "applied" | "conflict" | "rejected";

export type InspectionSummary = {
  inspection_id: string;
  title: string;
  location: string;
  status: string;
  version: number;
};

export type InspectionListResponse = {
  items: InspectionSummary[];
  count: number;
};

export type InspectionMutationResponse = {
  inspection_id: string;
  version: number;
  status: string;
};

export type ChangeSet = {
  id: string;
  entity_id: string;
  entity_type: "inspection";
  operation: "update";
  base_version: number;
  payload: {
    title?: string;
    location?: string;
  };
  created_at: string;
};

export type QueuedChange = ChangeSet & {
  sync_status: SyncStatus;
  reason?: string;
  new_version?: number;
  server_state?: ServerInspectionState;
};

export type SyncBatch = {
  batch_id: string;
  client_id: string;
  changes: ChangeSet[];
};

export type AppliedChange = {
  change_id: string;
  new_version: number;
};

export type RejectedChange = {
  change_id: string;
  reason: string;
  conflict?: ConflictResult;
};

export type ConflictResult = {
  change_id: string;
  entity_id: string;
  entity_type: string;
  server_version: number;
  client_version: number;
  server_state: ServerInspectionState;
  reason: string;
};

export type ServerInspectionState = {
  id: string;
  title: string;
  location: string;
  status: string;
  version: number;
  created_by: string;
  created_at: string;
  updated_at: string;
  observations: unknown[];
  evidences: unknown[];
};

export type SyncResponse = {
  batch_id: string;
  status: "success" | "partial_success" | "conflict";
  applied_changes: AppliedChange[];
  rejected_changes: RejectedChange[];
  server_delta: {
    inspections?: ServerInspectionState[];
  };
};

export type AuthSession = {
  accessToken: string;
  tokenType: string;
};
