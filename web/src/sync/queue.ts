import type {
  ChangeSet,
  InspectionSummary,
  QueuedChange,
  SyncBatch,
  SyncResponse,
} from "../types";

export const QUEUE_STORAGE_KEY = "inspections.offline.queue.v1";

type CreateInspectionUpdateInput = {
  inspection: InspectionSummary;
  title: string;
  location: string;
  changeId?: string;
  now?: Date;
};

export function createInspectionUpdateChange({
  inspection,
  title,
  location,
  changeId = randomId(),
  now = new Date(),
}: CreateInspectionUpdateInput): QueuedChange {
  const nextTitle = title.trim();
  const nextLocation = location.trim();
  const payload: ChangeSet["payload"] = {};

  if (nextTitle.length === 0) {
    throw new Error("El titulo de la inspeccion no puede quedar vacio.");
  }

  if (nextLocation.length === 0) {
    throw new Error("La ubicacion de la inspeccion no puede quedar vacia.");
  }

  if (nextTitle !== inspection.title) {
    payload.title = nextTitle;
  }

  if (nextLocation !== inspection.location) {
    payload.location = nextLocation;
  }

  if (Object.keys(payload).length === 0) {
    throw new Error("No hay cambios locales para encolar.");
  }

  return {
    id: changeId,
    entity_id: inspection.inspection_id,
    entity_type: "inspection",
    operation: "update",
    base_version: inspection.version,
    payload,
    created_at: now.toISOString(),
    sync_status: "pending",
  };
}

export function createSyncBatch(
  queuedChanges: QueuedChange[],
  clientId = "web-mvp",
  batchId = randomId(),
): SyncBatch {
  const changes = queuedChanges
    .filter((change) => change.sync_status === "pending")
    .map(toChangeSet);

  if (changes.length === 0) {
    throw new Error("No hay cambios pendientes por sincronizar.");
  }

  return {
    batch_id: batchId,
    client_id: clientId,
    changes,
  };
}

export function applySyncResponse(
  queue: QueuedChange[],
  response: SyncResponse,
): QueuedChange[] {
  const appliedById = new Map(
    response.applied_changes.map((change) => [change.change_id, change]),
  );
  const rejectedById = new Map(
    response.rejected_changes.map((change) => [change.change_id, change]),
  );

  return queue.map((change) => {
    const applied = appliedById.get(change.id);
    if (applied) {
      return {
        ...change,
        sync_status: "applied" as const,
        new_version: applied.new_version,
        reason: undefined,
        server_state: undefined,
      };
    }

    const rejected = rejectedById.get(change.id);
    if (rejected) {
      return {
        ...change,
        sync_status: rejected.conflict ? ("conflict" as const) : ("rejected" as const),
        reason: rejected.reason,
        server_state: rejected.conflict?.server_state,
      };
    }

    return change;
  });
}

export function mergeServerDelta(
  inspections: InspectionSummary[],
  response: SyncResponse,
): InspectionSummary[] {
  const nextById = new Map(
    inspections.map((inspection) => [inspection.inspection_id, inspection]),
  );

  for (const inspection of response.server_delta.inspections ?? []) {
    nextById.set(inspection.id, {
      inspection_id: inspection.id,
      title: inspection.title,
      location: inspection.location,
      status: inspection.status,
      version: inspection.version,
    });
  }

  for (const rejectedChange of response.rejected_changes) {
    const serverState = rejectedChange.conflict?.server_state;
    if (!serverState) {
      continue;
    }

    nextById.set(serverState.id, {
      inspection_id: serverState.id,
      title: serverState.title,
      location: serverState.location,
      status: serverState.status,
      version: serverState.version,
    });
  }

  return Array.from(nextById.values());
}

export function applyPendingQueue(
  inspections: InspectionSummary[],
  queue: QueuedChange[],
): InspectionSummary[] {
  const nextById = new Map(
    inspections.map((inspection) => [inspection.inspection_id, { ...inspection }]),
  );

  for (const change of queue) {
    if (change.sync_status !== "pending") {
      continue;
    }

    const inspection = nextById.get(change.entity_id);
    if (!inspection) {
      continue;
    }

    nextById.set(change.entity_id, {
      ...inspection,
      title: change.payload.title ?? inspection.title,
      location: change.payload.location ?? inspection.location,
    });
  }

  return Array.from(nextById.values());
}

export function loadQueuedChanges(storage: Storage = localStorage): QueuedChange[] {
  const rawQueue = storage.getItem(QUEUE_STORAGE_KEY);
  if (!rawQueue) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawQueue) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(isQueuedChange);
  } catch {
    return [];
  }
}

export function saveQueuedChanges(
  queue: QueuedChange[],
  storage: Storage = localStorage,
): void {
  storage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(queue));
}

export function clearAppliedChanges(queue: QueuedChange[]): QueuedChange[] {
  return queue.filter((change) => change.sync_status !== "applied");
}

function toChangeSet(change: QueuedChange): ChangeSet {
  return {
    id: change.id,
    entity_id: change.entity_id,
    entity_type: change.entity_type,
    operation: change.operation,
    base_version: change.base_version,
    payload: change.payload,
    created_at: change.created_at,
  };
}

function isQueuedChange(value: unknown): value is QueuedChange {
  if (!value || typeof value !== "object") {
    return false;
  }

  const change = value as Partial<QueuedChange>;
  return (
    typeof change.id === "string" &&
    typeof change.entity_id === "string" &&
    change.entity_type === "inspection" &&
    change.operation === "update" &&
    typeof change.base_version === "number" &&
    typeof change.created_at === "string" &&
    (change.sync_status === "pending" ||
      change.sync_status === "applied" ||
      change.sync_status === "conflict" ||
      change.sync_status === "rejected") &&
    typeof change.payload === "object" &&
    change.payload !== null
  );
}

function randomId(): string {
  if ("crypto" in globalThis && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }

  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (token) => {
    const random = Math.floor(Math.random() * 16);
    const value = token === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}
