import {
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  ClipboardList,
  LogIn,
  LogOut,
  Plus,
  RefreshCcw,
  Save,
  Server,
  UploadCloud,
  Wifi,
  WifiOff,
  XCircle,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { ApiError, InspectionsApi, resolveApiBaseUrl } from "./api/client";
import type { AuthSession, InspectionSummary, QueuedChange } from "./types";
import {
  applyPendingQueue,
  applySyncResponse,
  clearAppliedChanges,
  createInspectionUpdateChange,
  createSyncBatch,
  loadQueuedChanges,
  mergeServerDelta,
  saveQueuedChanges,
} from "./sync/queue";

const AUTH_STORAGE_KEY = "inspections.auth.v1";
const DEFAULT_EMAIL = "admin@inspections.local";
const DEFAULT_PASSWORD = "change-me";

type Notice = {
  kind: "info" | "success" | "warning" | "error";
  message: string;
};

type Draft = {
  title: string;
  location: string;
};

export default function App(): JSX.Element {
  const apiBaseUrl = resolveApiBaseUrl();
  const api = useMemo(() => new InspectionsApi(apiBaseUrl), [apiBaseUrl]);
  const [session, setSession] = useState<AuthSession | null>(loadSession);
  const [email, setEmail] = useState(DEFAULT_EMAIL);
  const [password, setPassword] = useState(DEFAULT_PASSWORD);
  const [inspections, setInspections] = useState<InspectionSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>({ title: "", location: "" });
  const [newInspection, setNewInspection] = useState<Draft>({
    title: "Inspeccion de campo",
    location: "Merida",
  });
  const [queue, setQueue] = useState<QueuedChange[]>(loadQueuedChanges);
  const [notice, setNotice] = useState<Notice>({
    kind: "info",
    message: "Inicia sesion y carga inspecciones para operar el MVP offline-first.",
  });
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);

  const selectedInspection =
    inspections.find((inspection) => inspection.inspection_id === selectedId) ?? null;
  const pendingCount = queue.filter((change) => change.sync_status === "pending").length;
  const conflictCount = queue.filter((change) => change.sync_status === "conflict").length;
  const hasPendingForSelected =
    selectedInspection !== null &&
    queue.some(
      (change) =>
        change.entity_id === selectedInspection.inspection_id &&
        change.sync_status === "pending",
    );
  const isBusy = busyAction !== null;

  useEffect(() => {
    saveQueuedChanges(queue);
  }, [queue]);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    if (!session) {
      return;
    }

    void refreshInspections(session.accessToken, queue, { silent: true }).catch((error) => {
      setNotice({ kind: "error", message: errorMessage(error) });
    });
    // Solo debe correr al recuperar una sesion guardada.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleLogin(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusyAction("login");
    try {
      const nextSession = await api.login(email.trim(), password);
      setSession(nextSession);
      saveSession(nextSession);
      await refreshInspections(nextSession.accessToken, queue);
      setNotice({ kind: "success", message: "Sesion iniciada. Contratos HTTP listos." });
    } catch (error) {
      setNotice({ kind: "error", message: errorMessage(error) });
    } finally {
      setBusyAction(null);
    }
  }

  function handleLogout(): void {
    setSession(null);
    clearSession();
    setInspections([]);
    setSelectedId(null);
    setDraft({ title: "", location: "" });
    setNotice({ kind: "info", message: "Sesion cerrada. La cola local permanece guardada." });
  }

  async function handleRefresh(): Promise<void> {
    if (!session) {
      return;
    }

    setBusyAction("refresh");
    try {
      await refreshInspections(session.accessToken, queue);
      setNotice({ kind: "success", message: "Inspecciones actualizadas desde backend." });
    } catch (error) {
      setNotice({ kind: "error", message: errorMessage(error) });
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCreateInspection(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!session) {
      return;
    }

    const title = newInspection.title.trim();
    const location = newInspection.location.trim();
    if (!title || !location) {
      setNotice({ kind: "warning", message: "Titulo y ubicacion son obligatorios." });
      return;
    }

    setBusyAction("create");
    try {
      const created = await api.createInspection(session.accessToken, title, location);
      const loaded = await api.listInspections(session.accessToken);
      const nextInspections = applyPendingQueue(loaded.items, queue);
      setInspections(nextInspections);
      selectInspection(created.inspection_id, nextInspections, { title, location });
      setNewInspection({ title: "Inspeccion de campo", location: "Merida" });
      setNotice({
        kind: "success",
        message: `Inspeccion creada en backend con version ${created.version}.`,
      });
    } catch (error) {
      setNotice({ kind: "error", message: errorMessage(error) });
    } finally {
      setBusyAction(null);
    }
  }

  function handleSelectInspection(inspection: InspectionSummary): void {
    selectInspection(inspection.inspection_id, inspections);
  }

  function handleQueueLocalEdit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (!selectedInspection) {
      setNotice({ kind: "warning", message: "Selecciona una inspeccion primero." });
      return;
    }

    if (hasPendingForSelected) {
      setNotice({
        kind: "warning",
        message: "Ya existe una edicion pendiente para esta inspeccion. Sincronizala primero.",
      });
      return;
    }

    try {
      const change = createInspectionUpdateChange({
        inspection: selectedInspection,
        title: draft.title,
        location: draft.location,
      });
      const nextQueue = [change, ...queue];
      setQueue(nextQueue);
      setInspections((current) =>
        current.map((inspection) =>
          inspection.inspection_id === selectedInspection.inspection_id
            ? {
                ...inspection,
                title: change.payload.title ?? inspection.title,
                location: change.payload.location ?? inspection.location,
              }
            : inspection,
        ),
      );
      setDraft({
        title: change.payload.title ?? selectedInspection.title,
        location: change.payload.location ?? selectedInspection.location,
      });
      setNotice({
        kind: "info",
        message: "Edicion guardada localmente. Pendiente de POST /sync/batch.",
      });
    } catch (error) {
      setNotice({ kind: "warning", message: errorMessage(error) });
    }
  }

  async function handleSync(): Promise<void> {
    if (!session) {
      return;
    }

    setBusyAction("sync");
    try {
      const batch = createSyncBatch(queue);
      const response = await api.syncBatch(session.accessToken, batch);
      const nextQueue = applySyncResponse(queue, response);
      const nextInspections = mergeServerDelta(inspections, response);
      setQueue(nextQueue);
      setInspections(nextInspections);

      if (selectedId) {
        const selected = nextInspections.find(
          (inspection) => inspection.inspection_id === selectedId,
        );
        if (selected) {
          setDraft({ title: selected.title, location: selected.location });
        }
      }

      setNotice({
        kind: response.rejected_changes.length > 0 ? "warning" : "success",
        message: `${syncStatusLabel(response.status)}: ${response.applied_changes.length} aplicado(s), ${response.rejected_changes.length} rechazado(s).`,
      });
    } catch (error) {
      setNotice({ kind: "error", message: errorMessage(error) });
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSimulateServerChange(): Promise<void> {
    if (!session || !selectedInspection) {
      return;
    }

    if (hasPendingForSelected) {
      setNotice({
        kind: "warning",
        message: "Sincroniza la edicion pendiente antes de simular otro cambio remoto.",
      });
      return;
    }

    setBusyAction("server-change");
    try {
      const suffix = new Date().toLocaleTimeString("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
      });
      const result = await api.patchInspection(session.accessToken, selectedInspection.inspection_id, {
        title: `${selectedInspection.title} servidor ${suffix}`,
      });
      setNotice({
        kind: "info",
        message: `Cambio directo aplicado en servidor version ${result.version}. La vista local no se refresco para poder demostrar conflicto.`,
      });
    } catch (error) {
      setNotice({ kind: "error", message: errorMessage(error) });
    } finally {
      setBusyAction(null);
    }
  }

  function handleClearApplied(): void {
    setQueue((current) => clearAppliedChanges(current));
    setNotice({ kind: "info", message: "Cambios aplicados retirados de la cola local." });
  }

  async function refreshInspections(
    token: string,
    queueSnapshot: QueuedChange[],
    options: { silent?: boolean } = {},
  ): Promise<void> {
    const response = await api.listInspections(token);
    const nextInspections = applyPendingQueue(response.items, queueSnapshot);
    setInspections(nextInspections);

    if (selectedId) {
      const selected = nextInspections.find(
        (inspection) => inspection.inspection_id === selectedId,
      );
      if (selected) {
        setDraft({ title: selected.title, location: selected.location });
        return;
      }
    }

    if (nextInspections[0]) {
      selectInspection(nextInspections[0].inspection_id, nextInspections);
    } else {
      setSelectedId(null);
      setDraft({ title: "", location: "" });
    }

    if (!options.silent) {
      setNotice({ kind: "success", message: "Inspecciones cargadas desde backend." });
    }
  }

  function selectInspection(
    inspectionId: string,
    source: InspectionSummary[],
    fallbackDraft?: Draft,
  ): void {
    const inspection = source.find((item) => item.inspection_id === inspectionId);
    setSelectedId(inspectionId);
    setDraft(
      inspection
        ? { title: inspection.title, location: inspection.location }
        : fallbackDraft ?? { title: "", location: "" },
    );
  }

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">INS-11 cliente web MVP</p>
          <h1>Inspecciones offline-first</h1>
        </div>
        <div className="top-actions">
          <span className={isOnline ? "network online" : "network offline"}>
            {isOnline ? <Wifi size={16} /> : <WifiOff size={16} />}
            {isOnline ? "online" : "offline"}
          </span>
          <span className="api-url">{apiBaseUrl}</span>
          {session ? (
            <button className="icon-button" type="button" onClick={handleLogout} title="Cerrar sesion">
              <LogOut size={18} />
            </button>
          ) : null}
        </div>
      </header>

      {!session ? (
        <section className="auth-view" aria-label="Autenticacion">
          <form className="auth-panel" onSubmit={handleLogin}>
            <div>
              <p className="eyebrow">Backend protegido</p>
              <h2>Iniciar sesion</h2>
            </div>
            <label>
              Correo
              <input
                autoComplete="username"
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                value={email}
              />
            </label>
            <label>
              Contrasena
              <input
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />
            </label>
            <button className="primary-button" disabled={isBusy} type="submit">
              <LogIn size={18} />
              {busyAction === "login" ? "Entrando..." : "Entrar"}
            </button>
          </form>
        </section>
      ) : (
        <section className="workspace" aria-label="Cliente de sincronizacion">
          <aside className="inspection-pane" aria-label="Listado de inspecciones">
            <div className="pane-header">
              <div>
                <p className="eyebrow">Servidor</p>
                <h2>Inspecciones</h2>
              </div>
              <button
                className="icon-button"
                disabled={isBusy}
                onClick={handleRefresh}
                title="Recargar inspecciones"
                type="button"
              >
                <RefreshCcw size={18} />
              </button>
            </div>

            <form className="compact-form" onSubmit={handleCreateInspection}>
              <label>
                Titulo
                <input
                  onChange={(event) =>
                    setNewInspection((current) => ({
                      ...current,
                      title: event.target.value,
                    }))
                  }
                  value={newInspection.title}
                />
              </label>
              <label>
                Ubicacion
                <input
                  onChange={(event) =>
                    setNewInspection((current) => ({
                      ...current,
                      location: event.target.value,
                    }))
                  }
                  value={newInspection.location}
                />
              </label>
              <button className="secondary-button" disabled={isBusy} type="submit">
                <Plus size={17} />
                Crear
              </button>
            </form>

            <div className="inspection-list">
              {inspections.length === 0 ? (
                <p className="empty-state">No hay inspecciones cargadas.</p>
              ) : null}
              {inspections.map((inspection) => (
                <button
                  className={
                    inspection.inspection_id === selectedId
                      ? "inspection-row selected"
                      : "inspection-row"
                  }
                  key={inspection.inspection_id}
                  onClick={() => handleSelectInspection(inspection)}
                  type="button"
                >
                  <ClipboardList size={18} />
                  <span>
                    <strong>{inspection.title}</strong>
                    <small>
                      v{inspection.version} · {inspection.status} · {inspection.location}
                    </small>
                  </span>
                </button>
              ))}
            </div>
          </aside>

          <section className="editor-pane" aria-label="Editor local">
            <div className="pane-header">
              <div>
                <p className="eyebrow">Local</p>
                <h2>Editar inspeccion</h2>
              </div>
              {selectedInspection ? (
                <span className="version-pill">base v{selectedInspection.version}</span>
              ) : null}
            </div>

            <form className="editor-form" onSubmit={handleQueueLocalEdit}>
              <label>
                Titulo
                <input
                  disabled={!selectedInspection}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, title: event.target.value }))
                  }
                  value={draft.title}
                />
              </label>
              <label>
                Ubicacion
                <input
                  disabled={!selectedInspection}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, location: event.target.value }))
                  }
                  value={draft.location}
                />
              </label>
              <div className="editor-actions">
                <button
                  className="primary-button"
                  disabled={!selectedInspection || isBusy || hasPendingForSelected}
                  type="submit"
                >
                  <Save size={18} />
                  Guardar local
                </button>
                <button
                  className="ghost-button"
                  disabled={!selectedInspection || isBusy || hasPendingForSelected}
                  onClick={handleSimulateServerChange}
                  type="button"
                >
                  <Server size={18} />
                  Cambio servidor
                </button>
              </div>
            </form>

            <div className={`notice ${notice.kind}`} role="status">
              {noticeIcon(notice.kind)}
              <span>{notice.message}</span>
            </div>
          </section>

          <aside className="queue-pane" aria-label="Cola de sincronizacion">
            <div className="pane-header">
              <div>
                <p className="eyebrow">POST /sync/batch</p>
                <h2>Cola local</h2>
              </div>
              <span className="queue-count">{pendingCount} pendientes</span>
            </div>

            <div className="queue-actions">
              <button
                className="primary-button"
                disabled={pendingCount === 0 || isBusy}
                onClick={handleSync}
                type="button"
              >
                <UploadCloud size={18} />
                Sincronizar
              </button>
              <button
                className="ghost-button"
                disabled={queue.every((change) => change.sync_status !== "applied")}
                onClick={handleClearApplied}
                type="button"
              >
                Limpiar aplicados
              </button>
            </div>

            <div className="sync-summary">
              <span>
                <CircleDot size={14} />
                {queue.length} cambios
              </span>
              <span>
                <AlertTriangle size={14} />
                {conflictCount} conflictos
              </span>
            </div>

            <div className="queue-list">
              {queue.length === 0 ? <p className="empty-state">Cola local vacia.</p> : null}
              {queue.map((change) => (
                <article className="queue-item" key={change.id}>
                  <div className="queue-item-header">
                    <StatusBadge status={change.sync_status} />
                    <small>{formatDate(change.created_at)}</small>
                  </div>
                  <strong>{change.payload.title ?? "Sin cambio de titulo"}</strong>
                  <small>
                    inspeccion {shortId(change.entity_id)} · base v{change.base_version}
                  </small>
                  {change.reason ? <p className="reason">Motivo: {change.reason}</p> : null}
                  {change.server_state ? (
                    <div className="server-state">
                      <span>Servidor v{change.server_state.version}</span>
                      <strong>{change.server_state.title}</strong>
                      <small>{change.server_state.location}</small>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          </aside>
        </section>
      )}
    </main>
  );
}

function StatusBadge({ status }: { status: QueuedChange["sync_status"] }): JSX.Element {
  const labels: Record<QueuedChange["sync_status"], string> = {
    pending: "pendiente",
    applied: "aplicado",
    conflict: "conflicto",
    rejected: "rechazado",
  };

  return <span className={`status-badge ${status}`}>{labels[status]}</span>;
}

function noticeIcon(kind: Notice["kind"]): JSX.Element {
  if (kind === "success") {
    return <CheckCircle2 size={18} />;
  }
  if (kind === "error") {
    return <XCircle size={18} />;
  }
  if (kind === "warning") {
    return <AlertTriangle size={18} />;
  }
  return <CircleDot size={18} />;
}

function loadSession(): AuthSession | null {
  const rawSession = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!rawSession) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawSession) as Partial<AuthSession>;
    if (typeof parsed.accessToken === "string" && typeof parsed.tokenType === "string") {
      return {
        accessToken: parsed.accessToken,
        tokenType: parsed.tokenType,
      };
    }
  } catch {
    return null;
  }

  return null;
}

function saveSession(session: AuthSession): void {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

function clearSession(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Error inesperado.";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "2-digit",
  }).format(new Date(value));
}

function shortId(value: string): string {
  return value.slice(0, 8);
}

function syncStatusLabel(status: string): string {
  if (status === "success") {
    return "Sincronizacion completa";
  }
  if (status === "partial_success") {
    return "Sincronizacion parcial";
  }
  if (status === "conflict") {
    return "Conflicto de sincronizacion";
  }
  return `Sincronizacion ${status}`;
}
