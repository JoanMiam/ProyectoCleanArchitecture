import { describe, expect, it } from "vitest";

import type { InspectionSummary, QueuedChange, SyncResponse } from "../types";
import {
  applyPendingQueue,
  applySyncResponse,
  clearAppliedChanges,
  createInspectionUpdateChange,
  createSyncBatch,
  loadQueuedChanges,
  mergeServerDelta,
  QUEUE_STORAGE_KEY,
  saveQueuedChanges,
} from "./queue";

const inspection: InspectionSummary = {
  inspection_id: "11111111-1111-4111-8111-111111111111",
  title: "Puente norte",
  location: "Merida",
  status: "draft",
  version: 3,
};

describe("offline queue", () => {
  it("creates a backend-compatible inspection update ChangeSet", () => {
    const change = createInspectionUpdateChange({
      inspection,
      title: "Puente norte revisado",
      location: "Merida",
      changeId: "22222222-2222-4222-8222-222222222222",
      now: new Date("2026-05-30T12:00:00.000Z"),
    });

    expect(change).toMatchObject({
      id: "22222222-2222-4222-8222-222222222222",
      entity_id: inspection.inspection_id,
      entity_type: "inspection",
      operation: "update",
      base_version: 3,
      payload: { title: "Puente norte revisado" },
      created_at: "2026-05-30T12:00:00.000Z",
      sync_status: "pending",
    });
  });

  it("rejects empty local edits before building a ChangeSet", () => {
    expect(() =>
      createInspectionUpdateChange({
        inspection,
        title: "Puente norte",
        location: "Merida",
      }),
    ).toThrow("No hay cambios locales para encolar.");
  });

  it("rejects blank title or location before sending sync payloads", () => {
    expect(() =>
      createInspectionUpdateChange({
        inspection,
        title: "   ",
        location: "Merida",
      }),
    ).toThrow("El titulo de la inspeccion no puede quedar vacio.");

    expect(() =>
      createInspectionUpdateChange({
        inspection,
        title: "Puente norte",
        location: "   ",
      }),
    ).toThrow("La ubicacion de la inspeccion no puede quedar vacia.");
  });

  it("builds a sync batch with only pending changes", () => {
    const pending = queuedChange("33333333-3333-4333-8333-333333333333", "pending");
    const applied = queuedChange("44444444-4444-4444-8444-444444444444", "applied");

    const batch = createSyncBatch(
      [pending, applied],
      "web-test",
      "55555555-5555-4555-8555-555555555555",
    );

    expect(batch).toEqual({
      batch_id: "55555555-5555-4555-8555-555555555555",
      client_id: "web-test",
      changes: [
        {
          id: pending.id,
          entity_id: pending.entity_id,
          entity_type: "inspection",
          operation: "update",
          base_version: pending.base_version,
          payload: pending.payload,
          created_at: pending.created_at,
        },
      ],
    });
  });

  it("marks applied and conflicting changes from a sync response", () => {
    const applied = queuedChange("66666666-6666-4666-8666-666666666666", "pending");
    const conflict = queuedChange("77777777-7777-4777-8777-777777777777", "pending");
    const response: SyncResponse = {
      batch_id: "88888888-8888-4888-8888-888888888888",
      status: "partial_success",
      applied_changes: [{ change_id: applied.id, new_version: 4 }],
      rejected_changes: [
        {
          change_id: conflict.id,
          reason: "version_mismatch",
          conflict: {
            change_id: conflict.id,
            entity_id: conflict.entity_id,
            entity_type: "inspection",
            server_version: 5,
            client_version: 3,
            reason: "version_mismatch",
            server_state: {
              id: conflict.entity_id,
              title: "Servidor",
              location: "Merida",
              status: "draft",
              version: 5,
              created_by: "99999999-9999-4999-8999-999999999999",
              created_at: "2026-05-30T12:00:00",
              updated_at: "2026-05-30T12:30:00",
              observations: [],
              evidences: [],
            },
          },
        },
      ],
      server_delta: { inspections: [] },
    };

    const nextQueue = applySyncResponse([applied, conflict], response);

    expect(nextQueue[0]).toMatchObject({ sync_status: "applied", new_version: 4 });
    expect(nextQueue[1]).toMatchObject({
      sync_status: "conflict",
      reason: "version_mismatch",
      server_state: { title: "Servidor", version: 5 },
    });
  });

  it("merges authoritative server delta into the inspection list", () => {
    const response: SyncResponse = {
      batch_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      status: "success",
      applied_changes: [],
      rejected_changes: [],
      server_delta: {
        inspections: [
          {
            id: inspection.inspection_id,
            title: "Puente norte final",
            location: "Progreso",
            status: "draft",
            version: 4,
            created_by: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            created_at: "2026-05-30T12:00:00",
            updated_at: "2026-05-30T12:40:00",
            observations: [],
            evidences: [],
          },
        ],
      },
    };

    expect(mergeServerDelta([inspection], response)).toEqual([
      {
        inspection_id: inspection.inspection_id,
        title: "Puente norte final",
        location: "Progreso",
        status: "draft",
        version: 4,
      },
    ]);
  });

  it("merges conflict server state into the inspection list", () => {
    const response: SyncResponse = {
      batch_id: "abababab-abab-4aba-8bab-abababababab",
      status: "conflict",
      applied_changes: [],
      rejected_changes: [
        {
          change_id: "cdcdcdcd-cdcd-4cdc-8dcd-cdcdcdcdcdcd",
          reason: "version_mismatch",
          conflict: {
            change_id: "cdcdcdcd-cdcd-4cdc-8dcd-cdcdcdcdcdcd",
            entity_id: inspection.inspection_id,
            entity_type: "inspection",
            server_version: 9,
            client_version: 3,
            reason: "version_mismatch",
            server_state: {
              id: inspection.inspection_id,
              title: "Titulo autoritativo",
              location: "Servidor",
              status: "draft",
              version: 9,
              created_by: "efefefef-efef-4efe-8fef-efefefefefef",
              created_at: "2026-05-30T12:00:00",
              updated_at: "2026-05-30T12:55:00",
              observations: [],
              evidences: [],
            },
          },
        },
      ],
      server_delta: { inspections: [] },
    };

    expect(mergeServerDelta([inspection], response)).toEqual([
      {
        inspection_id: inspection.inspection_id,
        title: "Titulo autoritativo",
        location: "Servidor",
        status: "draft",
        version: 9,
      },
    ]);
  });

  it("applies pending queue changes over freshly loaded server data", () => {
    const pending = queuedChange("cccccccc-cccc-4ccc-8ccc-cccccccccccc", "pending");

    expect(applyPendingQueue([inspection], [pending])).toEqual([
      {
        ...inspection,
        title: pending.payload.title,
      },
    ]);
  });

  it("stores only valid queued changes and can remove applied entries", () => {
    const storage = new MemoryStorage();
    const pending = queuedChange("dddddddd-dddd-4ddd-8ddd-dddddddddddd", "pending");
    const applied = queuedChange("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", "applied");

    saveQueuedChanges([pending, applied], storage);
    storage.setItem(
      QUEUE_STORAGE_KEY,
      JSON.stringify([...loadQueuedChanges(storage), { invalid: true }]),
    );

    const loaded = loadQueuedChanges(storage);
    expect(loaded).toHaveLength(2);
    expect(clearAppliedChanges(loaded)).toEqual([pending]);
  });
});

function queuedChange(
  id: string,
  syncStatus: QueuedChange["sync_status"],
): QueuedChange {
  return {
    id,
    entity_id: inspection.inspection_id,
    entity_type: "inspection",
    operation: "update",
    base_version: inspection.version,
    payload: { title: "Puente norte local" },
    created_at: "2026-05-30T12:00:00.000Z",
    sync_status: syncStatus,
  };
}

class MemoryStorage implements Storage {
  private readonly items = new Map<string, string>();

  get length(): number {
    return this.items.size;
  }

  clear(): void {
    this.items.clear();
  }

  getItem(key: string): string | null {
    return this.items.get(key) ?? null;
  }

  key(index: number): string | null {
    return Array.from(this.items.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.items.delete(key);
  }

  setItem(key: string, value: string): void {
    this.items.set(key, value);
  }
}
