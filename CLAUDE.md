# NeoMonitor Expert Suite

Static HTML/CSS/JS web app para generar contenido médico para redes sociales (carruseles de Instagram, Reels, Stories, posts de LinkedIn) relacionado con monitoreo clínico neonatal, pediátrico y adultos.

## Stack

- HTML puro, sin build system, sin framework, sin package.json
- Tailwind CSS vía CDN
- Vanilla JavaScript
- Cada archivo es completamente autocontenido
- Todos los módulos son **responsive** (mobile-first): breakpoints `sm:`, `md:`, `lg:` de Tailwind

## Archivos

| Archivo | Módulo | Descripción |
|---|---|---|
| `index.html` | Dashboard | Panel central con los 5 módulos |
| `novedades.html` | Novedades NeoMonitor | Carruseles + Reels/Stories de novedades de producto, con soporte de audio |
| `casosexp.html` | Casos Expandidos | 33 escenarios, posts 1:1 + Reels 9:16 con CTA + audio personalizado |
| `quiz.html` | NeoQuiz Expert | 32 presets clínicos + generación IA + batch, pack de 5 Stories 9:16 con respuesta/explicación/CTA |
| `videosinc.html` | Video Sync 9:16 | Sincronización y exportación de video vertical |
| `neoplanner.html` | NeoPlanner | Planificador unificado: agrega las 3 bibliotecas, asigna fechas/captions, exporta CSV para Buffer/Later |

## Protocolos clínicos de referencia

- NRP 8ª Edición
- AHA / AAP 2023

## Branding

- Nombre: **NeoMonitor** (sin "Expert Suite", sin "Suite")
- Web: **www.neomonitor.pro**
- Canvas de todos los módulos usa "NeoMonitor" o "NEOMONITOR" — nunca "Expert Suite"
- El logo NM no se renderiza en los slides del canvas (fue eliminado de quiz.html)

## Captions automáticos

Todos los módulos generan un caption automático al guardar en biblioteca:

- **Casos Expandidos**: `🏥 {título}. Escenario clínico de reanimación... #rcp #educacionmedica #neonatologia #nrp #reanimacion #pediatria #neomonitor`
- **NeoQuiz**: `🧠 {título}. ¿Podés resolver este desafío?... #rcp #educacionmedica #quiz #neonatologia #nrp #reanimacion #pediatria #neomonitor`
- **Novedades**: `✨ {título}. Conocé las novedades en www.neomonitor.pro... #neomonitor #novedades #neonatologia #educacionmedica #pediatria #tecnologiamedica`

El caption se muestra en la card de biblioteca con botón "📋 Copiar".

## Servidor Node.js (server.js)

Puerto 8000. Sirve archivos estáticos y proxea llamadas a Claude API.

### Endpoints:
- `POST /api/generate-case` — genera caso clínico neonatal/pediátrico (5 slides con vitales, JSON estructurado)
- `POST /api/generate-novedades` — genera carrusel de novedades (3–5 slides con title/subtitle/body/tag/palette)
- `POST /api/generate-quiz` — genera quiz clínico crítico de reanimación (title/caseText/question/options[3]/answer/explanation)

