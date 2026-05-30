# Protocolo de Sincronización Offline-first

Este documento define el contrato de comunicación entre los clientes Web/Mobile y
el backend para sincronizar cambios offline del sistema de inspecciones.

El protocolo usa optimistic locking basado en versiones: cada `Inspection`
tiene una versión entera que se incrementa cuando el servidor aplica un cambio
exitosamente.

## 1. Conceptos core

- **Version:** número entero monotónicamente creciente del agregado en servidor.
- **ChangeSet:** intención de cambio atómica generada por un cliente offline.
- **SyncBatch:** lote de `ChangeSet` enviado a `POST /sync/batch`.
- **AppliedChange:** cambio aceptado; incluye la nueva versión del agregado.
- **RejectedChange:** cambio rechazado por conflicto, payload inválido o alcance no soportado.
- **Conflict:** rechazo por mismatch entre `base_version` del cliente y versión actual del servidor.
- **ServerDelta:** estado autoritativo que el cliente debe usar para actualizar su cache local.

## 2. Alcance actual del MVP

En el MVP actual el endpoint de sincronización aplica solamente:

- `entity_type = "inspection"`
- `operation = "update"`
- payload con al menos uno de estos campos: `title`, `location`

Los demás `entity_type` u `operation` se rechazan de forma controlada dentro de
`rejected_changes`. Esto permite mantener el contrato extensible sin fingir que
create/delete u otras entidades ya están implementadas.

## 3. Flujo de sincronización

1. El cliente realiza cambios localmente y genera uno o más `ChangeSet`.
2. Al recuperar conexión, el cliente envía un `SyncBatch` a `POST /sync/batch`.
3. El servidor procesa los cambios en orden:
   - Si el `change_id` ya fue aplicado, devuelve el resultado original sin mutar de nuevo.
   - Si el cambio está fuera del alcance actual, lo rechaza.
   - Si el payload no es válido, lo rechaza.
   - Si la entidad no existe, lo rechaza.
   - Si la versión no coincide, lo rechaza con detalle de conflicto.
   - Si la versión coincide, aplica el cambio, incrementa versión y registra idempotencia.
4. El servidor responde con:
   - `applied_changes`: cambios aplicados o reintentos idempotentes ya aplicados.
   - `rejected_changes`: cambios rechazados y su razón.
   - `server_delta`: estado autoritativo que el cliente debe sincronizar localmente.

## 4. Request: ChangeSet

Representa un cambio individual dentro del lote.

```json
{
  "id": "9f97e27b-7f77-43fb-9c78-7a1d75c15201",
  "entity_id": "2f8f0a5e-6d60-4e3d-a43d-441fe7f8f7db",
  "entity_type": "inspection",
  "operation": "update",
  "base_version": 0,
  "payload": {
    "title": "Título sincronizado",
    "location": "Bodega A"
  },
  "created_at": "2026-05-30T10:00:00Z"
}
```

### Campos

| Campo | Tipo | Requerido | Descripción |
| --- | --- | --- | --- |
| `id` | UUID | Sí | Identificador único generado por el cliente para idempotencia. |
| `entity_id` | UUID | Sí | Identificador de la entidad a mutar. |
| `entity_type` | string | Sí | Actualmente solo `"inspection"`. |
| `operation` | string | Sí | Actualmente solo `"update"`. |
| `base_version` | integer >= 0 | Sí | Versión del agregado que tenía el cliente al crear el cambio. |
| `payload` | object | No | Datos de la mutación. Para `inspection/update`, `title` y/o `location`. |
| `created_at` | ISO datetime | Sí | Fecha de creación del cambio en el cliente. |

## 5. Request: SyncBatch

Lote de cambios enviado por un cliente.

```json
{
  "batch_id": "426f58d8-2e7e-4a1e-9e23-3ecb8dfbd0d7",
  "client_id": "web-client",
  "changes": [
    {
      "id": "9f97e27b-7f77-43fb-9c78-7a1d75c15201",
      "entity_id": "2f8f0a5e-6d60-4e3d-a43d-441fe7f8f7db",
      "entity_type": "inspection",
      "operation": "update",
      "base_version": 0,
      "payload": {
        "title": "Título sincronizado"
      },
      "created_at": "2026-05-30T10:00:00Z"
    }
  ]
}
```

### Campos

| Campo | Tipo | Requerido | Descripción |
| --- | --- | --- | --- |
| `batch_id` | UUID | Sí | Identificador del lote. |
| `client_id` | string | Sí | Identificador del cliente que origina el lote. |
| `changes` | array | Sí | Lista no vacía de `ChangeSet`. |

