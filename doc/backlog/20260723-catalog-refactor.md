# Refactor

## Resumen

La arquitectura ha quedado con una separación clara entre catálogo empaquetado, persistencia y runtime.

### Catálogo estático

`src/app/catalogs` es la fuente versionada en Git de:

- Los cinco proveedores soportados.
- Modelos y deployments por proveedor.
- Skills builtin.
- Personas builtin.

Skills y personas tienen un `registry.json` con identidad, versión y metadata, y un Markdown con las instrucciones. Los IDs son estables, por ejemplo:

```text
builtin:skill:security
builtin:persona:tech_lead
```

### Bootstrap y SQL

El arranque sigue este orden:

```text
migraciones
→ validación del catálogo empaquetado
→ sincronización de builtins en SQL
→ creación del tenant local
→ construcción de servicios
```

La sincronización es transaccional e idempotente:

- Inserta nuevas builtins.
- Actualiza las que cambian de versión.
- Marca como deprecadas las retiradas.
- Nunca elimina builtins físicamente.
- Nunca modifica instrucciones custom.

Si el catálogo es inválido o no puede sincronizarse, la aplicación no termina de arrancar.

### Fuente operativa única

Después del bootstrap, SQL es la única fuente utilizada por:

- La API.
- Loops y councils.
- Planificadores.
- Tasks y meetings.
- Reviewers.
- Construcción de prompts.

Los Markdown no se leen durante las ejecuciones. Modificar un Markdown requiere reiniciar y sincronizar; modificar SQL afecta a las ejecuciones nuevas.

### Biblioteca efectiva por workspace

Cada workspace ve:

- Builtins globales.
- Sus propias instrucciones custom.
- En el futuro, contenido marketplace autorizado.

La habilitación se resuelve así:

```text
setting explícito del workspace
→ enabled_by_default
```

Las builtins pueden habilitarse, deshabilitarse o duplicarse, pero no editarse ni borrarse. Al duplicarlas se crea una custom editable con nuevo UUID y `source_instruction_id`.

Las custom siempre pertenecen a un workspace y no son visibles desde otros.

### Referencias y loops

Loops y councils utilizan la misma biblioteca efectiva que la API.

Para nuevas referencias, una instrucción debe:

- Existir.
- Ser visible para el workspace.
- Estar habilitada.
- No estar deprecada.

Las referencias históricas sí pueden resolver instrucciones deshabilitadas o deprecadas. Las dependencias continúan protegiendo el borrado de custom utilizadas.

### Ejecuciones reproducibles

Al iniciar un task o meeting se guarda:

```text
instructions-snapshot.json
```

Incluye IDs, tipo, origen, versiones, contenido efectivo y metadata de la biblioteca presentada al planner. La ejecución conserva ese snapshot en memoria y no vuelve a consultar las definiciones.

Por eso una ejecución histórica sigue siendo interpretable aunque posteriormente cambie el catálogo o SQL.

### Proveedores y modelos

Los proveedores tienen identidad centralizada y los modelos se relacionan exclusivamente mediante deployments. Un mismo modelo puede estar disponible desde varios proveedores.

El número de modelos de cada proveedor se calcula desde esos deployments. NVIDIA y Ollama existen como proveedores configurables, pero actualmente declaran explícitamente que no tienen deployments curados.

### Mantenimiento

Para cambiar una builtin:

- Se modifica su manifest o Markdown.
- Se incrementa `version`.
- Se ejecuta `make catalog-check`.
- El siguiente bootstrap la sincroniza.

En producción conviene activar:

```text
LOUIE_CATALOG_STRICT_VERSIONING=true
```

Así, un cambio de checksum sin incremento de versión impide el arranque.

El procedimiento completo está en [builtin-instruction-catalog.md](/home/jadraque/Documents/source/looping-louie/api/doc/builtin-instruction-catalog.md), y la visión general en [architecture.md](/home/jadraque/Documents/source/looping-louie/api/doc/architecture.md). La suite final quedó en **230 pruebas superadas**.

***

## Commits

### 1. Definir el contrato del catálogo

Crear los tipos compartidos y fijar las decisiones de dominio antes de mover datos.

Cambios:

- Crear `src/app/catalogs/instructions.py`.
- Definir:
  - `InstructionOrigin`: `builtin`, `custom`, `marketplace`.
  - `CatalogInstructionType`: `skill`, `persona`.
  - `SkillCatalogEntry`.
  - `PersonaCatalogEntry`.
  - Roles y metadatos comunes.
- Establecer IDs estables:
  - `builtin:skill:security`.
  - `builtin:persona:tech_lead`.
- Definir la semántica de:
  - `enabled_by_default`.
  - `catalog_version`.
  - `deprecated`.
  - `source_instruction_id`.

Criterios de aceptación:

