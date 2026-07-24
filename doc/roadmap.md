# Roadmap

## 23 de julio de 2026

### Idea

1. El usuario da de alta su/s *API key/s* en alguno de los 5 **proveedores** con
   los que contamos de base:
   - Anthropic,
   - Nvidia,
   - Ollama,
   - Openai,
   - Together.
2. Cada uno de esos proveedores le habilita a usar una serie de **proveedores**.
   Por ejemplo, no puedes usar Fable sin introducir tu *API key* de Anthropic.
3. El usuario luego tiene una lista de **habilidades**, *skills*, habilitadas
   por defecto, a las que poder sumar las suyas personalizadas y en el futuro
   comprar algunas del marketplace.
4. De modo similar a las *skills*, tendrá una serie de **personas** definidas.
5. Con los modelos, *skills* y personas, el usuario definirá sus **loops**,
   añadiendo un objetivo del *loop* (generación de ideas, desarrollo de código,
   etc) y un rol para cada persona que interviene en él.
6. El usuario entonces podrá definir **pipelines** encadenando *loops* con
   paradas para revisión humana.
7. Tendrá una sección donde poner en marcha *pipelines* (simples, con una única
   *loop*, o múltiples), llamada **ejecuciones**, donde podrá ver cuáles están
   programadas (*cron*), cuáles están en curso, cuáles detenidas, etc.
8. Tendrá una sección de observabilidad viendo quién ha lanzado qué en el equipo.
9. Y una sección de revisión humana donde dar el okay a los avances.

### Tareas

[x] Mover el `/src/app/http` a `/src/app/utils`.

[x] Simplificar la API de proveedores a `GET /providers`,
`GET/PATCH/DELETE /providers/{provider_id}`.

[x] Simplificar la API de modelos a `GET /models`,
`GET /models/{model_id}`.

[x] Simplificar la API de personas a `GET /personas`,
`GET/POST/PATCH/DELETE /personas/{persona_id}`.

[x] Simplificar la API de habilidades a `GET /skills`,
`GET/POST/PATCH/DELETE /skills/{skill_id}`.

[x] Meter `/src/app/skills` y `/src/app/personas` en `/src/app/catalogs`.

[ ] Eliminar el concepto de `Meeting`.



***