## 6. Response: SyncResponse

Resultado del procesamiento del lote.

```json
{
  "batch_id": "426f58d8-2e7e-4a1e-9e23-3ecb8dfbd0d7",
  "status": "success",
  "applied_changes": [
    {
      "change_id": "9f97e27b-7f77-43fb-9c78-7a1d75c15201",
      "new_version": 1
    }
  ],
  "rejected_changes": [],
  "server_delta": {
    "inspections": [
      {
        "id": "2f8f0a5e-6d60-4e3d-a43d-441fe7f8f7db",
        "title": "Título sincronizado",
        "location": "Bodega A",
        "status": "draft",
        "version": 1,
        "created_by": "00000000-0000-0000-0000-000000000001",
        "created_at": "2026-05-30T09:00:00",
        "updated_at": "2026-05-30T10:00:00",
        "observations": [],
        "evidences": []
      }
    ]
  }
}
```

### Campos

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `batch_id` | UUID | Identificador del lote procesado. |
| `status` | string | `"success"`, `"partial_success"` o `"conflict"`. |
| `applied_changes` | array | Cambios aplicados; cada item incluye `change_id` y `new_version`. |
| `rejected_changes` | array | Cambios rechazados; cada item incluye `change_id`, `reason` y opcionalmente `conflict`. |
| `server_delta` | object | Estado autoritativo actualizado por entidad. Actualmente contiene `inspections`. |

### Semántica de `status`

- `success`: no hubo rechazos.
- `conflict`: no se aplicó ningún cambio y al menos un cambio fue rechazado por conflicto de versión.
- `partial_success`: hubo uno o más rechazos que no cumplen la condición anterior, con o sin cambios aplicados.

## 7. Response con conflicto de versión

Cuando `base_version` no coincide con la versión actual del servidor, el cambio
se rechaza con `reason = "version_mismatch"` y el detalle del conflicto.

```json
{
  "batch_id": "426f58d8-2e7e-4a1e-9e23-3ecb8dfbd0d7",
  "status": "conflict",
  "applied_changes": [],
  "rejected_changes": [
    {
      "change_id": "9f97e27b-7f77-43fb-9c78-7a1d75c15201",
      "reason": "version_mismatch",
      "conflict": {
        "change_id": "9f97e27b-7f77-43fb-9c78-7a1d75c15201",
        "entity_id": "2f8f0a5e-6d60-4e3d-a43d-441fe7f8f7db",
        "entity_type": "inspection",
        "server_version": 2,
        "client_version": 0,
        "server_state": {
          "id": "2f8f0a5e-6d60-4e3d-a43d-441fe7f8f7db",
          "title": "Título en servidor",
          "location": "Bodega A",
          "status": "draft",
          "version": 2,
          "created_by": "00000000-0000-0000-0000-000000000001",
          "created_at": "2026-05-30T09:00:00",
          "updated_at": "2026-05-30T10:30:00",
          "observations": [],
          "evidences": []
        },
        "reason": "version_mismatch"
      }
    }
  ],
  "server_delta": {
    "inspections": []
  }
}
```

## 8. Razones de rechazo

| Reason | Significado |
| --- | --- |
| `version_mismatch` | La versión base del cliente no coincide con la versión actual del servidor. |
| `unsupported_entity_type` | El tipo de entidad no está soportado por el MVP actual. |
| `unsupported_operation` | La operación no está soportada por el MVP actual. |
| `invalid_payload` | El payload contiene campos con tipo inválido. |
| `empty_update_payload` | El update no contiene ningún campo editable. |
| `entity_not_found` | La entidad indicada por `entity_id` no existe. |

## 9. Idempotencia

Cada `ChangeSet.id` se registra cuando el servidor aplica correctamente un
cambio. Si el cliente reintenta el mismo `ChangeSet`, el servidor no vuelve a
mutar el agregado; devuelve el `AppliedChange` y el `server_delta` originalmente
guardados.

Esto evita duplicar incrementos de versión por reintentos de red.

## 10. Estrategias de resolución

Las estrategias completas de resolución forman parte de INS-7. El protocolo deja
el espacio preparado para que un cliente pueda resolver un conflicto con:

- `keep_server`: descartar cambio cliente y usar estado servidor.
- `keep_client`: reenviar una versión consolidada basada en el estado actual.
- `manual_merge`: presentar al usuario una mezcla manual y enviar un nuevo cambio.

---

Este protocolo es la base para INS-2, INS-6 e INS-8. La versión documentada aquí
refleja el contrato HTTP actual de `POST /sync/batch`.
