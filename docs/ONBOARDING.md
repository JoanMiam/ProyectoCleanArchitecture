# Onboarding — Setup del equipo

## Requisitos

| Herramienta | Versión mínima | Instalación |
|---|---|---|
| Docker Desktop | 4.x | https://docker.com |
| Docker Compose | v2 (incluido en Docker Desktop) | — |
| Git | 2.x | `brew install git` |
| gh CLI | 2.x | `brew install gh` |
| Python | 3.12 (solo si dev local sin Docker) | `brew install python@3.12` |
| Flutter SDK | 3.x (solo para mobile) | https://flutter.dev |
| Node.js | 20 LTS (solo para web) | `brew install node` |

## Setup inicial (primera vez)

```bash
# 1. Clonar
git clone <repo-url>
cd ProyectoClean

# 2. Variables de entorno
cp .env.example .env
# Editar .env si necesitas cambiar puertos o passwords

# 3. Levantar stack
make up
# Primera vez descarga imágenes (~2min)

# 4. Migrar DB
make migrate

# 5. Seed de datos de prueba
make seed

# 6. Verificar
curl http://localhost:8000/healthz   # debe retornar {"status":"ok"}
open http://localhost:8000/docs      # Swagger UI
open http://localhost:9001           # MinIO console (minioadmin/minioadmin123)
```

## Desarrollo día a día

```bash
make up           # levantar (si no está corriendo)
make logs         # ver logs en vivo
make test-unit    # tests rápidos (sin Docker, solo unit)
make lint         # ruff + mypy + import-linter
make migrate      # después de crear nueva migración
make down         # bajar al terminar
```

## Dev local backend (sin Docker, más rápido para iterate)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Requiere Postgres/Redis corriendo (puedes usar: docker compose up postgres redis -d)
export $(grep -v '^#' ../.env | xargs)
DATABASE_URL=postgresql+asyncpg://inspections_user:inspections_pass@localhost:5432/inspections_db

pytest tests/unit/ -v             # tests unitarios (no necesita Postgres)
ruff check src/ tests/
mypy src/
lint-imports
```

## Workflow de ramas

```
main          — protegida, requiere PR + review + CI verde
feat/<scope>  — nuevas features
fix/<scope>   — bug fixes
chore/<scope> — infra, deps, docs
```

## Convenciones de commits (Conventional Commits)

```
feat: add offline inspection capture
fix: correct version comparison in conflict detection
chore: update alembic to 1.13
test: add unit tests for ApplyChangesBatch
refactor: extract conflict detection to domain policy
docs: add sync protocol spec
```

## Troubleshooting frecuente

**`make up` falla con "port already in use":**
```bash
# Ver qué usa el puerto
lsof -i :5432   # postgres
lsof -i :6379   # redis
lsof -i :9000   # minio
# Cambiar puertos en .env o docker-compose.yml
```

**`make migrate` falla con "connection refused":**
```bash
# Esperar a que postgres esté healthy
docker compose ps   # verificar que postgres está "healthy"
```

**Tests fallan con import errors:**
```bash
cd backend && pip install -e ".[dev]"
```
