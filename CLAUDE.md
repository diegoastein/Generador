# NeoMonitor Expert Suite

Static HTML/CSS/JS web app para generar contenido médico para redes sociales (carruseles de Instagram, Reels, Stories, posts de LinkedIn) relacionado con monitoreo clínico neonatal, pediátrico y adultos.

## Stack

- HTML puro, sin build system, sin framework, sin package.json
- Tailwind CSS vía CDN
- Vanilla JavaScript
- Cada archivo es completamente autocontenido

## Archivos

| Archivo | Módulo | Descripción |
|---|---|---|
| `index.html` | Dashboard | Panel central con los 4 módulos |
| `novedades.html` | Novedades NeoMonitor | Carruseles + Reels/Stories de novedades de producto, con soporte de audio |
| `casosexp.html` | Casos Expandidos | 33 escenarios, posts 1:1 + Reels 9:16 con CTA + audio personalizado |
| `quiz.html` | NeoQuiz Expert | 32 presets clínicos, pack de 5 Stories con respuesta/explicación/CTA |
| `videosinc.html` | Video Sync 9:16 | Sincronización y exportación de video vertical |
| `neoplanner.html` | NeoPlanner | Planificador de publicaciones: vincula biblioteca con fechas/captions/Drive URLs, exporta CSV compatible con Buffer/Later |

## Protocolos clínicos de referencia

- NRP 8ª Edición
- AHA / AAP 2023

## Audio personalizado en Casos Expandidos

En `casosexp.html`, la sección "Música para el Reel" permite:

1. **Subir MP3 local**: Click en el input de archivo para seleccionar un audio de Pixabay, FreePD, Zapsplat, etc.
2. **Guardar como defecto**: Una vez cargado, botón "Guardar como defecto" persiste el audio en localStorage
3. **Cargar automáticamente**: Al reiniciar la página, se carga el audio guardado (marcado con ⭐)
4. **Eliminar defecto**: Botón "Eliminar defecto" limpia el almacenamiento sin perder el audio actual
5. **Limpiar actual**: Botón "Limpiar" quita el audio del session actual sin afectar el guardado

Sin audio guardado, la página inicia sin audio.

## Generación en Batch (Casos Expandidos)

Sección "Generar en Masa" en `casosexp.html` permite generar múltiples casos con IA y exportarlos automáticamente:

1. **Elegir formato**:
   - 📷 **Carruseles**: PNG 1:1 (5 slides por tema)
   - 🎬 **Reels**: MP4 9:16 (35 segundos con audio, compatible Instagram)
   - ✨ **Ambos**: PNG + MP4 en la misma carpeta

2. **Escribir temas**: Uno por línea en el textarea
   ```
   Bradicardia severa en prematuro
   Neumotórax a tensión
   Hipoglucemia grave
   ```

3. **Generar**: Click en "Generar + ZIP"
   - Llama a Claude API (prompts personalizados en servidor)
   - Genera 5 slides renderizados por cada tema
   - Genera reels grabados si está seleccionado (toma ~35s por reel)
   - Comprime en ZIP con estructura de carpetas por tema

4. **ZIP descargado automáticamente** con estructura:
   ```
   NeoMonitor_Batch_YYYY-MM-DD.zip
   ├── bradicardia_severa_en_prematuro/
   │   ├── carruseles/
   │   │   ├── 1_signos_vitales_anormales.png
   │   │   ├── 2_evaluacion_inicial.png
   │   │   ├── 3_manejo_inmediato.png
   │   │   ├── 4_monitoreo_continuo.png
   │   │   └── 5_seguimiento_y_evaluacion.png
   │   └── reels/
   │       └── reel_bradicardia_severa_en_prematuro_9-16.mp4
   ├── neumotorax_a_tension/
   │   └── ...
   ```

**Formatos**:
- **Carruseles**: PNG 1080×1080 (1:1)
- **Reels**: MP4 1080×1920 (H.264 + AAC) o WebM fallback — 9:16, compatible con Instagram

**Nota**: Generación de reels es lenta (35s por reel). Para batch de 10 reels ≈ 6 min.

En Chromebook, los ZIPs se descargan a la carpeta sincronizada con Google Drive automáticamente.

## Biblioteca Local (Casos Expandidos)

Pestaña **📚 Biblioteca** en `casosexp.html` que registra todo el contenido generado:

### Datos guardados por elemento:
- **ID**: timestamp único
- **Título**: del caso
- **Tipo**: Carrusel o Reel
- **Fecha/Hora**: de generación
- **Audio**: nombre del archivo usado (o "Sin audio")
- **Estado**: Borrador / Listo / Publicado (cambiable)
- **Datos del caso**: snapshot completo para regenerar

### Almacenamiento:
- **localStorage** bajo clave `neocontent_library`
- Persiste entre sesiones automáticamente
- Formato: Array de objetos JSON

### Funcionalidades por elemento:
1. **↻ Recargar**: Carga el caso en el editor para regenerar/editar
2. **✕ Borrar**: Elimina de la biblioteca (requiere confirmación)
3. **Estado**: dropdown para marcar Borrador/Listo/Publicado

### Interfaz:
- Grid de cards (responsive: 1 col móvil, 3 cols desktop)
- Contador en tab (`📚 Biblioteca (N)`)
- Mensaje si está vacía

**Nota**: Los datos regenerables (slides, audio) se guardan en el snapshot. El caso se puede recargar idéntico tiempo después.

## Descarga de Carruseles y Reels individuales

### Carruseles (desde "Generar Carrusel 1:1"):
- **Descargar individual**: Click en imagen → descarga PNG nombrado `1_titulo_slide.png`
- **Descargar como ZIP**: Botón "📦 Descargar Carrusel como ZIP"
  - Estructura: `carruseles/1_titulo.png, 2_titulo.png, ...`
  - Nombre: `NeoMonitor_Carrusel_{titulo}_{YYYY-MM-DD}.zip`
  - Se agrega automáticamente a la Biblioteca con estado "Borrador"

