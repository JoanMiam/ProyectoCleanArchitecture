# Alineación del proyecto con la materia Clean Architecture

Este documento registra cómo los conceptos vistos en las presentaciones de la materia se deben aplicar al proyecto **Offline-first Inspections System**. Su propósito es evitar que el desarrollo se convierta en un CRUD y asegurar que cada decisión técnica pueda defenderse desde Clean Architecture, SOLID, DDD, TDD, calidad y separación de detalles tecnológicos.

## Material revisado

Se revisó el archivo `PresentacionesCLEAN.zip`, descomprimido localmente, con 20 PDFs y 319 páginas en total. Se aplicó extracción de texto de PDF y OCR selectivo en 50 páginas con texto insuficiente o contenido principalmente visual.

| Archivo | Páginas | OCR aplicado en páginas |
|---|---:|---|
| `1.1.cleanArchitectureIntroduction.pdf` | 16 | 1, 2 |
| `1.2.CleanCode.pdf` | 14 | 2, 4, 5 |
| `1.3.BigO.pdf` | 13 | 13 |
| `1.4.paradigms.pdf` | 19 | 16 |
| `1.5.qualityTools.pdf` | 8 | 7, 8 |
| `1.6.tdd.pdf` | 30 | 5, 6, 7, 9, 12, 13, 20 |
| `1.7.RthinkDesignPatternsV2.pdf` | 22 | 9, 18 |
| `2.0.Solid.pdf` | 5 | 1 |
| `2.1.Srp.pdf` | 13 | - |
| `2.2.OpenClosed.pdf` | 10 | 1 |
| `2.2.z.DDD.pdf` | 13 | - |
| `2.3.Liskov.pdf` | 9 | 5, 6, 7 |
| `2.4.InterfaceSegregation.pdf` | 9 | - |
| `2.5.DependencyInversion.pdf` | 19 | 1, 8, 9, 10, 11, 12, 13 |
| `3.0.CleanArchitecture.pdf` | 17 | 1, 4, 5, 6, 7, 8 |
| `3.1.Boundaries.pdf` | 9 | 4 |
| `3.2.CleanAnatomy.pdf` | 16 | - |
| `3.3.Domain.pdf` | 30 | 21, 22, 28 |
| `3.4.TheInfrastructure.pdf` | 20 | - |
| `3.5.OtherArchitectures.pdf` | 27 | 3, 4, 5, 7, 8, 9, 10, 11, 12, 13 |

## Principios de la materia que deben guiar el proyecto

### 1. Arquitectura como protección del cambio

La arquitectura no debe verse como carpetas bonitas, sino como una forma de minimizar el costo de construir y mantener el sistema. En este proyecto, el costo principal aparece en la sincronización offline-first, la evolución de reglas de conflicto, los cambios de infraestructura y la incorporación de clientes distintos.

Aplicación concreta:

- El dominio no debe depender de FastAPI, SQLAlchemy, Redis, MinIO, Pydantic ni frameworks.
- Los casos de uso deben describir reglas de aplicación, no detalles HTTP.
- PostgreSQL, Redis, MinIO, FastAPI, React y Flutter son detalles reemplazables.
- El sistema debe hacer evidente su intención: inspecciones, evidencias, lotes de sincronización, conflictos, auditoría y modelos de lectura.

### 2. Clean Code como base antes de la arquitectura

Las presentaciones recalcan reglas de código limpio: nombres descriptivos, evitar variables mágicas, funciones pequeñas, funciones con una sola responsabilidad, pocos argumentos, evitar side effects ocultos y evitar comentarios que compensen código confuso.

Aplicación concreta:

- Nombrar conceptos con lenguaje del dominio: `Inspection`, `Observation`, `Evidence`, `ChangeSet`, `SyncBatch`, `ConflictResult`, `AuditTrail`.
- Evitar nombres genéricos como `Manager`, `Handler`, `Processor` cuando exista un concepto del dominio más preciso.
- Evitar `dict` crudos en el dominio cuando el concepto tenga reglas propias.
- Usar value objects para identidad, versión, estado y resultado de conflicto.
- Evitar funciones de caso de uso que mezclen validación, persistencia, mapeo HTTP y lógica de dominio.

### 3. Big O y eficiencia en sincronización

La materia introduce Big O para razonar sobre eficiencia. En este proyecto debe aplicarse especialmente al procesamiento de batches y conflictos.

Aplicación concreta:

- `ApplyChangesBatch` no debe comparar cada cambio contra todos los cambios previos con ciclos anidados innecesarios.
- Usar mapas por `change_id`, `inspection_id` y `entity_id` para deduplicación e idempotencia.
- Definir límites de tamaño de batch.
- Indexar en base de datos campos como `batch_id`, `change_id`, `inspection_id`, `base_version` y `created_at`.
- Evitar reconstruir read models completos cuando se puede proyectar incrementalmente.

### 4. Paradigmas: disciplina y diseño

La materia relaciona paradigmas con disciplina: estructurado controla el flujo directo, orientado a objetos controla la transferencia indirecta mediante polimorfismo y funcional controla la asignación.

Aplicación concreta:

