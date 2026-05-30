# Architecture

## Clean Architecture — Regla de dependencias

```
┌─────────────────────────────────────────────────────────┐
│  interfaces/  (HTTP routers, workers)                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │  infrastructure/  (SQLAlchemy, MinIO, Redis, JWT) │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  application/  (use cases, ports/ABCs, DTOs)│  │  │
│  │  │  ┌───────────────────────────────────────┐  │  │  │
│  │  │  │  domain/  (entities, value objects,   │  │  │  │
│  │  │  │           policies, events, exceptions)│  │  │  │
│  │  │  └───────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Regla:** las flechas apuntan hacia adentro. `domain/` no importa NADA externo.
Enforced por `import-linter` en CI — un PR que viola la regla no mergea.

## Capas

### domain/
- `entities/` ✅: Inspection (aggregate root), Observation, Evidence, User
- `value_objects/` ✅: InspectionStatus (StrEnum), Version, IDs (NewType), ConflictType, ResolutionStrategy
- `policies/` ✅: ConflictPolicy (optimistic locking), Conflict value object
- `events.py` ✅: DomainEvent base + InspectionCreated, InspectionSubmitted, InspectionClosed, ObservationAdded, ObservationEdited, ObservationRemoved, EvidenceAttached
- `exceptions.py` ✅: DomainError, InspectionNotFoundError, ObservationNotFoundError, EvidenceNotFoundError, InvalidStateError

**Sin imports de FastAPI, SQLAlchemy, Pydantic, Redis.** Solo stdlib.

### application/
- `ports/` ✅: InspectionRepository, UnitOfWork, Clock, AuthContext, ChangeSetRepository, ConflictRepository, AuditRepository, FileStorageGateway, QueueGateway, TokenProvider, PasswordHasher, UserRepository
- `use_cases/` ✅: CreateInspection, EditInspection, GetInspection, ListInspections, AddObservation, SubmitInspection, ApplyChangesBatch, ResolveConflict, AttachEvidence, Login, GetAuditTrail
- `dto/` ✅: CreateInspectionDTO, EditInspectionDTO, GetInspectionDTO, ListInspectionsDTO, AddObservationDTO, SubmitInspectionDTO, AttachEvidenceDTO, AuditDTO (read model), AuthDTO, SyncDTO

**Sin imports de infrastructure/ o interfaces/.**

### infrastructure/
- `persistence/sqlalchemy/` ✅: modelos ORM (Inspection, Observation, Evidence, User, AppliedChange, AuditEvent), mappers ORM↔Domain, SQLAlchemyInspectionRepository, SQLAlchemyUserRepository, SQLAlchemyAuditRepository, SQLAlchemyChangeSetRepository, SQLAlchemyUnitOfWork
- `storage/minio_storage.py` ✅: MinIOStorageGateway impl (FileStorageGateway)
- `queue/rq_gateway.py` ✅: RQGateway impl (QueueGateway) con asyncio.to_thread
- `auth/` ✅: JwtTokenProvider, BcryptPasswordHasher, JwtAuthContext
- `clock/system_clock.py` ✅: SystemClock impl

### interfaces/
- `http/routers/` ✅: auth, inspections, sync, evidences, audit
- `http/schemas/` ✅: Pydantic schemas — solo en esta capa (inspection, sync, evidence, audit, auth)
- `http/deps.py` ✅: dependency providers FastAPI, AuthContext, AuditRepoDep, UnitOfWorkDep, etc.
- `workers/audit_worker.py` ✅: RQ job para persistir eventos de auditoría

## C4 — Vista de contenedores

```
┌──────────────────────────────────────────────────────────────┐
│  Web Client (React + Vite) [MVP — cliente mínimo de demo]    │
│       │ sync batch (HTTP POST /sync/batch)                   │
│       ▼                                                       │
│  Backend API (FastAPI)  ──────────────────────────────────┐  │
│       │                                                    │  │
│       ├──► PostgreSQL 16 (estado autoritativo)             │  │
│       ├──► Redis + RQ (jobs asíncronos)                    │  │
│       └──► MinIO (evidencias/archivos)                     │  │
│                                                            │  │
│  Mobile App (Flutter/Android) ── extensión futura (no MVP) │  │
└──────────────────────────────────────────────────────────────┘
```

## API HTTP

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/auth/login` | Autenticación JWT |
| `POST` | `/inspections` | Crear inspección |
| `GET` | `/inspections` | Listar inspecciones |
| `GET` | `/inspections/{id}` | Obtener inspección |
| `PATCH` | `/inspections/{id}` | Editar inspección |
| `POST` | `/inspections/{id}/observations` | Agregar observación |
| `POST` | `/inspections/{id}/submit` | Enviar inspección |
| `POST` | `/inspections/{id}/evidences` | Adjuntar evidencia |
| `GET` | `/inspections/{id}/audit` | Audit trail |
| `POST` | `/sync/batch` | Aplicar lote de cambios offline |

## Flujo de auditoría

```
Mutation (HTTP) → Use case → async with uow → commit → salir del bloque
                                                             ↓
                                               inspection.collect_events()
                                                             ↓
                                               AuditRepository.append_many()
                                                             ↓
                                               audit_events table (JSONB payload)

GET /inspections/{id}/audit → GetAuditTrail use case → list[AuditEntryDTO]
```

El `AuditRepository` es independiente de la `UnitOfWork`: append-only, separado de la transacción principal.

## Protocolo de sincronización

Ver [SYNC_PROTOCOL.md](SYNC_PROTOCOL.md).

## Quality tools

| Tool | Propósito |
|---|---|
| Docker Compose | Entorno reproducible |
| GitHub Actions | CI: lint + type + test en cada PR y push a main/develop |
| Ruff | Linter + formatter Python |
| mypy (strict) | Type checking Python, 106 archivos fuente |
| import-linter | Enforce regla de dependencias (3 contratos) |
| pytest + coverage | Tests + gate ≥85% cobertura |
| dart analyze | Lint Flutter (extensión futura) |
| ESLint + Prettier | Lint web |
| vitest | Tests web |
