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

> **Leyenda de estado:** ✅ implementado · 🔲 previsto (pendiente de issue)

### domain/
- `entities/` ✅: Inspection (aggregate root), Observation, Evidence
- `value_objects/` ✅: InspectionStatus, Version, IDs
- `policies/` 🔲: ConflictPolicy, MergePolicy (INS-3)
- `events.py` 🔲: domain events — ConflictDetected, ConflictResolved, ChangeApplied (INS-3)
- `exceptions/` 🔲: DomainError, InvalidStateError

**Sin imports de FastAPI, SQLAlchemy, Pydantic, Redis.** Solo stdlib.

### application/
- `ports/` ✅ parcial: InspectionRepository, UnitOfWork, Clock, AuthContext
- `ports/` 🔲: ChangeSetRepository, ConflictRepository, AuditRepository, FileStorageGateway, QueueGateway (INS-4)
- `use_cases/` ✅: CreateInspection, EditInspection
- `use_cases/` 🔲: GetInspection, ListInspections, AddObservation, SubmitInspection (INS-13), ApplyChangesBatch (INS-6), ResolveConflict (INS-7), AttachEvidence (INS-9), Login (INS-14)
- `dto/` ✅ parcial: CreateInspectionDTO, EditInspectionDTO
- `dto/` ✅: sync DTOs — ChangeSet, SyncBatch, ServerDelta, ConflictResult (INS-2)

**Sin imports de infrastructure/ o interfaces/.**

### infrastructure/
- `persistence/sqlalchemy/` 🔲: modelos ORM, mappers ORM↔Domain, repositorios concretos (INS-5)
- `storage/minio_storage.py` 🔲: FileStorageGateway impl (INS-9)
- `queue/` 🔲: QueueGateway impl (INS-4/INS-10)
- `auth/` 🔲: JWT provider, password hasher (INS-14)
- `clock/system_clock.py` ✅: Clock impl

### interfaces/
- `http/routers/` 🔲: inspections, sync, evidences, auth, audit (INS-8)
- `http/schemas/` 🔲: Pydantic schemas — solo en esta capa (INS-8)
- `http/deps.py` 🔲: dependencias FastAPI, AuthContext (INS-14)
- `workers/` 🔲: RQ workers para audit y proyecciones (INS-10)

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

## Protocolo de sincronización

Ver [SYNC_PROTOCOL.md](SYNC_PROTOCOL.md).

## Quality tools

| Tool | Propósito |
|---|---|
| Docker Compose | Entorno reproducible |
| GitHub Actions | CI: lint + type + test en cada PR |
| Ruff | Linter + formatter Python |
| mypy (strict) | Type checking Python |
| import-linter | Enforce regla de dependencias |
| pytest + coverage | Tests + gate ≥85% en domain/application |
| dart analyze | Lint Flutter |
| ESLint + Prettier | Lint web |
| vitest | Tests web |