### Cuándo se necesita el servidor:
- **Siempre para generación con IA**: los archivos HTML llaman a `/api/...` (URL relativa). Si se abre el HTML directo con `file://`, esas llamadas fallan con "Failed to fetch".
- **No necesario para descargas**: PNG, ZIP y video son 100% client-side.

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
canvas.toBlob(blob => triggerDownload(URL.createObjectURL(blob), 'archivo.png'), 'image/png');
```

## Biblioteca Local

Cada módulo tiene su propia biblioteca en localStorage:

| Módulo | Clave localStorage |
|---|---|
| Casos Expandidos | `neocontent_library` |
| Novedades | `neonovedades_library` |
| NeoQuiz | `neoquiz_library` |
| NeoPlanner (plan) | `neoplanner_plan` |

### Campos comunes por item de biblioteca:
- `id`: timestamp único
- `title`: título del contenido
- `type`: "Carrusel" | "Reel" | "Video" | "Quiz Pack"
- `dateTime`: fecha/hora de generación (string)
- `status`: "Borrador" | "Listo" | "Publicado"
- `caption`: texto auto-generado con hashtags (editable en NeoPlanner)
- datos del contenido: `scenarioData` (casos) | `quizData` (quiz) | `slidesData` (novedades)

## NeoPlanner (neoplanner.html)

Agrega las 3 bibliotecas en una vista unificada para planificar publicaciones.

- Lee `neocontent_library` + `neoquiz_library` + `neonovedades_library`, ordenadas por fecha desc
- Badge de fuente por item: **Casos** / **Quiz** / **Novedades**
- Caption pre-cargado desde el campo `caption` del item (editable)
- Filtros: Todos / Sin programar / Con fecha / Casos / Quiz / Novedades
- Asignar fecha y hora a cada publicación
- Los archivos generados se descargan a la carpeta de Google Drive sincronizada (Chromebook)
- Exportar CSV compatible con Buffer / Later / Meta Business Suite
  - Columnas: Date, Time, Source, Type, Title, Caption, Status

## NeoQuiz (quiz.html)

### Generación con IA
- Tab "✨ Generar con IA": describir escenario → llama a `/api/generate-quiz`
- Todos los casos generados por IA son situaciones **críticas de reanimación** (NRP/AHA/AAP)
- El resultado se carga en el editor manual para ajuste antes de generar
- API key se guarda en `claude_api_key` (localStorage)

### Generación en Masa (Batch)
- Card "📦 Generar en Masa": un tema por línea → genera cada quiz con IA → ZIP de PNGs
- Estructura ZIP: `{tema}/stories/{1_portada, 2_escenario, 3_pregunta, 4_respuesta, 5_cta}.png`
- Cada item se agrega automáticamente a la biblioteca con caption

### Canvas (drawQuizSlide)
- Formato 9:16 (1080×1920)
- Sin logo NM en los slides — fue eliminado para ganar espacio
- Título portada: bold 76px, lineH 86
- `wrapText()` con `measureText()` — quiz usa system-ui (no Arial), no tiene el bug de Inter

## Novedades (novedades.html)

### Exportación de video
- Intenta MP4 primero: `video/mp4;codecs="avc1.42E01E,mp4a.40.2"` → `video/mp4` → WebM fallback
- La extensión del archivo refleja el formato real (.mp4 o .webm)
- Audio capturado via `AudioContext` + `createMediaStreamDestination`: usa `defaultAudioUrl` o audio del primer slide
- `audioEl.play()` se llama en el mismo tick que `mediaRecRef.current.start()`
- El reel se agrega a la biblioteca en `onstop` (no antes)

### Layout 3 columnas (desktop):
- **Izquierda (200px)**: lista de slides con orden, agregar/eliminar — `hidden md:flex` en móvil
- **Centro (420px → w-full en móvil)**: tabs "✨ Generar con IA" | "✏️ Editor manual" + acciones de exportación
- **Derecha (flex-1)**: preview canvas o biblioteca — `hidden lg:flex` en móvil

### Responsive móvil (novedades.html):
- Panel izquierdo oculto en móvil (`hidden md:flex`)
- Panel central toma `flex-1` en móvil / `md:flex-none md:w-96` en desktop
- Panel derecho oculto en móvil (`hidden lg:flex`)
- Header siempre en fila única con botones siempre visibles
- Body scrollea normalmente en móvil: `body { overflow-y: auto; height: auto }` via media query, `.app-root { height: auto; min-height: 100svh }`, `.body-section { overflow: visible }`
- Contenido del panel: `md:flex-1 md:overflow-y-auto` (en móvil altura natural, scroll a cargo de la página)

### Header (novedades.html):
- Mismo patrón que casosexp: botones `text-[9px] font-black px-2 py-1 rounded-lg` siempre visibles
- Botones: **📥 Exportar** (azul) | **📤 Importar** (verde) | **📚 Biblioteca** (ámbar)
- Format switcher (⬜ Carrusel / 📱 Reel) movido al panel de acciones de exportación, no en el header

### Biblioteca toggle:
- Botón "📚 Biblioteca" en el header alterna `mainTab` entre `'editor'` y `'library'`
- Cuando `mainTab === 'library'`, el **panel central** reemplaza el editor con la lista de items — funciona en todos los tamaños de pantalla (móvil, tablet, desktop)
- En desktop lg+, el panel derecho también muestra la biblioteca (comportamiento previo, sin romper nada)
- Cada card de biblioteca muestra: tipo, cantidad de slides, selector de estado, título, fecha, botón **↻ Recargar** (carga `slidesData` en el editor y vuelve a `mainTab='editor'`), botón eliminar y caption con "📋 Copiar"
- Botón "✕ Cerrar" dentro de la vista biblioteca vuelve a `mainTab='editor'`

## Renderizado de Canvas (casosexp.html)

### Funciones de renderizado:
- **renderSlideToCanvas()**: Genera carruseles 1:1 (1080×1080 PNG)
- **renderReelSlideToCanvas()**: Genera Reels 9:16 (1080×1920 PNG mientras se graba)
- **renderCTASlide()**: CTA 1:1
- **renderReelCTASlide()**: CTA 9:16

### Especificaciones de fuente y truncado:
- **Fuente**: Arial (siempre disponible en canvas, evita problemas con Inter)
- **Títulos 1:1**: bold 72px, máximo 25 caracteres
- **Títulos 9:16**: bold 96px, máximo 30 caracteres
- **Descripciones 1:1**: 36px, máximo **35 caracteres** + `…`
- **Descripciones 9:16**: 34px, máximo **45 caracteres** + `…`
- **Vitales**: bold 140px (1:1) / 160px (9:16)
- **Footer**: 26px (1:1) / 36px (9:16)

### Nota importante:
- NO usar `wrapText()` en casosexp — causa cuelgues por intentar medir Inter en canvas
- Truncado basado en **substring(0, N)**, no en `measureText()` — más confiable
- Todos los textos usan `.substring(0, maxChars)` antes de renderizar

## Audio personalizado en Casos Expandidos

En `casosexp.html`, la sección "Música para el Reel" permite:

1. **Subir MP3 local**: Click en el input de archivo
2. **Guardar como defecto**: persiste en localStorage (`defaultAudioBase64` + `defaultAudioFileName`)
3. **Cargar automáticamente**: al reiniciar la página, se carga el audio guardado (marcado con ⭐)
4. **Eliminar defecto**: limpia localStorage sin perder el audio actual
5. **Limpiar actual**: quita el audio de la sesión sin afectar el guardado

## Generación en Batch (Casos Expandidos)

Sección "Generar en Masa" en `casosexp.html`:

- **Formatos**: Carruseles (PNG 1:1) | Reels (MP4 9:16) | Ambos
- **Temas**: un tema por línea en el textarea
- **ZIP** con estructura `{tema}/carruseles/` y/o `{tema}/reels/`
- Reels: ~35s por reel. Batch de 10 reels ≈ 6 min.
- En Chromebook los ZIPs se descargan a Google Drive automáticamente

## Responsive / Mobile

Todos los módulos usan el mismo patrón:

- **Sidebar/aside**: `hidden md:flex` — se oculta en móvil
- **Layout principal**: `flex flex-col md:flex-row` — apilado vertical en móvil
- **Grids**: `grid-cols-1 lg:grid-cols-12` — columna única en móvil
- **Padding**: `p-4 md:p-8 lg:p-12` — reducido en pantallas chicas
- **Inputs**: `font-size: 16px` en CSS global — evita zoom automático en iOS/Android
- Media query: `@media (max-width: 768px) { input, textarea, select { padding: 12px !important; font-size: 16px; } }`

### Trampas conocidas:
- **No usar `window.innerWidth`** en props de React para layout — no es reactivo; usar clases Tailwind responsive
- **No usar `style={{ width: '420px' }}` fijo** en paneles — rompe móvil; usar clases como `w-full md:w-96`
- **`overflow: hidden` en body** bloquea scroll en móvil — en móvil usar `overflow-y: auto; height: auto` via media query
- **`height: 100vh`** en el contenedor raíz no contempla la barra de direcciones del navegador móvil — sobreescribir con `height: auto; min-height: 100svh` en móvil
- **`flex-shrink-0`** en el panel central dentro de un contenedor columna fija — el panel se desborda y recorta contenido; usar `flex-1` en móvil

## Sincronización Firebase (pendiente de implementar)

### Proyecto Firebase
- Proyecto: `studio-378906782-70dc4` (Firebase app, antes vacío — reutilizado para NeoMonitor)
- Firestore creado en región `nam5` (default database)
- Config SDK ya obtenida (apiKey, authDomain, appId, etc.)
- Firebase CLI v13.35.1 instalado globalmente (`sudo npm install -g firebase-tools@13`)

### Arquitectura definida
- Sin servidor, sin login — app personal, uso en múltiples dispositivos
- Archivo compartido `firebase-sync.js` incluido via `<script src="firebase-sync.js">` en cada HTML
- Estructura Firestore:
  ```
  /neomonitor/novedades/{itemId}
  /neomonitor/casos/{itemId}
  /neomonitor/quiz/{itemId}
  ```
- API pública que expone `firebase-sync.js`:
  ```js
  NeoSync.save(coleccion, item)   // guarda/actualiza item en Firestore + localStorage
  NeoSync.delete(coleccion, id)   // elimina de Firestore + localStorage
  NeoSync.loadAll(coleccion)      // descarga Firestore y mergea con localStorage (gana el más reciente por id timestamp)
  NeoSync.status                  // 'ok' | 'syncing' | 'offline'
  ```

### Flujo de sync
- Al **abrir** la app: `NeoSync.loadAll()` → merge con localStorage
- Al **guardar** en biblioteca: escribe en localStorage Y llama `NeoSync.save()`
- Al **eliminar**: borra en localStorage Y llama `NeoSync.delete()`
- Indicador visual de estado sync en cada módulo: "✓ sincronizado" / "↻ sincronizando..." / "⚠ sin conexión"

### Plan de implementación
1. Crear `firebase-sync.js` con la lógica compartida y config del proyecto
2. Integrar en `novedades.html` como prueba piloto
3. Validar y replicar en `casosexp.html`, `quiz.html`, `neoplanner.html`
4. Configurar reglas de seguridad Firestore (actualmente cerradas)

### Pendiente antes de arrancar
- Definir reglas de Firestore (por ahora bloqueado — hay que abrir lectura/escritura o usar Auth anónima)

## Convenciones

- Al agregar nuevos módulos, seguir el patrón de archivo único autocontenido
- Los formatos de salida son: 1:1 (carruseles/posts) y 9:16 (Reels/Stories)
- Targets: neonatología, pediatría, adultos
- Plataformas: Instagram y LinkedIn
- Canvas casosexp: siempre Arial, truncado por caracteres, nunca measureText en bucle
- Canvas quiz/novedades: usan system-ui/Inter con wrapText y measureText (no tienen el bug)

### Directrices de desarrollo:
1. Think before acting. Read existing files before writing code.
2. Be concise in output but thorough in reasoning.
3. Prefer editing over rewriting whole files.
4. Do not re-read files you have already read unless the file may have changed.
5. Test your code before declaring done.
6. No sycophantic openers or closing fluff.
7. Keep solutions simple and direct.
8. User instructions always override this file.
