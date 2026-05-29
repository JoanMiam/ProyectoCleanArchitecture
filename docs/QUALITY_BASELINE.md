# Quality Baseline (INS-15)

Estabilización del baseline técnico del backend **antes** de los tickets
funcionales. No se agrega funcionalidad: solo limpieza de lint y configuración
reproducible. mypy, import-linter y pytest ya estaban en verde; el trabajo fue
dejar `ruff` en verde y fijar el baseline.

## Comandos de validación

Ejecutados desde `backend/` con el venv activo (`pip install -e ".[dev]"`):

```bash
ruff check src/ tests/     # estilo + imports
mypy src/                  # tipos (strict)
lint-imports               # regla de capas (import-linter)
pytest tests/unit -v       # tests
```
Para ejecutar 4 tests en powershell (Windows), se ejecuta lo siguiente en (.venv)

ruff check src/ tests/; mypy src/; lint-imports; pytest tests/unit -v



Atajo equivalente del Makefile: `make lint-local && make test-local`.

## Estado inicial (antes de INS-15)

| Herramienta | Resultado | Detalle |
|---|---|---|
| mypy | ✅ | 46 archivos, sin errores |
| import-linter | ✅ | 3/3 contratos de capas respetados |
| pytest | ✅ | 38 tests passed |
| ruff | ❌ | 9 errores + 1 warning de config |

### Hallazgos de ruff y corrección aplicada

| Regla | Sitio | Corrección |
|---|---|---|
| `E501` (línea >100) | `domain/entities/evidence.py:11` | Docstring reflejado a varias líneas. |
| `E501` | `domain/entities/inspection.py:144` | Firma de `remove_observation` multilínea. |
| `E501` | `tests/unit/application/test_edit_inspection.py:135` | Llamada multilínea. |
| `N818` (excepción sin sufijo `Error`) | `domain/exceptions.py` ×4 | Renombradas: `InspectionNotFound-->InspectionNotFoundError`, `ObservationNotFound-->ObservationNotFoundError`, `EvidenceNotFound-->EvidenceNotFoundError`, `InvariantViolation-->InvariantViolationError`. Actualizadas todas las referencias en `entities/inspection.py` y `tests/`. |
| `UP042` (`str, Enum`) | `domain/value_objects/inspection_status.py` | Migrado a `enum.StrEnum` (Python 3.12). |
| `I001` (imports sin ordenar) | `tests/unit/conftest.py` | `ruff check --fix` (auto). |
| warning | `pyproject.toml` | Eliminados ignores muertos `ANN101`/`ANN102` (reglas removidas en ruff nuevo). |

### Cambios de configuración (justificados)

- **`ruff>=0.4` → `ruff>=0.15,<0.16`**: el rango sin tope hacía que `pip` instalara
  una versión más nueva que la usada al crear el scaffold, introduciendo reglas
  (`UP042`, comportamiento de `N818`) que no existían antes. Fijar el rango hace
  el baseline **reproducible** entre máquinas y CI. Es el objetivo del ticket.
- **Quitar `ANN101`/`ANN102` del ignore**: ambas reglas fueron eliminadas de ruff;
  ignorarlas no tiene efecto y genera un warning. Limpieza de config, no
  relajación.

> **No se relajó ninguna regla de calidad.** Los errores se corrigieron en el
> código (incluido el rename `N818`), no suprimiéndolos. Única alternativa
> considerada y descartada: ignorar `N818` en `exceptions.py` con argumento DDD
> ("NotFound" lee mejor que "NotFoundError"); se descartó por preferir nombres
> conformes a PEP 8 desde el inicio, antes de que INS-5/6/7 dependan de ellos.

## Estado final (después de INS-15)

```text
ruff check src/ tests/   → All checks passed!
mypy src/                → Success: no issues found in 46 source files
lint-imports             → Contracts: 3 kept, 0 broken.
pytest tests/unit        → 38 passed
```

## Notas para tickets posteriores

- Las excepciones de dominio ahora terminan en `Error`. Cualquier issue que las
  use (INS-5 persistencia, INS-6 ApplyChangesBatch) debe importar los nombres
  nuevos.
- `InspectionStatus` es `StrEnum`: `str(InspectionStatus.DRAFT) == "draft"`
  (antes era `"InspectionStatus.DRAFT"`). Relevante al serializar a JSON.
- Opcional (no requerido por el DoD): `ruff format src/ tests/` para formateo
  automático consistente. No se aplicó aquí para acotar el cambio a lint.
