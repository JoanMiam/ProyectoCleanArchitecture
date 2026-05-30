# Protocolo de Sincronización Offline-first

Este documento define el contrato de comunicación entre los clientes (Web/Mobile) y el Backend para el sistema de inspecciones. El objetivo es permitir el trabajo sin conexión y la resolución de conflictos mediante un modelo de **Optimistic Locking** basado en versiones.

## 1. Conceptos Core

- **Version:** Cada Agregado (`Inspection`) tiene un número de versión entero que se incrementa en cada cambio exitoso en el servidor.
- **ChangeSet:** Representa una intención de cambio atómica generada por el cliente (ej. "Crear observación X en Inspección Y").
- **SyncBatch:** Un conjunto de `ChangeSet` que el cliente envía al servidor en una sola petición.
- **Conflict:** Ocurre cuando un `ChangeSet` tiene una `base_version` inferior a la `current_version` en el servidor.

## 2. Flujo de Sincronización

1. **Local Action:** El cliente realiza cambios localmente, los guarda en su DB local (IndexedDB/SQLite) y genera `ChangeSets`.
2. **Push Batch:** Al recuperar conexión, el cliente envía un `SyncBatch` vía `POST /sync/batch`.
3. **Server Processing:** El servidor procesa cada `ChangeSet` en orden.
   - Si la versión coincide: Aplica el cambio e incrementa la versión.
   - Si no coincide: Genera un `Conflict`.
4. **Server Response:** El servidor responde con un `SyncResponse` que contiene:
   - `accepted_ids`: IDs de los ChangeSets aplicados con éxito.
   - `conflicts`: Lista de conflictos detectados.
   - `server_delta`: Versiones autoritativas de las entidades que el cliente debe actualizar.

## 3. Especificación de Objetos (JSON)

### ChangeSet
Representa un cambio individual.
```json
{
  "id": "uuid-del-cambio-local",
  "entity_id": "uuid-de-la-inspeccion",
  "entity_type": "inspection",
  "operation": "create | update | delete",
  "base_version": 0,
  "payload": { ... },
  "created_at": "2026-05-29T10:00:00Z"
}
```

### SyncBatch
Lote de cambios.
```json
{
  "batch_id": "uuid-del-lote",
  "changes": [
    { "id": "c1", ... },
    { "id": "c2", ... }
  ]
}
```

### SyncResponse
Resultado de la operación.
```json
{
  "batch_id": "uuid-del-lote",
  "status": "success | partial_success | conflict",
  "accepted_ids": ["c1"],
  "conflicts": [
    {
      "change_id": "c2",
      "reason": "version_mismatch",
      "server_version": 5,
      "client_version": 4,
      "conflict_type": "concurrent_modification",
      "server_state": { ... }
    }
  ],
  "server_delta": {
    "inspections": [
       { "id": "uuid", "version": 5, ... }
    ]
  }
}
```

## 4. Estrategias de Resolución (INS-7)
El protocolo soporta tres estrategias que se definirán en la lógica de negocio:
- `keep_server`: Descartar cambio cliente, usar estado servidor.
- `keep_client`: Forzar el cambio del cliente sobre el servidor (incrementando versión).
- `manual_merge`: El cliente debe presentar una nueva versión consolidada.

---
*Este protocolo es la base para INS-2, INS-6 y INS-8.*