- Los tipos no dependen de servicios, SQLite ni FastAPI.
- Está documentado que las builtins son inmutables desde la API.
- Custom y marketplace pueden compartir la infraestructura sin confundirse con builtins.

---

### 2. Centralizar el catálogo de proveedores

Mover las definiciones estáticas fuera de `ProviderService`.

Cambios:

- Crear `src/app/catalogs/providers.py`.
- Mover allí:
  - `ProviderId`.
  - `ProviderCatalogEntry`.
  - Los cinco proveedores.
  - `PROVIDER_CATALOG`.
  - `PROVIDER_CATALOG_BY_ID`.
- Hacer que `catalogs/models.py` importe `ProviderId`.
- Inyectar el catálogo en `ProviderService`.
- Adaptar `ProviderStateRepositoryAdapter`.

Criterios de aceptación:

- `ProviderService` no contiene constantes de catálogo.
- No existen strings duplicados para identificar proveedores.
- Los endpoints de proveedores siguen devolviendo lo mismo.

---

### 3. Consolidar el catálogo de modelos

Ajustar el catálogo existente para que dependa del nuevo catálogo de proveedores.

Cambios:

- Validar que cada `ModelDeployment.provider_id` exista.
- Crear una validación de IDs de modelo y deployments duplicados.
- Añadir deployments curados para NVIDIA y Ollama, o documentar explícitamente que todavía tienen catálogo vacío.
- Mantener la relación proveedor-modelo exclusivamente mediante `ModelDeployment`.
- Eliminar cualquier configuración antigua de conteos estáticos que ya no sea utilizada.

Criterios de aceptación:

- Un modelo puede estar disponible mediante varios proveedores.
- El número de modelos de un proveedor se calcula desde deployments.
- Ningún modelo referencia un proveedor inexistente.
- NVIDIA y Ollama no aparecen accidentalmente como configurados pero sin explicación de catálogo.

---

### 4. Reorganizar físicamente skills y personas

Mover los recursos versionados bajo `catalogs`.

Estructura objetivo:

```text
src/app/catalogs/
├── skills/
│   ├── loader.py
│   ├── registry.json
│   └── content/
└── personas/
    ├── loader.py
    ├── registry.json
    └── content/
```

Cambios:

- Mover todos los Markdown.
- Mover los dos `registry.json`.
- Añadir `content_path` explícito a cada entrada.
- Añadir a cada entrada:
  - `id` estable.
  - `name`.
  - `version`.
  - `enabled_by_default`.
  - Metadatos específicos.
- Eliminar metadatos duplicados del front matter cuando ya estén en el manifest.
- Mantener temporalmente wrappers de importación para no romper el runtime durante las tareas intermedias.

Criterios de aceptación:

- Cada entrada del manifest resuelve exactamente un Markdown.
- No se buscan archivos recursivamente por nombre.
- No hay IDs, nombres o rutas duplicadas.
- Los wrappers están marcados como temporales.

---

### 5. Implementar y validar los loaders del catálogo

Construir loaders que devuelvan objetos tipados, no diccionarios ni texto suelto.

Cambios:

- Implementar:
  - `load_skill_catalog()`.
  - `load_persona_catalog()`.
  - `load_instruction_catalog()`.
- Validar:
  - JSON correcto.
  - Campos obligatorios.
  - Archivos existentes.
  - IDs únicos.
  - Versiones positivas.
  - Roles válidos.
  - Rangos de strictness.
  - `skill_ids` existentes.
  - IDs coherentes entre manifest y contenido.
- Calcular un checksum determinista del contenido y metadatos.

Criterios de aceptación:

- Un catálogo inválido impide arrancar con un error explicativo.
- Los loaders devuelven entradas inmutables.
- Las referencias entre personas y skills se validan conjuntamente.
- El checksum cambia al modificar contenido o metadatos relevantes.

---

### 6. Crear la migración del nuevo modelo SQL

Transformar `instructions` para admitir definiciones globales y personalizadas.

Esquema objetivo aproximado:

```text
instructions
├── id
├── instruction_type
├── origin
├── owner_workspace_id
├── source_instruction_id
├── name
├── name_key
├── description
├── content
├── metadata_json
├── catalog_version
├── checksum
├── enabled_by_default
├── deprecated
├── version
├── created_at
└── updated_at
```

Y:

```text
workspace_instruction_settings
├── workspace_id
├── instruction_id
├── enabled
├── created_at
└── updated_at
```

Cambios:

- Crear migraciones SQLite y PostgreSQL.
- Reconstruir `instructions`, porque el `workspace_id` actual es obligatorio.
- Migrar los registros existentes como:
  - `origin = custom`.
  - `owner_workspace_id = workspace_id`.
- Añadir índices únicos parciales:
  - Builtins únicas globalmente por tipo y nombre.
  - Custom únicas por workspace, tipo y nombre.
