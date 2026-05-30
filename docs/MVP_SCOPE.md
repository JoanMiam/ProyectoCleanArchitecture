# Alcance del MVP

Define qué entra y qué queda fuera del MVP académico del proyecto **Offline-first Inspections System**.

---

## Qué incluye el MVP

### Dominio
- Entidad `Inspection` como agregado raíz con estados: `Draft`, `InProgress`, `Submitted`, `Closed`.
- Entidades `Observation` y `Evidence` asociadas al agregado.
- Control de versiones mediante `Version` en cada agregado.
- Políticas de conflicto y merge: `keep_server`, `keep_client`, `manual_merge`.
- Eventos de dominio auditables: `ChangeApplied`, `ConflictDetected`, `ConflictResolved`.

### Contratos de sincronización
- `ChangeSet`: cambio local generado por un cliente offline.
- `SyncBatch`: lote de ChangeSets enviado al backend con metadatos de idempotencia.
- `ServerDelta`: cambios autoritativos devueltos por el servidor tras aplicar un batch.
- `ConflictResult`: representación explícita de un conflicto con estado autoritativo y cambio entrante.

### Backend (FastAPI + Clean Architecture)
- `ApplyChangesBatch`: caso de uso central — recibe un lote, valida idempotencia por `batch_id`/`change_id`, compara `base_version`, aplica o devuelve conflicto.
- `ResolveConflict`: caso de uso para resolver conflictos con las tres estrategias básicas.
- `AttachEvidence`: adjuntar archivos a una inspección u observación.
- Casos de uso base: `CreateInspection`, `EditInspection`, `GetInspection`, `ListInspections`, `AddObservation`, `SubmitInspection`.
- Auditoría: registro de quién cambió qué y cuándo por inspección.
- Read models: listado resumido de inspecciones por estado, usuario y fecha.
- Autenticación JWT: login, token, endpoints protegidos, `AuthContext`.
- Persistencia autoritativa: PostgreSQL via SQLAlchemy + Alembic.
- Almacenamiento de evidencias: MinIO (S3-compatible).
- Jobs asíncronos: Redis + RQ para proyecciones y auditoría.

### API HTTP
- `POST /auth/login`
- `POST /inspections`
- `GET /inspections`, `GET /inspections/{id}`
- `PATCH /inspections/{id}`
- `POST /sync/batch`
- `POST /inspections/{id}/evidences`
- `GET /inspections/{id}/audit`

### Cliente mínimo web (React + Vite)
- Crear y editar una inspección.
- Cola local de cambios en el cliente.
- Enviar batch al endpoint `POST /sync/batch`.
- Mostrar estado de sincronización: pendiente, aplicado, conflicto.
- **No** incluye offline storage real en el cliente (IndexedDB/localStorage mínimo para demo).

### Calidad
- `ruff` + `mypy` + `import-linter` + `pytest` con cobertura mínima en dominio/application.
- CI con GitHub Actions: lint + type check + tests en cada PR.
- Docker Compose: stack completo reproducible.

---

## Qué queda fuera del MVP

| Fuera de alcance | Motivo |
|---|---|
| App móvil Flutter | Tiempo limitado; web client cubre la demo offline-first con menor riesgo. Queda como extensión documentada. |
| Offline storage complejo en cliente | IndexedDB/service workers están fuera del alcance de la materia backend-first. |
| Merge automático por campos (field-level CRDT) | La política `manual_merge` con payload explícito cubre el MVP. CRDTs son extensión futura. |
| Panel de administración completo | La web es un cliente mínimo de demo, no un panel de supervisión completo. |
| Multi-tenancy | Un solo tenant (equipo de inspectores). |
| Notificaciones en tiempo real (WebSocket/SSE) | No requerido para defender el MVP. |

---

## Mapa de issues al MVP

| Componente MVP | Issue |
|---|---|
| Documentación alineada | INS-1 |
| Contratos sync (ChangeSet, SyncBatch, etc.) | INS-2 |
| Dominio conflictos y políticas | INS-3 |
| Ports (ChangeSetRepo, ConflictRepo, AuditRepo, FileStorageGateway, QueueGateway) | INS-4 |
| Persistencia SQLAlchemy y UnitOfWork real | INS-5 |
| ApplyChangesBatch con idempotencia y versionado | INS-6 |
| ResolveConflict (3 estrategias) | INS-7 |
| Endpoints HTTP + schemas Pydantic | INS-8 |
| AttachEvidence + MinIO adapter | INS-9 |
| Auditoría y read models | INS-10 |
| Cliente web mínimo (React + Vite) | INS-11 |
| Calidad final — CI, cobertura, docs finales | INS-12 |
| Casos de uso base inspecciones | INS-13 |
| Autenticación JWT y AuthContext | INS-14 |
| Baseline de calidad técnica inicial | INS-15 |

---

## Decisión de alcance cliente

Se prioriza **React + Vite** como cliente mínimo (INS-11) en lugar de Flutter/Android porque:
- Permite demo más rápida sin configurar emuladores ni SDKs móviles.
- El valor del proyecto está en el backend (sincronización, conflictos, auditoría).
- Un cliente web que consume `POST /sync/batch` demuestra el protocolo con menor riesgo de tiempo.

Flutter queda documentado como extensión futura en `mobile/`.
