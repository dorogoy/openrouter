# Script para listar y filtrar modelos de OpenRouter.ai

Este proyecto descarga la lista de modelos públicos de OpenRouter.ai, extrae los datos principales y muestra en consola una tabla ordenada por el precio input (prompt, por 1K tokens), usando `uv` para la gestión del entorno y dependencias.

---


## ⚡ Uso correcto con `uv`

Con los archivos `pyproject.toml` y `uv.lock` ya presentes en el proyecto, solo necesitas ejecutar el script directamente. `uv` creará el entorno virtual y gestionará las dependencias automáticamente:

```bash
uv run python main.py [opciones de filtrado]
```

**Ejemplo de uso con filtros:**
```bash
uv run python main.py --name=gpt --min-price=0.005 --max-price=0.015
```

---
## Opciones de filtrado disponibles
Puedes acotar la tabla de resultados por los siguientes argumentos opcionales:


- `--name <texto>`
  - Filtra modelos cuyo nombre contenga el texto (insensible a mayúsculas/minúsculas).
- `--provider <texto>`
  - Filtra por proveedor (insensible a mayúsculas/minúsculas).
- `--slug <texto>`
  - Filtra por slug.
- `--min-price <value>`
  - Minimum price (prompt, per 1K tokens).
- `--max-price <value>`
  - Maximum price (prompt, per 1K tokens).
- `--incluir-gratis`
  - Incluye modelos gratuitos en la tabla (por defecto se omiten).

**Notas de ordenación y filtrado:**
- Por defecto, los modelos se ordenan de mayor a menor precio (prompt, por 1K tokens).
- El modelo "Auto Router" no se muestra nunca.
- Los modelos gratuitos solo se muestran si usas `--incluir-gratis`.

Puedes combinar varios filtros a la vez. Por ejemplo:
```bash
uv run python main.py --provider=openai --min-price=0.001 --max-price=0.01
```

---


## Notas
- El filtrado es inclusivo y flexible: solo modelos que cumplan todos los filtros se mostrarán.
- Los modelos sin precio explícito de prompt no aparecerán si usas filtros de precio.
- Puedes adaptar fácilmente el script para añadir más columnas o lógica de filtrado si lo necesitas.

### ⚡ Sobre la caché automática

El script utiliza una caché local automática para evitar descargar la lista de modelos en cada ejecución:

- La caché se almacena en el directorio temporal del sistema y se actualiza automáticamente una vez al día.
- Si ejecutas el script varias veces en el mismo día, solo descargará los datos la primera vez.
- Si hay un error de red, el script usará la última caché disponible (aunque esté desactualizada), mostrando un aviso.
- No necesitas preocuparte por limpiar la caché: se gestiona sola y se sobrescribe cada día.

---

¿Dudas? Abre una issue o pide mejoras por chat con Goose 😃
