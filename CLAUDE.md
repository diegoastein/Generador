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
| `index.html` | Dashboard | Panel central con los 6 módulos |
| `novedades.html` | Novedades NeoMonitor | Carruseles + Reels/Stories de novedades de producto, con soporte de audio |
| `casosclinicos.html` | Casos Clínicos | 33 escenarios clínicos, carruseles 1:1 con CTA |
| `casosexp.html` | Casos Expandidos | 33 escenarios, posts 1:1 + Reels 9:16 con CTA |
| `quiz.html` | NeoQuiz Expert | 32 presets clínicos, pack de 5 Stories con respuesta/explicación/CTA |
| `videosinc.html` | Video Sync 9:16 | Sincronización y exportación de video vertical |
| `integrado.html` | Suite Integrada | Interfaz unificada: Video Sync + Casos + NeoQuiz |

## Protocolos clínicos de referencia

- NRP 8ª Edición
- AHA / AAP 2023

## Convenciones

- Al agregar nuevos módulos, seguir el patrón de archivo único autocontenido
- Los formatos de salida son: 1:1 (carruseles/posts) y 9:16 (Reels/Stories)
- Targets: neonatología, pediatría, adultos
- Plataformas: Instagram y LinkedIn

1. Think before acting. Read existing files before writing code.
2. Be concise in output but thorough in reasoning.
3. Prefer editing over rewriting whole files.
4. Do not re-read files you have already read unless the file may have changed.
5. Test your code before declaring done.
6. No sycophantic openers or closing fluff.
7. Keep solutions simple and direct.
8. User instructions always override this file.