- Usar polimorfismo a través de puertos: `InspectionRepository`, `FileStorageGateway`, `QueueGateway`, `AuthContext`.
- Mantener entidades con comportamiento donde existan invariantes reales.
- Mantener DTOs como estructuras de datos sin comportamiento.
- Evitar herencia innecesaria; favorecer composición, interfaces y políticas.

### 5. Quality Tools y CI/CD

Las presentaciones incluyen linters, testing tools, hooks y pipelines como formas de automatizar decisiones de arquitectura y calidad.

Aplicación concreta:

- Mantener `ruff`, `mypy`, `pytest`, `coverage` e `import-linter` como quality gates.
- La arquitectura debe validarse automáticamente con reglas de importación.
- El pipeline debe ejecutar lint, type check, tests e import-linter.
- El proyecto debe poder levantarse con Docker Compose.
- No relajar reglas de calidad sin justificación documentada.

### 6. TDD y Red-Green-Refactor

TDD se presenta como forma de evitar código podrido y reducir miedo al cambio. En este proyecto debe aplicarse principalmente en dominio y aplicación, donde las reglas son más estables y testeables.

Aplicación concreta:

- Primero probar invariantes de `Inspection`, `Observation`, `Evidence` y `Version`.
- Después probar políticas de conflicto y merge.
- Luego probar casos de uso con fakes de puertos.
- Las pruebas de infraestructura y HTTP son necesarias, pero no deben sustituir las pruebas del núcleo.
- Cada ticket funcional debe incluir al menos pruebas unitarias del dominio/aplicación cuando toque reglas.

### 7. Design Patterns como ideas, no recetas

Las presentaciones insisten en que los patrones comunican intención y deben evolucionar con el problema. No deben imponerse si ensucian el diseño.

Aplicación concreta:

- Strategy: políticas de resolución de conflicto (`keep_server`, `keep_client`, `manual_merge`).
- Factory/factory methods: creación válida de agregados y value objects.
- Repository: acceso a agregados sin exponer detalles de SQLAlchemy.
- Unit of Work: transacciones de casos de uso.
- Adapter/Gateway: MinIO, Redis, PostgreSQL, JWT y servicios externos.
- Presenter/Mapper: conversión de salida de casos de uso a respuesta HTTP.
- No introducir patrones por demostración; solo cuando reduzcan acoplamiento o expresen intención.

### 8. SOLID aplicado al proyecto

#### SRP - Single Responsibility Principle

Un módulo debe responder a un solo actor o razón de cambio. En este proyecto:

- El dominio responde a cambios de reglas de inspección y sincronización.
- Los casos de uso responden a cambios de flujo de aplicación.
- Los routers HTTP responden a cambios de contrato de API.
- Los repositorios responden a cambios de persistencia.
- Los gateways responden a cambios de servicios externos.

#### OCP - Open/Closed Principle

El núcleo debe estar cerrado a modificación frecuente y abierto a extensión mediante políticas y puertos.

- Agregar nuevas estrategias de conflicto no debe reescribir `ApplyChangesBatch` completo.
- Agregar otro storage no debe cambiar `AttachEvidence`.
- Cambiar PostgreSQL no debe cambiar el dominio.

#### LSP - Liskov Substitution Principle

Toda implementación concreta de un puerto debe poder sustituirse por otra sin romper el caso de uso.

- Un fake de `InspectionRepository` y el repositorio SQLAlchemy deben cumplir el mismo contrato.
- `FileStorageGateway` local o MinIO deben respetar la misma semántica.
- Las excepciones y resultados esperados deben estar definidos por el puerto.

#### ISP - Interface Segregation Principle

Los clientes no deben depender de métodos que no usan.

- Separar `InspectionRepository`, `ChangeSetRepository`, `ConflictRepository`, `AuditRepository`.
- No crear un `DatabaseGateway` gigante.
- No obligar a `AttachEvidence` a depender de métodos de conflicto o read models.

#### DIP - Dependency Inversion Principle

Los módulos de alto nivel dependen de abstracciones; los detalles implementan esas abstracciones.

- `application/use_cases` depende de `application/ports`.
- `infrastructure` implementa los puertos.
- `interfaces/http` traduce HTTP hacia DTOs/casos de uso.

### 9. DDD y lenguaje ubicuo

La materia recalca que la arquitectura debe representar intención de negocio, no tecnología. El lenguaje del código debe corresponder al dominio.

Lenguaje ubicuo recomendado:

- `Inspection`: agregado raíz.
- `Observation`: hallazgo o nota dentro de una inspección.
- `Evidence`: archivo/metadato asociado a inspección u observación.
- `ChangeSet`: cambio local generado por un cliente offline.
- `SyncBatch`: lote de ChangeSets enviado al backend.
- `ServerDelta`: cambios autoritativos devueltos por el servidor.
- `Conflict`: desacuerdo entre cambio local y estado autoritativo.
- `ConflictResolution`: decisión trazable para resolver un conflicto.
- `AuditTrail`: línea de tiempo de eventos relevantes.
- `ReadModel`: vista optimizada para consulta.

### 10. Boundaries y Scream Architecture