- Añadir checks para origen, booleanos y versiones.
- Añadir la tabla de settings.

Criterios de aceptación:

- Los datos custom existentes se conservan.
- Una builtin puede tener `owner_workspace_id = NULL`.
- Una custom siempre tiene propietario.
- Las settings no duplican contenido.
- Las migraciones funcionan sobre base vacía y sobre una base con datos existentes.

---

### 7. Implementar el sincronizador del catálogo

Crear un servicio de bootstrap que materialice los catálogos en SQL.

Cambios:

- Crear `CatalogSeeder` o `InstructionCatalogSynchronizer`.
- Ejecutar la sincronización en una única transacción.
- Para cada builtin:
  - Insertar si no existe.
  - Actualizar si aumentó la versión o cambió el checksum.
  - Mantener el ID estable.
- Marcar como deprecadas las entradas retiradas.
- Nunca borrar físicamente una builtin.
- Registrar errores de versión:
  - No aceptar que el manifest reduzca `catalog_version`.
  - Detectar mismo número de versión con checksum diferente, según la política elegida.

Política recomendada:

- Durante desarrollo, permitir mismo número con checksum distinto mostrando advertencia.
- En producción, exigir incremento de `catalog_version`.

Criterios de aceptación:

- Ejecutar el sincronizador varias veces es idempotente.
- No genera duplicados.
- No modifica registros custom.
- Una builtin retirada queda deprecada.
- Un fallo revierte toda la transacción.

---

### 8. Integrar el sincronizador en el bootstrap

Convertir la carga del catálogo en una parte formal del arranque.

Orden:

```text
run migrations
    ↓
load and validate packaged catalog
    ↓
synchronize catalog into SQL
    ↓
ensure local tenant
    ↓
construct repositories and services
```

Cambios:

- Integrar el sincronizador en `configure_application`.
- Eliminar la dependencia operativa de `LOUIE_BUILTIN_SKILLS_PATH`.
- Permitir inyectar un catálogo alternativo en tests.
- Exponer métricas o logs básicos:
  - Insertados.
  - Actualizados.
  - Sin cambios.
  - Deprecados.

Criterios de aceptación:

- Tras levantar una base vacía, SQL contiene todas las skills y personas builtin.
- Reiniciar la aplicación no cambia innecesariamente registros.
- La aplicación no construye sus servicios si el catálogo no pudo sincronizarse.

---

### 9. Adaptar el repositorio de instrucciones

Hacer que SQL pueda devolver la biblioteca efectiva del workspace.

Cambios:

- Adaptar `SqliteInstructionRepository`.
- Añadir operaciones:
  - `list_available_for_workspace`.
  - `get_available_for_workspace`.
  - `get_owned_custom`.
  - `set_enabled`.
  - `is_enabled`.
- La lectura efectiva debe incluir:
  - Builtins globales.
  - Custom del workspace.
  - Marketplace autorizado en el futuro.
- Resolver `enabled` así:
  - Setting explícito del workspace.
  - Si no existe, `enabled_by_default`.
- Excluir deprecadas por defecto, con opción para resolver referencias históricas.
- Implementar correctamente búsqueda y ordenación sobre el conjunto efectivo.

Criterios de aceptación:

- Un workspace ve builtins y sus custom.
- No ve custom de otro workspace.
- Puede describir una builtin por ID.
- Una builtin deshabilitada puede consultarse, pero no seleccionarse para un loop nuevo.
- Las referencias históricas pueden seguir resolviendo una builtin deprecada.

---

### 10. Separar lectura, mutación y habilitación en servicios

Actualizar `InstructionService`, `SkillService` y `PersonaService`.

Cambios:

- La lectura usa la biblioteca efectiva.
- `create` genera siempre `origin=custom`.
- `update` y `delete` sólo funcionan con instrucciones custom propiedad del workspace.
- Añadir:
  - `enable`.
  - `disable`.
  - `duplicate` o `fork`.
- `duplicate` crea una custom con:
  - Nuevo UUID.
  - `source_instruction_id`.
  - Copia inicial de contenido y metadatos.
- Añadir errores específicos:
  - `BuiltinInstructionImmutableError`.
  - `InstructionDisabledError`.
  - `InstructionNotOwnedError`.

Criterios de aceptación:

- No se puede editar ni borrar una builtin.
- Se puede habilitar o deshabilitar.
- Se puede duplicar y editar la copia.
- Las restricciones funcionan igual para skills y personas.
- El control de versión optimista sigue funcionando en custom.

---

### 11. Actualizar contratos y endpoints de API

Mostrar a la UI la procedencia y capacidades de cada instrucción.

Añadir a respuestas:

```json
{
  "origin": "builtin",
  "enabled": true,
  "editable": false,
  "duplicable": true,
  "deprecated": false,
  "catalog_version": 2,
  "source_instruction_id": null
}
```

