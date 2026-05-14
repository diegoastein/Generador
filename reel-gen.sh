#!/usr/bin/env bash
# reel-gen — Generador de Reels/Stories desde imágenes usando ffmpeg
# Requiere: ffmpeg   (sudo apt install ffmpeg)

set -euo pipefail

# ── Defaults ───────────────────────────────────────────────────────────────
FORMAT="vertical"   # vertical (1080×1920) | square (1080×1080)
DURATION=3          # segundos por imagen
FIT="contain"       # contain (sin recorte, barras negras) | cover (rellena y recorta)
OUT_FMT="mp4"       # mp4 | webm
OUTPUT=""           # se autodetecta si está vacío
AUDIO=""            # ruta al MP3
DIR=""              # carpeta de imágenes (alternativa a listar archivos)

# ── Ayuda ──────────────────────────────────────────────────────────────────
usage() {
cat <<EOF
Uso: $(basename "$0") [opciones] [img1 img2 img3 ...]

OPCIONES:
  -d, --dir CARPETA     Toma todas las imágenes de CARPETA (orden alfabético)
  -t, --duration SEGS   Duración por imagen en segundos  (default: 3)
  -f, --format FORMATO  Formato del video: vertical (default) | square
      --fit MODO        Ajuste de imagen: contain (default) | cover
  -a, --audio ARCHIVO   Archivo MP3 para el audio (se hace loop si es corto)
      --webm            Exportar en WebM en lugar de MP4
  -o, --output ARCHIVO  Nombre del archivo de salida
  -h, --help            Mostrar esta ayuda

EJEMPLOS:
  # Todas las fotos de la carpeta actual, orden alfabético:
  $(basename "$0") *.jpg

  # Carpeta específica, 4 segundos por foto, con música:
  $(basename "$0") --dir ./fotos -t 4 -a musica.mp3

  # Orden personalizado (el que se pasa en la línea):
  $(basename "$0") intro.jpg slide3.jpg slide1.jpg cierre.jpg

  # Cuadrado, sin recorte, exportar WebM:
  $(basename "$0") --format square --fit contain --webm *.png

  # Vertical recortando bordes (cover), sin audio:
  $(basename "$0") --fit cover -o resultado.mp4 *.jpg

EOF
}

# ── Parseo de opciones ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    -d|--dir)      DIR="$2";       shift 2 ;;
    -t|--duration) DURATION="$2";  shift 2 ;;
    -f|--format)   FORMAT="$2";    shift 2 ;;
       --fit)      FIT="$2";       shift 2 ;;
    -a|--audio)    AUDIO="$2";     shift 2 ;;
       --webm)     OUT_FMT="webm"; shift   ;;
    -o|--output)   OUTPUT="$2";    shift 2 ;;
    -h|--help)     usage; exit 0  ;;
    --)            shift; break   ;;
    -*)            echo "Opción desconocida: $1" >&2; usage >&2; exit 1 ;;
    *)             break ;;
  esac
done

# ── Verificar dependencias ─────────────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
  echo "Error: ffmpeg no está instalado."
  echo "Instalá con:  sudo apt install ffmpeg"
  exit 1
fi

# ── Recolectar imágenes ────────────────────────────────────────────────────
declare -a IMAGES

if [[ -n "$DIR" ]]; then
  [[ -d "$DIR" ]] || { echo "Error: carpeta no encontrada: $DIR" >&2; exit 1; }
  while IFS= read -r f; do
    IMAGES+=("$f")
  done < <(find "$DIR" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) | LC_ALL=C sort)
else
  for f in "$@"; do
    [[ -f "$f" ]] || { echo "Archivo no encontrado: $f" >&2; exit 1; }
    [[ "$f" =~ \.(jpg|jpeg|png)$ ]] || { echo "Formato no soportado: $f (usar jpg, jpeg o png)" >&2; exit 1; }
    IMAGES+=("$f")
  done
fi