La arquitectura debe gritar el caso de uso, no el framework. Al abrir el repo debe ser claro que el sistema trata de inspecciones offline-first, no solo de FastAPI o SQLAlchemy.

Aplicación concreta en carpetas:

```text
backend/src/
  domain/
    entities/
    value_objects/
    events.py
    policies/
  application/
    use_cases/
    dto/
    ports/
  infrastructure/
    persistence/sqlalchemy/
    storage/
    queue/
    auth/
  interfaces/
    http/
      routers/
      schemas/
      deps.py
    workers/
```

Regla práctica:

- `domain` no conoce `application`.
- `application` no conoce `infrastructure` ni `interfaces`.
- `infrastructure` no conoce `interfaces`.
- `interfaces` puede conocer `application`, pero no debe poner reglas de negocio.

### 11. Domain, Application Domain e Infrastructure

La materia distingue reglas empresariales críticas de reglas de aplicación.

Aplicación concreta:

- Entidad: `Inspection`, `Observation`, `Evidence`, `Version`, `Conflict`.
- Value objects: ids, estado, versión, operación de cambio, estrategia de resolución.
- Use cases: `CreateInspection`, `EditInspection`, `ApplyChangesBatch`, `ResolveConflict`, `AttachEvidence`.
- DTOs: requests/responses de casos de uso, comandos y queries.
- Infrastructure: SQLAlchemy, MinIO, Redis, JWT, Docker.
- Interfaces: routers FastAPI, schemas Pydantic, workers, CLI si aplica.

### 12. Humble Object Pattern

La lógica difícil de probar debe aislarse de frameworks difíciles de probar. En el proyecto:

- FastAPI routers deben ser delgados.
- SQLAlchemy models no deben contener reglas de negocio.
- Pydantic schemas no deben actuar como entidades.
- Los mappers convierten entre DTOs, entidades y modelos externos.
- La mayor cantidad de reglas debe estar en dominio y casos de uso probables con fakes.

### 13. Otras arquitecturas: hexagonal, onion y CQRS

Las presentaciones muestran que Clean Architecture, Hexagonal y Onion comparten la misma idea central: el dominio al centro y los detalles afuera.

Aplicación concreta:

- Usar puertos/adaptadores como en arquitectura hexagonal.
- Mantener dependencias hacia adentro como en onion/clean.
- Aplicar una separación simple de Command/Query:
  - Commands: crear, editar, adjuntar evidencia, aplicar batch, resolver conflicto.
  - Queries: obtener inspección, listar inspecciones, consultar auditoría, consultar read models.
- No implementar CQRS complejo si no aporta al MVP; usarlo como criterio para separar mutaciones de consultas.

## Aplicación a los Issues del proyecto

| Issue | Conceptos de la materia aplicados |
|---|---|
| INS-1 | Scream Architecture, documentación alineada, detalles tecnológicos como detalles |
| INS-2 | DDD, DTOs, boundaries, contrato de sincronización |
| INS-3 | Domain, entidades, value objects, eventos de dominio, Strategy |
| INS-4 | DIP, ISP, puertos, plugin architecture |
| INS-5 | Infrastructure, repositories, Unit of Work, data mappers |
| INS-6 | Use cases, TDD, idempotencia, Big O, OCP |
| INS-7 | Strategy, domain policies, auditoría |
| INS-8 | Controllers, humble object, mappers, boundaries |
| INS-9 | Gateway, adapter, infraestructura como detalle |
| INS-10 | Audit trail, read models, Command/Query separation |
| INS-11 | UI como detalle, cliente mínimo, boundaries |
| INS-12 | Quality tools, CI/CD, tests, lint, architecture enforcement |
| INS-13 | Application business rules, use cases, TDD |
| INS-14 | AuthContext como puerto, JWT como detalle, auditoría por usuario |
| INS-15 | Quality baseline, clean code, miedo al cambio reducido por pruebas |

## Definition of Done global alineada con la materia

Todo ticket funcional debe cumplir, cuando aplique:

- Respeta la regla de dependencias hacia adentro.
- Tiene pruebas unitarias si modifica dominio o application.
- No introduce frameworks en el dominio.
- Usa nombres del lenguaje ubicuo.
- No mezcla entidad y DTO.
- No convierte routers, schemas o modelos ORM en casos de uso.
- Mantiene funciones pequeñas y con responsabilidades claras.
- Pasa `ruff`, `mypy`, `pytest` e `import-linter`.
- Documenta decisiones importantes si cambian límites arquitectónicos.

## Decisión de alcance recomendada para el MVP

Para una entrega defendible, se recomienda priorizar:

1. Backend con Clean Architecture real.
2. Dominio y casos de uso testeados.
3. Sync batch con idempotencia y versionado.
4. Conflicto básico y resolución trazable.
5. API HTTP delgada.
6. Auditoría mínima.
7. Cliente mínimo web o mobile para demo.
8. CI/CD y evidencia de pruebas.

No se recomienda intentar completar un mobile offline-first complejo y un panel web completo al mismo tiempo si el tiempo es limitado. Es preferible una demostración pequeña, correcta y alineada con la materia que una implementación grande con reglas en lugares incorrectos.
