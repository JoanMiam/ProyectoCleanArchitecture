# Offline-first Inspections System

Sistema de inspecciones de campo con sincronización offline, control de versiones y resolución de conflictos. Construido con **Clean Architecture**.

**Stack:** FastAPI (Python 3.12) · Flutter (Android) · React + Vite · PostgreSQL · Redis · MinIO · Docker

## Quick-start (5 comandos)

```bash
git clone <repo-url> && cd ProyectoCleanArchitecture
cp .env.example .env
make up
make migrate
make seed
```

- API: http://localhost:8000/docs
- Web panel: http://localhost:5173
- MinIO console: http://localhost:9001

## Estructura

```
ProyectoCleanArchitecture/
├── backend/    FastAPI + Clean Architecture (domain → application → infrastructure → interfaces)
├── mobile/     Flutter offline-first (Android) — extensión futura, fuera del MVP
├── web/        React + Vite cliente mínimo de demo (MVP)
├── infra/      PostgreSQL init, MinIO policies
└── docs/       Arquitectura, protocolo sync, onboarding
```

## Comandos frecuentes

| Comando | Descripción |
|---|---|
| `make up` | Levantar stack completo |
| `make down` | Bajar stack |
| `make migrate` | Correr migraciones Alembic |
| `make seed` | Datos de prueba |
| `make test` | Tests backend (pytest) |
| `make test-mobile` | Tests Flutter (fuera de MVP) |
| `make lint` | Ruff + mypy + import-linter |
| `make logs` | Ver logs de todos los servicios |

## Arquitectura

Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Onboarding

Ver [docs/ONBOARDING.md](docs/ONBOARDING.md).
