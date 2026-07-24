# Endpoints

El workspace se resuelve desde el JWT o X-Workspace-ID; no aparece en las rutas.

Los recursos ya migrados usan rutas REST de colección y elemento. Otros
recursos conservan temporalmente estas rutas de acción:

/{resource}/list
/{resource}/describe/{id}
/{resource}/create
/{resource}/update/{id}
/{resource}/delete/{id}

Y verbos específicos para operaciones particulares:

/meetings/run
/runs/cancel

Todas las rutas empiezan por el prefijo: `/api/v1`.

## Providers

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/providers` | Lista los proveedores del catálogo y su estado. |
| `GET` | `/providers/{provider_id}` | Devuelve configuración y estado del proveedor. |
| `PATCH` | `/providers/{provider_id}` | Configura credenciales, URL o estado habilitado. |
| `DELETE` | `/providers/{provider_id}` | Elimina la configuración del workspace. |

## Models

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/models` | Lista el catálogo curado y la disponibilidad de cada modelo. |
| `GET` | `/models/{model_id}` | Devuelve proveedor, capacidades y estado del modelo. |

## Personas

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/personas` | Lista personas y metadatos básicos. |
| `GET` | `/personas/{persona_id}` | Devuelve la persona y sus instrucciones completas. |
| `POST` | `/personas` | Crea una persona directamente o desde `source_persona_id`. |
| `PATCH` | `/personas/{persona_id}` | Modifica contenido o el estado `enabled`. |
| `DELETE` | `/personas/{persona_id}` | Elimina una persona si no tiene dependencias. |

## Skills

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/skills` | Lista skills sin devolver todo su contenido. |
| `GET` | `/skills/{skill_id}` | Devuelve metadatos e instrucciones completas. |
| `POST` | `/skills` | Crea una skill directamente o desde `source_skill_id`. |
| `PATCH` | `/skills/{skill_id}` | Modifica contenido o el estado `enabled`. |
| `DELETE` | `/skills/{skill_id}` | Elimina una skill si no está siendo utilizada. |

## Loops

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/loops` | Lista diez definiciones desde el `offset` indicado. |
| `POST` | `/loops` | Crea un loop activo. |
| `GET` | `/loops/{loop_id}` | Devuelve la definición completa. |
| `PATCH` | `/loops/{loop_id}` | Modifica campos o estado. |
| `DELETE` | `/loops/{loop_id}` | Elimina la definición y conserva su changelog. |
| `GET` | `/loops/{loop_id}/changelog` | Lista diez cambios desde el `offset` indicado. |

## Meetings

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `POST` | `/meeting/run` | Ejecuta una reunión usando un prompt, tipo y loop. |

Tipos iniciales:

- shape_idea
- plan_implementation

## Workflows

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `POST` | `/workflow/run` | Ejecuta una lista de tareas usando un loop. |

## Runs

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/runs/list` | Lista ejecuciones con filtros por estado, tipo o loop. |
| `GET` | `/runs/describe/{run_id}` | Devuelve estado, configuración, métricas y resultado. |
| `POST` | `/runs/cancel/{run_id}` | Solicita la cancelación de un run activo. |
| `GET` | `/runs/events/list/{run_id}` | Lista iteraciones, retries y eventos. |
| `GET` | `/runs/artifacts/list/{run_id}` | Lista los artefactos generados. |
| `GET` | `/runs/artifacts/describe/{artifact_id}` | Devuelve un artefacto concreto. |
