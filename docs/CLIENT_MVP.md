# Cliente web MVP

Este documento describe el cliente minimo de demostracion agregado para INS-11.

## Alcance

- Cliente web en `web/` con React + Vite.
- Autenticacion contra `POST /auth/login`.
- Listado de inspecciones desde `GET /inspections`.
- Creacion de inspecciones con `POST /inspections`.
- Edicion local de inspecciones mediante una cola persistida en `localStorage`.
- Sincronizacion de cambios pendientes contra `POST /sync/batch`.
- Visualizacion de estados `pending`, `applied`, `rejected` y `conflict`.
- Boton de cambio remoto para provocar un conflicto de version durante la demo.

El cliente consume contratos HTTP del backend. No conoce entidades internas, repositorios,
Unit of Work ni reglas de dominio.

## Fuera de alcance

- Flutter/mobile queda fuera del MVP y se mantiene como extension futura.
- No se implementa Service Worker, IndexedDB ni cache offline completo.
- La creacion de inspecciones se hace en linea con `POST /inspections`; la cola local del
  MVP cubre ediciones `inspection/update`, que es el contrato soportado actualmente por
  `POST /sync/batch`.
- No hay resolucion interactiva de conflictos en el cliente; se muestra el estado servidor
  devuelto por el backend.
- No se incluye carga de evidencias desde el cliente web.
- No es un panel administrativo completo.

## Ejecucion con Docker

```bash
cp .env.example .env
make up
make migrate
make seed
```

Servicios principales:

- API: <http://localhost:8000/docs>
- Web: <http://localhost:5173>

Credenciales seed:

- Usuario: `admin@inspections.local`
- Contrasena: `change-me`

## Ejecucion local del cliente

```bash
cd web
npm install
npm run dev
```

La URL del backend se configura con:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Pruebas y build

```bash
cd web
npm test -- --coverage
npm run build
```

Tambien puede ejecutarse desde la raiz con:

```bash
make test-web
```

## Verificacion manual sugerida

1. Levantar backend, migrar y sembrar datos.
2. Entrar al cliente web con el usuario seed.
3. Crear una inspeccion.
4. Seleccionar la inspeccion, cambiar titulo o ubicacion y usar `Guardar local`.
5. Confirmar que aparece un cambio `pending` en la cola.
6. Usar `Sincronizar` y confirmar que el cambio queda `applied`.
7. Para demostrar conflicto:
   - Seleccionar una inspeccion sin cambios pendientes.
   - Usar `Cambio servidor`.
   - Sin refrescar, editar localmente y guardar en cola.
   - Usar `Sincronizar`.
   - Confirmar que la cola muestra `conflict` con el estado autoritativo del servidor.

## Decisiones tecnicas

- La cola se concentra en `web/src/sync/queue.ts` como funciones puras testeables.
- La UI mantiene formularios y estados de pantalla, pero no decide reglas de versionado.
- El cliente no inventa operaciones que el backend todavia no soporta; por eso el batch
  enviado usa `entity_type = "inspection"` y `operation = "update"`.
- `localStorage` es suficiente para una demo academica y evita introducir infraestructura
  de cliente antes de validar el flujo principal.