### Reels (desde "Exportar Reel 9:16"):
- **Descargar**: Se descarga automático como `NeoMonitor_Reel_{titulo}.mp4`
- Se agrega automáticamente a la Biblioteca con estado "Borrador"

### Ambos:
- **Mismo sistema de nombrado descriptivo** que batch
- **Añadidos a la Biblioteca automáticamente** al exportar
- **Pueden cambiar de estado** desde la Biblioteca
- **Pueden regenerarse** desde la Biblioteca (recarga el caso)

## Servidor Node.js (server.js)

Puerto 8000. Sirve archivos estáticos y proxea llamadas a Claude API.

### Endpoints:
- `POST /api/generate-case` — genera caso clínico neonatal/pediátrico (5 slides con vitales, JSON estructurado)
- `POST /api/generate-novedades` — genera carrusel de novedades de producto NeoMonitor (3–5 slides con title/subtitle/body/tag/palette)

### Cuándo se necesita el servidor:
- **Siempre para generación con IA**: los archivos HTML llaman a `/api/...` (URL relativa). Si se abre el HTML directo con `file://`, esas llamadas fallan con "Failed to fetch".
- **No necesario para descargas**: PNG, ZIP y video son 100% client-side. Funcionan con `file://` o `localhost`.

### Patrón de descarga correcto (todos los módulos):
Usar `canvas.toBlob()` + `URL.createObjectURL()` + `document.body.appendChild(a)` antes de `.click()`. **No usar `canvas.toDataURL()`** para descargas — Chrome moderno puede bloquearlo silenciosamente.

```javascript
const triggerDownload = (url, filename) => {
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
};
// Para canvas:
canvas.toBlob(blob => triggerDownload(URL.createObjectURL(blob), 'archivo.png'), 'image/png');
```

## Biblioteca Local

Cada módulo tiene su propia biblioteca en localStorage:

| Módulo | Clave localStorage |
|---|---|
| Casos Expandidos | `neocontent_library` |
| Novedades | `neonovedades_library` |
| NeoQuiz | `neoquiz_library` |

NeoPlanner lee `neocontent_library` (de Casos Expandidos) y guarda el plan en `neoplanner_plan`.

### Campos comunes por item de biblioteca:
- `id`: timestamp único
- `title`: título del contenido
- `type`: "Carrusel", "Reel", "Video", etc.
- `dateTime`: fecha/hora de generación (string)
- `status`: "Borrador" | "Listo" | "Publicado"
- `slidesData` / datos del caso: snapshot para regenerar

## Novedades (novedades.html)

### Layout 3 columnas:
- **Izquierda (200px)**: lista de slides con orden, agregar/eliminar
- **Centro (420px)**: tabs — "✨ Generar con IA" | "✏️ Editor manual" + acciones de exportación fijas abajo
- **Derecha (flex-1)**: preview canvas (cuando mainTab = 'editor') o biblioteca (cuando mainTab = 'library')

### Generación con IA:
- Requiere servidor corriendo (`localhost:8000`)
- Tab "✨ Generar con IA" → describir novedad → llama a `/api/generate-novedades`
- API key se guarda en localStorage (`claude_api_key`)
- Resultado: 3–5 slides con palette automática, reemplaza slides actuales

### Biblioteca toggle:
- Botón "📚 Biblioteca" en el header alterna `mainTab` entre `'editor'` y `'library'`
- No hay tabs internos en el panel derecho — el header es el único control

## Renderizado de Canvas (casosexp.html)

### Funciones de renderizado:
- **renderSlideToCanvas()**: Genera carruseles 1:1 (1080×1080 PNG)
- **renderReelSlideToCanvas()**: Genera Reels 9:16 (1080×1920 PNG mientras se graba)
- **renderCTASlide()**: CTA 1:1 con botón y llamada a acción
- **renderReelCTASlide()**: CTA 9:16 para Reels

### Especificaciones de fuente y truncado:
- **Fuente**: Arial (siempre disponible en canvas, evita problemas con Inter)
- **Títulos 1:1**: bold 72px, máximo 25 caracteres
- **Títulos 9:16**: bold 96px, máximo 30 caracteres
- **Descripciones 1:1**: 36px, máximo **35 caracteres** + `…`
- **Descripciones 9:16**: 34px, máximo **45 caracteres** + `…`
- **Vitales**: bold 140px (1:1) / 160px (9:16)
- **Footer**: 26px (1:1) / 36px (9:16)

### Nota importante:
- NO usar `wrapText()` — causa cuelgues por intentar medir Inter en canvas
- Truncado basado en **substring(0, N)**, no en `measureText()` — más confiable
- El texto se trunca con `…` al final si es más largo que el límite
- Todos los textos usan `.substring(0, maxChars)` antes de renderizar

## Convenciones

- Al agregar nuevos módulos, seguir el patrón de archivo único autocontenido
- Los formatos de salida son: 1:1 (carruseles/posts) y 9:16 (Reels/Stories)
- Targets: neonatología, pediatría, adultos
- Plataformas: Instagram y LinkedIn
- Canvas: siempre usar Arial, truncado basado en caracteres, nunca measureText en bucle

### Directrices de desarrollo:
1. Think before acting. Read existing files before writing code.
2. Be concise in output but thorough in reasoning.
3. Prefer editing over rewriting whole files.
4. Do not re-read files you have already read unless the file may have changed.
5. Test your code before declaring done.
6. No sycophantic openers or closing fluff.
7. Keep solutions simple and direct.
8. User instructions always override this file.
