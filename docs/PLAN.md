# Plan de ejecución — Sistema Offline-first de Inspecciones

Plan de trabajo para los 15 issues (INS-1 … INS-15), repartidos 3 por integrante (5 integrantes).
El objetivo es construir el MVP sobre el scaffold actual respetando Clean Architecture, el orden de
dependencias y las herramientas de calidad declaradas (`ruff`, `mypy`, `import-linter`, `pytest`).

> **Lectura clave:** el reparto dice **quién posee** cada issue. El **orden** lo marcan las **olas**.
> Nadie hace sus 3 issues de golpe: caen en olas distintas según sus dependencias.

---

## 1. Estado actual del repo (punto de partida)

Solo existe un scaffold mínimo:

- **Domain:** `Inspection`, `Observation`, `Evidence`, `Version`, `ids`, `inspection_status`.
  Faltan conflictos y políticas (`domain/policies/` vacío).
- **Application:** use cases solo `create_inspection`, `edit_inspection`.
  Ports: `auth_context`, `clock`, `inspection_repository`, `unit_of_work`. DTOs solo create/edit.
- **Infrastructure:** `persistence/sqlalchemy/models` y `/mappers` vacíos; `auth/`, `storage/`, `queue/` vacíos.
- **Interfaces:** routers vacíos (solo health check en `main`).
- **Tests:** create, edit, dominio inspection. Una migración Alembic `0001_init`.
- Docker Compose y CI base ya presentes.

---

## 2. Grafo de dependencias

```
INS-1 (docs) ──┬─> INS-15 (quality baseline)
               └─> INS-2 (contratos sync) ──┬─> INS-3 (dominio conflicto)
                                             ├─> INS-4 (ports) ──> INS-5 (persistencia SQLAlchemy)
                                             └─> INS-13 (use cases base)

INS-2,3,4,13 ──> INS-6 (ApplyChangesBatch) ──> INS-7 (resolver conflictos)
INS-5 ──> INS-14 (auth JWT)
INS-5,6,13,14 ──> INS-8 (endpoints HTTP) ──┬─> INS-9 (evidencias/MinIO)
                                           ├─> INS-10 (auditoría/read models)
                                           └─> INS-11 (cliente web)
TODO ──> INS-12 (calidad final, cierra al final)
```

**Ruta crítica:** `INS-1 → INS-2 → INS-4 → INS-5 → INS-6 → INS-8`. Todo lo demás cuelga de ahí.

---

## 3. Olas de ejecución (reloj del proyecto)

| Ola | Issues | Objetivo |
|-----|--------|----------|
| **0 — Cimientos** | INS-1, INS-15 | Documentación alineada + baseline de calidad limpio. Desbloquean todo. |
| **1 — Contratos + dominio** | INS-2 → INS-3, INS-4, INS-13 | Contratos sync + dominio de conflicto + ports + use cases base. |
| **2 — Persistencia + core** | INS-5, INS-6 | SQLAlchemy/UnitOfWork real + ApplyChangesBatch (con fakes hasta tener INS-5). |
| **3 — Features + auth** | INS-14, INS-7, INS-8, INS-9 | JWT, resolución de conflictos, endpoints HTTP, evidencias. |
| **4 — Cliente + auditoría** | INS-10, INS-11 | Auditoría/read models + cliente web (arranca con mocks en ola 1). |
| **5 — Cierre** | INS-12 | CI verde, cobertura, import-linter, documentación final y demo. |

Regla: un issue **no empieza** hasta que sus dependencias cierran. Dentro de una ola varias
personas trabajan en paralelo.

---

## 4. Reparto por integrante (3 issues c/u)

| Integrante | Issues | Tema |
|---|---|---|
| **A — Núcleo sync** | INS-2, INS-6, INS-7 | Contratos, ApplyChangesBatch, resolución de conflictos |
| **B — Dominio base** | INS-4, INS-3, INS-13 | Ports, dominio de conflicto, use cases base |
| **C — Persistencia + auth** | INS-5, INS-14, INS-15 | SQLAlchemy/UoW, JWT/AuthContext, baseline de calidad |
| **D — Interfaz + evidencia** | INS-8, INS-9, INS-11 | Endpoints HTTP, MinIO, cliente web |
| **E — Docs + auditoría + QA final** | INS-1, INS-10, INS-12 | Docs (primero), auditoría/read models, calidad final (cierra) |

**Lógica:**
- **E** hace INS-1 primero → desbloquea a todos; cierra el proyecto con INS-12.
- **B** entrega fundaciones (ports/dominio/use cases) temprano → desbloquea a **A** y **C**. Concentra carga en ola 1.
- **A** dueño del valor central (sync/conflictos) — el "plato fuerte" para defender en la exposición.
- **C** persistencia + auth, ambos cuelgan de los ports de **B**.
- **D** capa externa (HTTP/web/evidencia); arranca el web con mocks sin esperar el backend.

---

## 5. Timeline real (olas × personas)

| Ola | A (núcleo) | B (dominio) | C (persist+auth) | D (interfaz) | E (docs+QA) |
|-----|-----------|-------------|------------------|--------------|-------------|
| **0** | — | — | **INS-15** | — | **INS-1** |
| **1** | **INS-2** | **INS-4 → INS-3 → INS-13** | espera | INS-11 (mocks) | — |
| **2** | **INS-6** (fakes) | apoya A | **INS-5** | espera | — |
| **3** | **INS-7** | apoya | **INS-14** | **INS-8 → INS-9** | — |
| **4** | apoya | apoya | apoya | **INS-11** (real) | **INS-10** |
| **5** | — | — | — | — | **INS-12** |

"Espera / apoya" = revisar PRs, escribir tests, desbloquear la ruta crítica. Nadie ocioso.

### Flujo concreto de cada quien
- **A:** INS-2 (ola 1) → INS-6 con fakes (ola 2) → INS-7 (ola 3).
- **B:** sus 3 juntos en ola 1 (INS-4 → INS-3 → INS-13); luego apoya. Excepción que concentra carga temprano.
- **C:** INS-15 (ola 0) → INS-5 (ola 2) → INS-14 (ola 3).
- **D:** INS-11 con mocks (ola 1) → INS-8 → INS-9 (ola 3) → INS-11 contra backend real (ola 4).
- **E:** INS-1 (ola 0) → INS-10 (ola 4, cuando hay persistencia + endpoints) → INS-12 (ola 5, cierre).

---

## 6. Riesgos de coordinación

- **INS-8 es cuello de botella** (depende de INS-5, 6, 13, 14). D debe coordinar mocks tempranos con A/B/C.
- **INS-6 antes que INS-5:** A debe trabajar con fakes de repositorio, no esperar persistencia real.
- **`docs/SYNC_PROTOCOL.md`** lo escribe A (INS-2) pero lo consumen D (INS-8) y E (INS-11). Fijar el contrato JSON pronto.
- **Deriva arquitectónica:** cada PR debe pasar `ruff`, `mypy`, `import-linter`, `pytest` (regla repetida en casi todos los DoD).

---

## 7. Definition of Done transversal (todos los PRs)

- `ruff check src/ tests/` pasa.
- `mypy src/` pasa (o excepciones documentadas y justificadas).
- `lint-imports` (import-linter) pasa — sin violaciones de capas.
- `pytest` pasa; los tests existentes no se rompen.
- El dominio y la capa application **no** importan FastAPI, Pydantic, SQLAlchemy ni infraestructura.
- Commit con el mensaje sugerido en cada issue.