Cambios:

- Actualizar schemas de skill y persona.
- Añadir endpoints de habilitación:
  - `PUT /skills/{id}/enabled`.
  - `PUT /personas/{id}/enabled`.
- Añadir duplicación:
  - `POST /skills/{id}/duplicate`.
  - `POST /personas/{id}/duplicate`.
- Mantener CRUD para custom.
- Adaptar controllers y manejo de errores.

Criterios de aceptación:

- La UI puede distinguir builtin, custom y marketplace.
- La UI sabe qué acciones están permitidas.
- Las listas incluyen el estado efectivo del workspace.
- No se expone `owner_workspace_id` de otros workspaces.

---

### 12. Unificar la resolución de referencias

Hacer que loops y councils utilicen la misma biblioteca que la API.

Cambios:

- Adaptar `CompositeReferenceRepository`.
- Resolver `skill` y `persona` mediante el repositorio efectivo.
- Validar al crear o actualizar un loop:
  - La instrucción existe.
  - Es visible para el workspace.
  - Está habilitada.
  - No está deprecada para nuevos usos.
- Mantener una vía de resolución histórica que admita deprecadas.
- Revisar `resource_dependencies` para que funcione con IDs builtin globales.

Criterios de aceptación:

- Un loop puede referenciar builtins y custom.
- Un loop no puede usar instrucciones deshabilitadas.
- Un workspace no puede referenciar custom de otro.
- Deshabilitar una instrucción no destruye loops existentes.
- El borrado de una custom sigue respetando dependencias.

---

### 13. Eliminar las lecturas directas de Markdown del runtime

Esta tarea completa realmente la unificación.

Cambios:

- Convertir `build_assignment_instructions` en una función pura que reciba contenido ya resuelto.
- Adaptar:
  - Execution planner.
  - Meeting planner.
  - Meeting team.
  - Reviewers.
  - Task runtime.
- Resolver skills y personas desde SQL antes de ensamblar prompts.
- Eliminar imports de:
  - `src.app.skills`.
  - `src.app.personas`.
- Eliminar los wrappers temporales.
- Evitar que servicios de ejecución conozcan rutas del filesystem.

Criterios de aceptación:

- `rg "src\\.app\\.(skills|personas)" src` no devuelve imports operativos.
- Modificar un Markdown sin reiniciar/sincronizar no afecta a una ejecución.
- Modificar SQL sí afecta a las lecturas posteriores.
- Una custom creada desde la API se puede usar inmediatamente en una ejecución.

---

### 14. Añadir snapshots, pruebas finales y limpieza

Cerrar reproducibilidad y eliminar restos del sistema antiguo.

Cambios de snapshot:

- Al iniciar una ejecución, guardar:
  - ID.
  - Tipo.
  - Origen.
  - Versión.
  - `catalog_version`.
  - Contenido efectivo.
  - Metadata relevante.
- No volver a consultar la definición durante esa ejecución.

Pruebas necesarias:

- Integridad de proveedores y modelos.
- Integridad de manifests.
- Sincronización inicial.
- Sincronización idempotente.
- Actualización de builtin.
- Deprecación.
- Migración de custom existentes.
- Aislamiento entre workspaces.
- Defaults de habilitación.
- Override de habilitación.
- Inmutabilidad builtin.
- Duplicación a custom.
- Resolución desde loops.
- Ejecución con builtin y custom.
- Snapshot reproducible.
- Bootstrap completo.

Limpieza:

- Eliminar `src/app/skills`.
- Eliminar `src/app/personas`.
- Eliminar loaders y settings obsoletos.
- Actualizar documentación de arquitectura.
- Documentar cómo añadir o actualizar una builtin.
- Añadir una comprobación de catálogo a CI.

Criterios de aceptación:

- API y runtime sólo leen instrucciones desde SQL.
- Los `.md` sólo son leídos por el sincronizador durante el arranque.
- La suite completa pasa.
- No quedan dos fuentes operativas.
- Una ejecución histórica sigue siendo interpretable tras actualizar el catálogo.

### División recomendada en PRs

Para mantener el repositorio funcional durante el proceso:

1. **PR 1:** tareas 1–3: contratos, proveedores y modelos.
2. **PR 2:** tareas 4–5: estructura y loaders de skills/personas.
3. **PR 3:** tareas 6–8: migración, sincronizador y bootstrap.
4. **PR 4:** tareas 9–11: repositorios, servicios y API.
5. **PR 5:** tareas 12–13: loops, referencias y runtime.
6. **PR 6:** tarea 14: snapshots, limpieza, documentación y pruebas completas.

El hito decisivo es el PR 5: hasta entonces pueden existir wrappers transitorios; una vez terminado, SQL pasa a ser definitivamente la única fuente operativa.