if [[ ${#IMAGES[@]} -eq 0 ]]; then
  echo "Error: no se encontraron imágenes."
  echo ""
  usage
  exit 1
fi

# ── Validar parámetros ─────────────────────────────────────────────────────
[[ "$FORMAT" =~ ^(vertical|square)$ ]] || {
  echo "Error: --format debe ser 'vertical' o 'square'" >&2; exit 1; }
[[ "$FIT" =~ ^(contain|cover)$ ]] || {
  echo "Error: --fit debe ser 'contain' o 'cover'" >&2; exit 1; }
[[ -n "$AUDIO" && ! -f "$AUDIO" ]] && {
  echo "Error: archivo de audio no encontrado: $AUDIO" >&2; exit 1; }

# ── Dimensiones del canvas ─────────────────────────────────────────────────
if [[ "$FORMAT" == "square" ]]; then
  W=1080; H=1080
else
  W=1080; H=1920
fi

# ── Ruta de salida (absoluta) ──────────────────────────────────────────────
[[ -z "$OUTPUT" ]] && OUTPUT="reel.${OUT_FMT}"
ABS_OUTPUT=$(realpath -m "$OUTPUT")

# ── Audio en ruta absoluta ─────────────────────────────────────────────────
[[ -n "$AUDIO" ]] && AUDIO=$(realpath "$AUDIO")

# ── Directorio temporal con nombres seguros (sin caracteres raros) ─────────
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

CONCAT="$WORKDIR/list.txt"
> "$CONCAT"

i=0
LAST_SAFE=""
for img in "${IMAGES[@]}"; do
  ext="${img##*.}"
  ext_lower="${ext,,}"          # lowercase
  safename="$(printf '%05d.%s' "$i" "$ext_lower")"
  cp "$img" "$WORKDIR/$safename"
  printf "file '%s/%s'\nduration %s\n" "$WORKDIR" "$safename" "$DURATION" >> "$CONCAT"
  LAST_SAFE="$WORKDIR/$safename"
  i=$((i + 1))
done
# FFmpeg concat quirk: el último frame necesita repetirse sin duration
printf "file '%s'\n" "$LAST_SAFE" >> "$CONCAT"

# ── Filtro de video ────────────────────────────────────────────────────────
if [[ "$FIT" == "cover" ]]; then
  # Escala para llenar el frame y recorta el exceso
  VF="scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1"
else
  # Escala para que entre completo y agrega barras negras
  VF="scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
fi

# ── Duración total exacta ──────────────────────────────────────────────────
TOTAL=$(awk "BEGIN{printf \"%.3f\", ${#IMAGES[@]} * $DURATION}")

# ── Argumentos de codec ────────────────────────────────────────────────────
declare -a VARGS AARGS EXTRA

if [[ "$OUT_FMT" == "webm" ]]; then
  VARGS=(-c:v libvpx-vp9 -b:v 0 -crf 33 -r 30)
  AARGS=(-c:a libopus -b:a 192k)
  EXTRA=(-f webm)
else
  VARGS=(-c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -r 30)
  AARGS=(-c:a aac -b:a 192k -movflags +faststart)
  EXTRA=()
fi

# ── Resumen antes de ejecutar ──────────────────────────────────────────────
echo ""
echo "  Imágenes : ${#IMAGES[@]}"
printf "  Duración : %ss por imagen → %ss total\n" "$DURATION" "$TOTAL"
printf "  Formato  : %s (%dx%d)\n" "$FORMAT" "$W" "$H"
echo "  Ajuste   : $FIT"
[[ -n "$AUDIO" ]] && echo "  Audio    : $(basename "$AUDIO")"
echo "  Salida   : $ABS_OUTPUT"
echo ""

# ── Ejecutar ffmpeg ────────────────────────────────────────────────────────
declare -a FF
FF=(-y -f concat -safe 0 -i "$CONCAT")

if [[ -n "$AUDIO" ]]; then
  # -stream_loop -1 hace que el audio haga loop si el video es más largo
  FF+=(-stream_loop -1 -i "$AUDIO")
  FF+=(-vf "$VF" "${VARGS[@]}" "${AARGS[@]}" -t "$TOTAL" "${EXTRA[@]}")
else
  FF+=(-vf "$VF" "${VARGS[@]}" -an -t "$TOTAL" "${EXTRA[@]}")
fi

ffmpeg "${FF[@]}" "$ABS_OUTPUT"

echo ""
echo "✓ Listo: $ABS_OUTPUT"
