# Endpoints

El workspace se resuelve desde el JWT o X-Workspace-ID; no aparece en las rutas.

Para las operaciones comunes se usa esta regla consistente:

/{resource}/list
/{resource}/describe/{id}
/{resource}/create
/{resource}/update/{id}
/{resource}/delete/{id}

Y verbos específicos para operaciones particulares:

/providers/test
/loops/validate
/meetings/run
/runs/cancel

Todas las rutas empiezan por el prefijo: `/api/v1`.

## Providers

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/providers/list` | Lista los proveedores soportados y su estado. |
| `GET` | `/providers/describe/{provider_id}` | Devuelve configuración y estado del proveedor. |
| `POST` | `/providers/configure/{provider_id}` | Guarda o sustituye sus credenciales. |
| `POST` | `/providers/enable/{provider_id}` | Habilita un proveedor configurado. |
| `POST` | `/providers/disable/{provider_id}` | Deshabilita el proveedor sin borrar credenciales. |
| `POST` | `/providers/test/{provider_id}` | Comprueba la conexión y credenciales. |
| `DELETE` | `/providers/delete/{provider_id}` | Elimina las credenciales almacenadas. |

## Models

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/models/list` | Lista el catálogo curado y la disponibilidad de cada modelo. |
| `GET` | `/models/describe/{model_id}` | Devuelve proveedor, capacidades y estado del modelo. |

## Personas

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/personas/list` | Lista personas y metadatos básicos. |
| `GET` | `/personas/describe/{persona_id}` | Devuelve la persona y sus instrucciones completas. |
| `POST` | `/personas/create` | Crea una persona. |
| `POST` | `/personas/update/{persona_id}` | Modifica una persona existente. |
| `DELETE` | `/personas/delete/{persona_id}` | Elimina una persona si no tiene dependencias. |

## Skills

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/skills/list` | Lista skills sin devolver todo su contenido. |
| `GET` | `/skills/describe/{skill_id}` | Devuelve metadatos e instrucciones completas. |
| `POST` | `/skills/create` | Crea una skill. |
| `POST` | `/skills/update/{skill_id}` | Modifica una skill existente. |
| `DELETE` | `/skills/delete/{skill_id}` | Elimina una skill si no está siendo utilizada. |

## Councils

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/councils/list` | Lista los councils guardados. |
| `GET` | `/councils/describe/{council_id}` | Devuelve personas, roles y skills asignadas. |
| `POST` | `/councils/create` | Crea un council. |
| `POST` | `/councils/update/{council_id}` | Modifica sus asignaciones. |
| `DELETE` | `/councils/delete/{council_id}` | Elimina el council si ningún loop lo utiliza. |

## Loops

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/loops/list` | Lista los loops y si actualmente son ejecutables. |
| `GET` | `/loops/describe/{loop_id}` | Devuelve council, modelos e iteraciones configuradas. |
| `POST` | `/loops/create` | Crea un loop. |
| `POST` | `/loops/update/{loop_id}` | Modifica council, modelos o iteraciones. |
| `DELETE` | `/loops/delete/{loop_id}` | Elimina el loop sin borrar runs históricos. |
| `POST` | `/loops/validate/{loop_id}` | Comprueba que council, roles y modelos son válidos. |

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
