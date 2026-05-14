#!/usr/bin/env python3
"""
reel-gui.py — Interfaz local para generar Reels con ffmpeg.
Individual: subí imágenes, configurá, descargá el video.
Lote: elegí una carpeta padre, seleccioná subcarpetas, generá todos los videos.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
import warnings
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

warnings.filterwarnings('ignore', category=DeprecationWarning)

PORT      = 8080
DOWNLOADS = '/mnt/chromeos/MyFiles/Downloads'
HOME      = os.path.expanduser('~')

# ── Estado de trabajos batch ───────────────────────────────────────────────
_jobs      = {}   # job_id → dict con estado
_jobs_lock = threading.Lock()

# ══════════════════════════════════════════════════════════════════════════════
# HTML embebido
# ══════════════════════════════════════════════════════════════════════════════
HTML = '''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reel Generator</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #111; color: #e0e0e0; min-height: 100vh; padding: 28px 16px 64px;
}
.container { max-width: 760px; margin: 0 auto; }
header { margin-bottom: 20px; }
header h1 { font-size: 1.4rem; font-weight: 700; color: #fff; letter-spacing: -.02em; }
header p { color: #555; font-size: .82rem; margin-top: 3px; }
.badge {
  display: inline-block; background: #1a1a1a; border: 1px solid #2a2a2a;
  border-radius: 5px; padding: 2px 8px; font-size: .68rem; color: #555;
  margin-left: 8px; vertical-align: middle;
}

/* ── Tabs ── */
.tabs { display: flex; gap: 4px; margin-bottom: 24px; border-bottom: 1px solid #1e1e1e; padding-bottom: 0; }
.tab-btn {
  background: none; border: none; color: #555; font-size: .88rem; font-weight: 600;
  padding: 8px 18px; cursor: pointer; border-bottom: 2px solid transparent;
  margin-bottom: -1px; transition: color .15s, border-color .15s; font-family: inherit;
}
.tab-btn:hover { color: #aaa; }
.tab-btn.active { color: #c026d3; border-bottom-color: #c026d3; }
.tab-pane { display: none; }
.tab-pane.active { display: block; }

/* ── Upload zone ── */
.upload-zone {
  border: 2px dashed #2a2a2a; border-radius: 12px; padding: 32px 20px;
  text-align: center; cursor: pointer; transition: border-color .2s, background .2s; margin-bottom: 20px;
}
.upload-zone:hover, .upload-zone.drag-over { border-color: #c026d3; background: rgba(192,38,211,.05); }
.upload-icon { font-size: 1.8rem; margin-bottom: 8px; }
.upload-zone strong { display: block; font-size: .9rem; color: #fff; margin-bottom: 3px; }
.upload-zone span { font-size: .76rem; color: #555; }

/* ── List header ── */
.list-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.list-header h2 { font-size: .7rem; font-weight: 700; color: #555; text-transform: uppercase; letter-spacing: .08em; }
.list-actions { display: flex; gap: 5px; }
.small-btn {
  background: #1e1e1e; border: 1px solid #2a2a2a; border-radius: 5px;
  color: #777; font-size: .7rem; cursor: pointer; padding: 3px 9px; font-family: inherit;
  transition: border-color .15s, color .15s;
}
.small-btn:hover { border-color: #444; color: #ccc; }

/* ── Image list ── */
.image-list { display: flex; flex-direction: column; gap: 5px; margin-bottom: 20px; min-height: 44px; }
.empty-state { background: #1a1a1a; border-radius: 8px; padding: 20px; text-align: center; color: #333; font-size: .82rem; }
.image-item {
  display: flex; align-items: center; gap: 9px; background: #1a1a1a;
  border-radius: 7px; padding: 6px 9px; user-select: none; border: 1px solid transparent; transition: border-color .15s;
}
.image-item:hover { border-color: #252525; }
.image-item.sortable-ghost { opacity: .2; }
.image-item.sortable-chosen { background: #1e1e1e; }
.drag-handle { color: #2e2e2e; cursor: grab; font-size: .85rem; flex-shrink: 0; padding: 2px 3px; transition: color .15s; }
.drag-handle:hover { color: #555; }
.item-num { font-size: .65rem; color: #333; min-width: 14px; text-align: right; flex-shrink: 0; }
.item-thumb { width: 40px; height: 40px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }
.item-name { flex: 1; font-size: .78rem; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-remove { background: none; border: none; color: #2e2e2e; cursor: pointer; font-size: .78rem; padding: 3px 5px; border-radius: 3px; flex-shrink: 0; transition: color .15s; }
.item-remove:hover { color: #ef4444; }

/* ── Settings grid ── */
.settings { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin-bottom: 18px; }
.setting-card { background: #1a1a1a; border-radius: 9px; padding: 12px 14px; }
.setting-card.full-width { grid-column: span 2; }
.setting-card label { display: block; font-size: .65rem; font-weight: 700; color: #444; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 7px; }
.select-wrap { position: relative; }
.select-wrap::after { content: "\\25be"; position: absolute; right: 9px; top: 50%; transform: translateY(-50%); color: #555; pointer-events: none; font-size: .7rem; }
.setting-card select, .setting-card input[type="number"], .setting-card input[type="text"] {
  width: 100%; background: #222; border: 1px solid #2a2a2a; border-radius: 6px;
  color: #e0e0e0; padding: 7px 9px; font-size: .84rem; appearance: none;
  -webkit-appearance: none; font-family: inherit; transition: border-color .15s;
}
.setting-card select:focus, .setting-card input:focus { outline: none; border-color: #c026d3; }
.duration-hint { font-size: .68rem; color: #3a3a3a; margin-top: 5px; }

/* ── Audio row ── */
.audio-row {
  display: flex; align-items: center; gap: 7px; background: #222;
  border: 1px solid #2a2a2a; border-radius: 6px; padding: 7px 9px; cursor: pointer; transition: border-color .15s;
}
.audio-row:hover { border-color: #3a3a3a; }
.audio-name { flex: 1; font-size: .8rem; color: #555; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.audio-row.has-file .audio-name { color: #c026d3; }
.audio-clear { background: none; border: none; color: #3a3a3a; cursor: pointer; font-size: .76rem; padding: 2px 4px; display: none; border-radius: 3px; transition: color .15s; }
.audio-row.has-file .audio-clear { display: block; }
.audio-clear:hover { color: #ef4444; }

/* ── Generate button ── */
.generate-btn {
  width: 100%; padding: 13px;
  background: linear-gradient(135deg, #c026d3 0%, #7c3aed 100%);
  border: none; border-radius: 10px; color: #fff; font-size: .93rem;
  font-weight: 700; cursor: pointer; font-family: inherit; transition: opacity .2s, transform .1s;
}
.generate-btn:hover:not(:disabled) { opacity: .9; }
.generate-btn:active:not(:disabled) { transform: scale(.99); }
.generate-btn:disabled { opacity: .3; cursor: not-allowed; }

/* ── Progress ── */
.progress-section { margin-top: 14px; }
.progress-bar { height: 4px; background: #1a1a1a; border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #c026d3, #7c3aed); border-radius: 2px; transition: width .35s ease; width: 0%; }
.progress-label { font-size: .73rem; color: #555; text-align: center; margin-top: 7px; }
.progress-label.error { color: #ef4444; }

/* ── Batch: path row ── */
.path-row { display: flex; gap: 6px; margin-bottom: 14px; align-items: center; }
.path-row input[type="text"] {
  flex: 1; background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 7px;
  color: #ccc; padding: 8px 10px; font-size: .82rem; font-family: inherit;
}
.path-row input:focus { outline: none; border-color: #c026d3; }
.quick-btn {
  background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 7px;
  color: #777; font-size: .72rem; cursor: pointer; padding: 7px 10px; white-space: nowrap;
  font-family: inherit; transition: border-color .15s, color .15s; flex-shrink: 0;
}
.quick-btn:hover { border-color: #444; color: #ccc; }
.load-btn {
  background: #1e1e1e; border: 1px solid #333; border-radius: 7px;
  color: #ccc; font-size: .8rem; font-weight: 600; cursor: pointer; padding: 7px 14px;
  font-family: inherit; transition: background .15s; flex-shrink: 0;
}
.load-btn:hover { background: #2a2a2a; }

/* ── Batch: folder list ── */
.folder-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.folder-header span { font-size: .7rem; color: #555; text-transform: uppercase; letter-spacing: .07em; font-weight: 700; }
.folder-list { display: flex; flex-direction: column; gap: 5px; margin-bottom: 20px; max-height: 260px; overflow-y: auto; }
.folder-item {
  display: flex; align-items: center; gap: 10px; background: #1a1a1a;
  border-radius: 7px; padding: 9px 12px; cursor: pointer; border: 1px solid transparent; transition: border-color .15s;
}
.folder-item:hover { border-color: #2a2a2a; }
.folder-item input[type="checkbox"] { width: 15px; height: 15px; accent-color: #c026d3; cursor: pointer; flex-shrink: 0; }
.folder-item .fname { flex: 1; font-size: .83rem; color: #ccc; }
.folder-item .fcount { font-size: .7rem; color: #444; white-space: nowrap; }

/* ── Batch: results ── */
.results-list { margin-top: 12px; display: flex; flex-direction: column; gap: 5px; }
.result-item {
  display: flex; align-items: center; gap: 8px; background: #1a1a1a;
  border-radius: 6px; padding: 7px 11px; font-size: .78rem;
}
.result-ok { color: #4ade80; }
.result-err { color: #f87171; }
.result-name { flex: 1; color: #aaa; }
.result-file { color: #666; font-size: .72rem; }

/* ── Modal explorador ── */
.modal-overlay {
  display: none; position: fixed; inset: 0; background: rgba(0,0,0,.75);
  z-index: 200; align-items: center; justify-content: center;
}
.modal-overlay.open { display: flex; }
.modal-box {
  background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px;
  width: min(560px, 95vw); max-height: 78vh; display: flex; flex-direction: column; overflow: hidden;
}
.modal-header {
  display: flex; align-items: center; gap: 8px; padding: 12px 14px; border-bottom: 1px solid #222;
}
.modal-path { flex: 1; font-size: .72rem; color: #777; word-break: break-all; font-family: monospace; }
.modal-close { background: none; border: none; color: #555; cursor: pointer; font-size: 1rem; padding: 2px 6px; border-radius: 4px; }
.modal-close:hover { color: #fff; background: #2a2a2a; }
.modal-shortcuts { display: flex; gap: 6px; padding: 8px 12px; border-bottom: 1px solid #1e1e1e; flex-wrap: wrap; }
.browse-list { flex: 1; overflow-y: auto; padding: 6px; }
.browse-item {
  padding: 8px 11px; border-radius: 6px; cursor: pointer; font-size: .83rem;
  color: #bbb; transition: background .1s; display: flex; align-items: center; gap: 8px; user-select: none;
}
.browse-item:hover { background: #222; color: #fff; }
.browse-item.up { color: #555; font-style: italic; }
.modal-footer { padding: 10px 14px; border-top: 1px solid #1e1e1e; }
.select-dir-btn {
  width: 100%; padding: 10px; background: linear-gradient(135deg, #c026d3, #7c3aed);
  border: none; border-radius: 8px; color: #fff; font-size: .88rem; font-weight: 700;
  cursor: pointer; font-family: inherit; transition: opacity .15s;
}
.select-dir-btn:hover { opacity: .9; }

@media (max-width: 520px) {
  .settings { grid-template-columns: 1fr; }
  .setting-card.full-width { grid-column: span 1; }
  .path-row { flex-wrap: wrap; }
}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Reel Generator <span class="badge">ffmpeg</span></h1>
    <p>Generá videos para Instagram Reels &mdash; procesamiento local</p>
  </header>

  <!-- Tabs -->
  <div class="tabs">
    <button class="tab-btn active" data-tab="individual">Individual</button>
    <button class="tab-btn" data-tab="batch">Lote</button>
  </div>

  <!-- ══ INDIVIDUAL ══════════════════════════════════════════════════════ -->
  <div id="tab-individual" class="tab-pane active">

    <div class="upload-zone" id="uploadZone">
      <div class="upload-icon">&#128444;</div>
      <strong>Arrastrá imágenes o hacé clic para seleccionar</strong>
      <span>PNG &middot; JPG &middot; JPEG &mdash; se ordenan alfabéticamente por defecto</span>
    </div>
    <input type="file" id="imageInput" accept=".png,.jpg,.jpeg,image/png,image/jpeg" multiple style="display:none">

    <div class="list-header">
      <h2>Imágenes &nbsp;<span id="imgCount" style="color:#555">0</span></h2>
      <div class="list-actions">
        <button class="small-btn" id="sortAlphaBtn">A&ndash;Z</button>
        <button class="small-btn" id="clearAllBtn">Limpiar</button>
      </div>
    </div>
    <div class="image-list" id="imageList">
      <div class="empty-state">Las imágenes aparecerán aquí</div>
    </div>

    <div class="settings">
      <div class="setting-card">
        <label>Formato</label>
        <div class="select-wrap">
          <select id="formatSelect">
            <option value="vertical">Vertical 9:16 &mdash; Reels</option>
            <option value="square">Cuadrado 1:1</option>
          </select>
        </div>
      </div>
      <div class="setting-card">
        <label>Duración por imagen (seg.)</label>
        <input type="number" id="durationInput" value="3" min="0.5" max="60" step="0.5">
        <div class="duration-hint" id="durationHint">Duración total: &mdash;</div>
      </div>
      <div class="setting-card">
        <label>Ajuste de imagen</label>
        <div class="select-wrap">
          <select id="fitMode">
            <option value="contain">Ajustar &mdash; sin recorte</option>
            <option value="cover">Rellenar &mdash; recorta bordes</option>
          </select>
        </div>
      </div>
      <div class="setting-card">
        <label>Formato de exportación</label>
        <div class="select-wrap">
          <select id="outputFormat">
            <option value="mp4">MP4</option>
            <option value="webm">WebM</option>
          </select>
        </div>
      </div>
      <div class="setting-card full-width">
        <label>Audio MP3 (opcional)</label>
        <div class="audio-row" id="audioRow">
          <span>&#9835;</span>
          <span class="audio-name" id="audioName">Sin audio</span>
          <button class="audio-clear" id="audioClear">&#10005;</button>
        </div>
        <input type="file" id="audioInput" accept=".mp3,audio/mpeg" style="display:none">
      </div>
    </div>

    <button class="generate-btn" id="generateBtn" disabled>Generar video</button>
    <div class="progress-section" id="progressSection" style="display:none">
      <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
      <div class="progress-label" id="progressLabel"></div>
    </div>

  </div><!-- /individual -->

  <!-- ══ LOTE ═══════════════════════════════════════════════════════════ -->
  <div id="tab-batch" class="tab-pane">

    <!-- Ruta padre -->
    <div class="path-row">
      <input type="text" id="parentPath" placeholder="Ruta de la carpeta que contiene las subcarpetas...">
      <button class="quick-btn" id="btnExaminar">&#128194; Examinar</button>
      <button class="quick-btn" id="btnDesc">Descargas</button>
      <button class="quick-btn" id="btnLinux">Linux</button>
      <button class="load-btn" id="btnLoad">Cargar</button>
    </div>

    <!-- Modal explorador de directorios -->
    <div class="modal-overlay" id="browseModal">
      <div class="modal-box">
        <div class="modal-header">
          <span class="modal-path" id="browseCurrentPath">/</span>
          <button class="modal-close" id="browseClose">&#10005;</button>
        </div>
        <div class="modal-shortcuts">
          <button class="quick-btn" id="browseDesc">&#128193; Descargas</button>
          <button class="quick-btn" id="browseLinux">&#128193; Linux</button>
          <button class="quick-btn" id="browseRoot">&#128193; Raíz /</button>
        </div>
        <div class="browse-list" id="browseDirList">
          <div class="empty-state">Cargando&hellip;</div>
        </div>
        <div class="modal-footer">
          <button class="select-dir-btn" id="browseSelect">
            &#10003;&nbsp; Seleccionar esta carpeta
          </button>
        </div>
      </div>
    </div>

    <!-- Lista de carpetas -->
    <div id="folderSection" style="display:none">
      <div class="folder-header">
        <span id="folderCountLabel">0 carpetas</span>
        <div class="list-actions">
          <button class="small-btn" id="selectAll">Todas</button>
          <button class="small-btn" id="selectNone">Ninguna</button>
        </div>
      </div>
      <div class="folder-list" id="folderList"></div>
    </div>

    <!-- Config lote -->
    <div class="settings">
      <div class="setting-card">
        <label>Formato</label>
        <div class="select-wrap">
          <select id="batchFormat">
            <option value="vertical">Vertical 9:16 &mdash; Reels</option>
            <option value="square">Cuadrado 1:1</option>
          </select>
        </div>
      </div>
      <div class="setting-card">
        <label>Duración por imagen (seg.)</label>
        <input type="number" id="batchDuration" value="4" min="0.5" max="60" step="0.5">
      </div>
      <div class="setting-card">
        <label>Ajuste de imagen</label>
        <div class="select-wrap">
          <select id="batchFit">
            <option value="contain">Ajustar &mdash; sin recorte</option>
            <option value="cover">Rellenar &mdash; recorta bordes</option>
          </select>
        </div>
      </div>
      <div class="setting-card">
        <label>Formato de exportación</label>
        <div class="select-wrap">
          <select id="batchOutFormat">
            <option value="mp4">MP4</option>
            <option value="webm">WebM</option>
          </select>
        </div>
      </div>
      <div class="setting-card full-width">
        <label>Audio MP3 para todos los videos (opcional)</label>
        <div class="audio-row" id="batchAudioRow">
          <span>&#9835;</span>
          <span class="audio-name" id="batchAudioName">Sin audio</span>
          <button class="audio-clear" id="batchAudioClear">&#10005;</button>
        </div>
        <input type="file" id="batchAudioInput" accept=".mp3,audio/mpeg" style="display:none">
      </div>
    </div>

    <button class="generate-btn" id="batchGenBtn" disabled>Generar lote</button>

    <div class="progress-section" id="batchProgressSection" style="display:none">
      <div class="progress-bar"><div class="progress-fill" id="batchProgressFill"></div></div>
      <div class="progress-label" id="batchProgressLabel"></div>
      <div class="results-list" id="batchResults"></div>
    </div>

  </div><!-- /batch -->

</div><!-- /container -->

<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
<script>
"use strict";

// ── Tab switching ───────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

// ══════════════════════════════════════════════════════════════════════════
// INDIVIDUAL
// ══════════════════════════════════════════════════════════════════════════
let imageItems = [], audioFile = null, sortable = null;

const uploadZone   = document.getElementById("uploadZone");
const imageInput   = document.getElementById("imageInput");
const imageList    = document.getElementById("imageList");
const imgCount     = document.getElementById("imgCount");
const generateBtn  = document.getElementById("generateBtn");
const progSection  = document.getElementById("progressSection");
const progFill     = document.getElementById("progressFill");
const progLabel    = document.getElementById("progressLabel");
const durInput     = document.getElementById("durationInput");
const durHint      = document.getElementById("durationHint");
const audioRow     = document.getElementById("audioRow");
const audioName    = document.getElementById("audioName");
const audioClear   = document.getElementById("audioClear");
const audioInput   = document.getElementById("audioInput");

uploadZone.addEventListener("click", () => imageInput.click());
uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("drag-over"); });
uploadZone.addEventListener("dragleave", e => { if (!uploadZone.contains(e.relatedTarget)) uploadZone.classList.remove("drag-over"); });
uploadZone.addEventListener("drop", e => { e.preventDefault(); uploadZone.classList.remove("drag-over"); addImages(Array.from(e.dataTransfer.files)); });
imageInput.addEventListener("change", e => { addImages(Array.from(e.target.files)); imageInput.value = ""; });

audioRow.addEventListener("click", e => { if (e.target !== audioClear) audioInput.click(); });
audioInput.addEventListener("change", e => {
  const f = e.target.files[0]; if (!f) return;
  audioFile = f; audioName.textContent = f.name; audioRow.classList.add("has-file"); audioInput.value = "";
});
audioClear.addEventListener("click", e => {
  e.stopPropagation(); audioFile = null; audioName.textContent = "Sin audio"; audioRow.classList.remove("has-file");
});

document.getElementById("sortAlphaBtn").addEventListener("click", () => {
  imageItems.sort((a, b) => a.name.localeCompare(b.name)); renderList();
});
document.getElementById("clearAllBtn").addEventListener("click", () => {
  imageItems.forEach(i => URL.revokeObjectURL(i.url)); imageItems = []; renderList();
});
durInput.addEventListener("input", updateHint);

function addImages(files) {
  const valid = files.filter(f => /\\.(png|jpe?g)$/i.test(f.name));
  if (!valid.length) return;
  Promise.all(valid.map(file => new Promise(resolve => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload  = () => resolve({ file, url, name: file.name });
    img.onerror = () => { URL.revokeObjectURL(url); resolve(null); };
    img.src = url;
  }))).then(results => {
    imageItems.push(...results.filter(Boolean));
    imageItems.sort((a, b) => a.name.localeCompare(b.name));
    renderList();
  });
}

function renderList() {
  imgCount.textContent = imageItems.length;
  updateHint();
  if (sortable) { sortable.destroy(); sortable = null; }
  if (!imageItems.length) {
    imageList.innerHTML = "<div class=\\"empty-state\\">Las imágenes aparecerán aquí</div>";
    generateBtn.disabled = true; return;
  }
  generateBtn.disabled = false;
  imageList.innerHTML = imageItems.map((item, i) => `
    <div class="image-item" data-idx="${i}">
      <span class="drag-handle">&#10023;&#10023;</span>
      <span class="item-num">${i+1}</span>
      <img class="item-thumb" src="${item.url}" alt="">
      <span class="item-name">${esc(item.name)}</span>
      <button class="item-remove" data-idx="${i}">&#10005;</button>
    </div>`).join("");
  imageList.querySelectorAll(".item-remove").forEach(btn => {
    btn.addEventListener("click", () => {
      const i = parseInt(btn.dataset.idx, 10);
      URL.revokeObjectURL(imageItems[i].url); imageItems.splice(i, 1); renderList();
    });
  });
  sortable = Sortable.create(imageList, {
    animation: 150, handle: ".drag-handle",
    ghostClass: "sortable-ghost", chosenClass: "sortable-chosen",
    onEnd(e) { const [m] = imageItems.splice(e.oldIndex,1); imageItems.splice(e.newIndex,0,m); renderList(); }
  });
}

function updateHint() {
  const dur = parseFloat(durInput.value) || 0;
  durHint.textContent = imageItems.length > 0
    ? `Duración total: ${(imageItems.length * dur).toFixed(1)}s`
    : "Duración total: —";
}

generateBtn.addEventListener("click", async () => {
  if (!imageItems.length) return;
  const format    = document.getElementById("formatSelect").value;
  const duration  = Math.max(0.5, parseFloat(durInput.value) || 3);
  const fit       = document.getElementById("fitMode").value;
  const outFormat = document.getElementById("outputFormat").value;

  generateBtn.disabled = true; generateBtn.textContent = "Generando…";
  progSection.style.display = "block";
  progLabel.classList.remove("error");

  try {
    const images = [];
    for (let i = 0; i < imageItems.length; i++) {
      setProgress(progFill, progLabel, (i / imageItems.length) * 40,
        `Preparando imagen ${i+1} de ${imageItems.length}…`);
      const ext = imageItems[i].name.split(".").pop().toLowerCase();
      images.push({ name: imageItems[i].name, ext, data: await toDataURL(imageItems[i].file) });
    }
    let audio = null;
    if (audioFile) { setProgress(progFill, progLabel, 45, "Preparando audio…"); audio = await toDataURL(audioFile); }
    setProgress(progFill, progLabel, 50, "Procesando con ffmpeg…");

    const resp = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format, duration, fit, outFormat, images, audio })
    });
    if (!resp.ok) throw new Error(await resp.text());

    setProgress(progFill, progLabel, 95, "Descargando…");
    const disposition = resp.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    const filename = match ? match[1] : `reel.${outFormat}`;
    const blob = await resp.blob();
    triggerDownload(URL.createObjectURL(blob), filename);
    setProgress(progFill, progLabel, 100, "&#10003; Listo: " + filename);
  } catch (err) {
    progLabel.classList.add("error");
    setProgress(progFill, progLabel, 0, "Error: " + err.message);
  } finally {
    generateBtn.disabled = false; generateBtn.textContent = "Generar video";
  }
});

// ══════════════════════════════════════════════════════════════════════════
// LOTE
// ══════════════════════════════════════════════════════════════════════════
let batchAudioFile = null;
let batchDirs      = [];   // [{name, path, count}]
let batchPollTimer = null;

document.getElementById("btnDesc").addEventListener("click", () => {
  document.getElementById("parentPath").value = DOWNLOADS_PATH;
});
document.getElementById("btnLinux").addEventListener("click", () => {
  document.getElementById("parentPath").value = HOME_PATH;
});

// ── Explorador de directorios ──────────────────────────────────────────────
let browseCurrent = HOME_PATH;

document.getElementById("btnExaminar").addEventListener("click", () => {
  openModal(document.getElementById("parentPath").value.trim() || HOME_PATH);
});
document.getElementById("browseClose").addEventListener("click", closeModal);
document.getElementById("browseModal").addEventListener("click", e => {
  if (e.target.id === "browseModal") closeModal();
});
document.getElementById("browseDesc").addEventListener("click",  () => openBrowse(DOWNLOADS_PATH));
document.getElementById("browseLinux").addEventListener("click", () => openBrowse(HOME_PATH));
document.getElementById("browseRoot").addEventListener("click",  () => openBrowse("/"));
document.getElementById("browseSelect").addEventListener("click", () => {
  document.getElementById("parentPath").value = browseCurrent;
  closeModal();
  loadDirs();
});

function openModal(startPath) {
  document.getElementById("browseModal").classList.add("open");
  openBrowse(startPath);
}
function closeModal() {
  document.getElementById("browseModal").classList.remove("open");
}

async function openBrowse(path) {
  const listEl = document.getElementById("browseDirList");
  const pathEl = document.getElementById("browseCurrentPath");
  pathEl.textContent = path;
  listEl.innerHTML = "<div class=\\"empty-state\\">Cargando&hellip;</div>";
  try {
    const resp = await fetch("/browse?path=" + encodeURIComponent(path));
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || resp.statusText);
    browseCurrent = data.current;
    pathEl.textContent = data.current;
    let html = "";
    if (data.parent !== null) {
      html += `<div class="browse-item up" data-path="${esc(data.parent)}">&#8593; &nbsp;..</div>`;
    }
    for (const d of data.dirs) {
      html += `<div class="browse-item" data-path="${esc(d.path)}">&#128193;&nbsp; ${esc(d.name)}</div>`;
    }
    listEl.innerHTML = html || "<div class=\\"empty-state\\">Sin subcarpetas</div>";
    listEl.querySelectorAll(".browse-item").forEach(el => {
      el.addEventListener("click", () => openBrowse(el.dataset.path));
    });
  } catch (err) {
    listEl.innerHTML = `<div class="empty-state" style="color:#f87171">Error: ${esc(err.message)}</div>`;
  }
}

const batchAudioRow   = document.getElementById("batchAudioRow");
const batchAudioName  = document.getElementById("batchAudioName");
const batchAudioClear = document.getElementById("batchAudioClear");
const batchAudioInput = document.getElementById("batchAudioInput");

batchAudioRow.addEventListener("click", e => { if (e.target !== batchAudioClear) batchAudioInput.click(); });
batchAudioInput.addEventListener("change", e => {
  const f = e.target.files[0]; if (!f) return;
  batchAudioFile = f; batchAudioName.textContent = f.name;
  batchAudioRow.classList.add("has-file"); batchAudioInput.value = "";
});
batchAudioClear.addEventListener("click", e => {
  e.stopPropagation(); batchAudioFile = null; batchAudioName.textContent = "Sin audio";
  batchAudioRow.classList.remove("has-file");
});

document.getElementById("btnLoad").addEventListener("click", loadDirs);
document.getElementById("selectAll").addEventListener("click",  () => setAllChecked(true));
document.getElementById("selectNone").addEventListener("click", () => setAllChecked(false));
document.getElementById("batchGenBtn").addEventListener("click", startBatch);

async function loadDirs() {
  const path = document.getElementById("parentPath").value.trim();
  if (!path) return;
  const btn = document.getElementById("btnLoad");
  btn.textContent = "Cargando…"; btn.disabled = true;
  try {
    const resp = await fetch("/list-dirs?path=" + encodeURIComponent(path));
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || resp.statusText);
    batchDirs = data.dirs;
    renderFolderList();
    document.getElementById("folderSection").style.display = "block";
  } catch (err) {
    alert("Error al cargar carpetas: " + err.message);
  } finally {
    btn.textContent = "Cargar"; btn.disabled = false;
  }
}

function renderFolderList() {
  const list = document.getElementById("folderList");
  const lbl  = document.getElementById("folderCountLabel");
  lbl.textContent = `${batchDirs.length} carpeta${batchDirs.length !== 1 ? "s" : ""} con imágenes`;
  if (!batchDirs.length) {
    list.innerHTML = "<div class=\\"empty-state\\">No se encontraron subcarpetas con imágenes</div>";
    document.getElementById("batchGenBtn").disabled = true;
    return;
  }
  list.innerHTML = batchDirs.map((d, i) => `
    <label class="folder-item">
      <input type="checkbox" class="folder-cb" data-idx="${i}" checked>
      <span class="fname">${esc(d.name)}</span>
      <span class="fcount">${d.count} imágenes</span>
    </label>`).join("");
  updateBatchBtn();
  list.querySelectorAll(".folder-cb").forEach(cb => cb.addEventListener("change", updateBatchBtn));
}

function setAllChecked(val) {
  document.querySelectorAll(".folder-cb").forEach(cb => { cb.checked = val; });
  updateBatchBtn();
}

function updateBatchBtn() {
  const any = [...document.querySelectorAll(".folder-cb")].some(c => c.checked);
  document.getElementById("batchGenBtn").disabled = !any;
}

function getSelectedPaths() {
  return [...document.querySelectorAll(".folder-cb")]
    .filter(c => c.checked)
    .map(c => batchDirs[parseInt(c.dataset.idx)].path);
}

async function startBatch() {
  const paths = getSelectedPaths();
  if (!paths.length) return;

  const btn = document.getElementById("batchGenBtn");
  btn.disabled = true; btn.textContent = "Generando…";
  const ps = document.getElementById("batchProgressSection");
  ps.style.display = "block";
  document.getElementById("batchResults").innerHTML = "";
  setProgress(document.getElementById("batchProgressFill"), document.getElementById("batchProgressLabel"),
    0, "Enviando configuración…");

  try {
    let audioB64 = null;
    if (batchAudioFile) audioB64 = await toDataURL(batchAudioFile);

    const config = {
      dirs:      paths,
      audioB64,
      format:    document.getElementById("batchFormat").value,
      duration:  Math.max(0.5, parseFloat(document.getElementById("batchDuration").value) || 4),
      fit:       document.getElementById("batchFit").value,
      outFormat: document.getElementById("batchOutFormat").value,
    };

    const resp = await fetch("/batch-start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config)
    });
    if (!resp.ok) throw new Error(await resp.text());
    const { jobId } = await resp.json();

    pollBatch(jobId, paths.length);
  } catch (err) {
    document.getElementById("batchProgressLabel").classList.add("error");
    setProgress(document.getElementById("batchProgressFill"), document.getElementById("batchProgressLabel"),
      0, "Error: " + err.message);
    btn.disabled = false; btn.textContent = "Generar lote";
  }
}

function pollBatch(jobId, total) {
  const fill  = document.getElementById("batchProgressFill");
  const label = document.getElementById("batchProgressLabel");
  const resultsEl = document.getElementById("batchResults");
  let lastDone = 0;

  batchPollTimer = setInterval(async () => {
    try {
      const resp = await fetch("/batch-status?id=" + jobId);
      const s    = await resp.json();

      const pct = s.total > 0 ? (s.done / s.total) * 100 : 0;
      const txt = s.current
        ? `Procesando ${s.done + 1} de ${s.total}: ${s.current}…`
        : s.complete
          ? `&#10003; Listo &mdash; ${s.done} videos generados`
          : "Iniciando…";
      setProgress(fill, label, pct, txt);

      // Render new results
      if (s.results.length > lastDone) {
        for (let i = lastDone; i < s.results.length; i++) {
          const r   = s.results[i];
          const div = document.createElement("div");
          div.className = "result-item";
          if (r.ok) {
            div.innerHTML = `<span class="result-ok">&#10003;</span><span class="result-name">${esc(r.dir)}</span><span class="result-file">${esc(r.output)}</span>`;
          } else {
            div.innerHTML = `<span class="result-err">&#10005;</span><span class="result-name">${esc(r.dir)}</span><span class="result-file" style="color:#f87171">${esc(r.error)}</span>`;
          }
          resultsEl.appendChild(div);
        }
        lastDone = s.results.length;
      }

      if (s.complete) {
        clearInterval(batchPollTimer);
        const btn = document.getElementById("batchGenBtn");
        btn.disabled = false; btn.textContent = "Generar lote";
      }
    } catch { /* ignore poll errors */ }
  }, 800);
}

// ── Helpers compartidos ────────────────────────────────────────────────────
function toDataURL(file) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = e => res(e.target.result);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}

function setProgress(fill, label, pct, text) {
  fill.style.width   = pct + "%";
  label.innerHTML    = text;
}

function triggerDownload(url, filename) {
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

function esc(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
</script>
</body>
</html>'''

# ══════════════════════════════════════════════════════════════════════════════
# Servidor
# ══════════════════════════════════════════════════════════════════════════════
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        code = str(args[1]) if len(args) > 1 else ''
        if code not in ('200', '304', ''):
            print(f'  {args[0]}  →  {code}')

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        params = parse_qs(parsed.query)

        if path == '/':
            # Inyectar rutas base para el JS
            page = (HTML
                    .replace('HOME_PATH',      json.dumps(HOME))
                    .replace('DOWNLOADS_PATH', json.dumps(DOWNLOADS)))
            data = page.encode('utf-8')
            self._respond(200, 'text/html; charset=utf-8', data)

        elif path == '/browse':
            dir_path = params.get('path', [HOME])[0]
            try:
                self._json(200, browse_directory(dir_path))
            except Exception as e:
                self._json(400, {'error': str(e)})

        elif path == '/list-dirs':
            parent = params.get('path', [''])[0]
            try:
                dirs = list_image_dirs(parent)
                self._json(200, {'dirs': dirs})
            except Exception as e:
                self._json(400, {'error': str(e)})

        elif path == '/batch-status':
            job_id = params.get('id', [''])[0]
            with _jobs_lock:
                job = _jobs.get(job_id)
            if job is None:
                self._json(404, {'error': 'Job no encontrado'})
            else:
                self._json(200, {k: job[k] for k in ('total','done','current','complete','results')})
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == '/generate':
            self._individual()
        elif self.path == '/batch-start':
            self._batch_start()
        else:
            self.send_response(404); self.end_headers()

    # ── individual ─────────────────────────────────────────────────────────
    def _individual(self):
        try:
            payload = self._read_json()
        except Exception as e:
            return self._error(400, str(e))
        workdir = tempfile.mkdtemp(prefix='reel_')
        try:
            video_bytes, filename = generate_reel(payload, workdir)
            ext  = filename.rsplit('.', 1)[-1]
            mime = 'video/mp4' if ext == 'mp4' else 'video/webm'
            self._respond(200, mime, video_bytes,
                          extra={'Content-Disposition': f'attachment; filename="{filename}"'})
        except Exception as e:
            print(f'  Error: {e}')
            self._error(500, str(e))
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    # ── batch start ────────────────────────────────────────────────────────
    def _batch_start(self):
        try:
            config = self._read_json()
        except Exception as e:
            return self._error(400, str(e))

        dirs = config.get('dirs', [])
        if not dirs:
            return self._error(400, 'No se recibieron carpetas')

        job_id  = uuid.uuid4().hex[:8]
        workdir = tempfile.mkdtemp(prefix=f'batch_{job_id}_')

        # Guardar audio si viene
        audio_path = None
        audio_b64  = config.get('audioB64')
        if audio_b64:
            audio_path = os.path.join(workdir, 'audio.mp3')
            with open(audio_path, 'wb') as f:
                f.write(decode_data_url(audio_b64))

        with _jobs_lock:
            _jobs[job_id] = {
                'total': len(dirs), 'done': 0, 'current': None,
                'complete': False, 'results': [], 'workdir': workdir,
            }

        threading.Thread(
            target=run_batch,
            args=(job_id, dirs, audio_path, config),
            daemon=True
        ).start()

        self._json(200, {'jobId': job_id})

    # ── utils ───────────────────────────────────────────────────────────────
    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length))

    def _respond(self, code, ctype, body, extra=None):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())

    def _json(self, code, data):
        self._respond(code, 'application/json', json.dumps(data))

    def _error(self, code, msg):
        self._respond(code, 'text/plain; charset=utf-8', msg)


# ══════════════════════════════════════════════════════════════════════════════
# Lógica de generación
# ══════════════════════════════════════════════════════════════════════════════

def decode_data_url(data_url: str) -> bytes:
    _, encoded = data_url.split(',', 1)
    return base64.b64decode(encoded)


def browse_directory(path: str) -> dict:
    path = os.path.realpath(path) if os.path.exists(path) else HOME
    if not os.path.isdir(path):
        path = HOME
    parent = os.path.dirname(path) if path != '/' else None
    subdirs = []
    try:
        for name in sorted(os.listdir(path), key=str.lower):
            if name.startswith('.'):
                continue
            full = os.path.join(path, name)
            if os.path.isdir(full):
                subdirs.append({'name': name, 'path': full})
    except PermissionError:
        pass
    return {'current': path, 'parent': parent, 'dirs': subdirs}


def list_image_dirs(parent_path: str) -> list:
    if not os.path.isdir(parent_path):
        raise ValueError(f'Carpeta no encontrada: {parent_path}')
    result = []
    for name in sorted(os.listdir(parent_path)):
        full = os.path.join(parent_path, name)
        if not os.path.isdir(full):
            continue
        try:
            imgs = [f for f in os.listdir(full)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        except PermissionError:
            continue
        if imgs:
            result.append({'name': name, 'path': full, 'count': len(imgs)})
    return result


def build_ffmpeg_cmd(img_paths, audio_path, output_path, concat_path,
                     fmt, duration, fit, out_fmt):
    w, h = (1080, 1920) if fmt == 'vertical' else (1080, 1080)

    if fit == 'cover':
        vf = (f'scale={w}:{h}:force_original_aspect_ratio=increase,'
              f'crop={w}:{h},setsar=1')
    else:
        vf = (f'scale={w}:{h}:force_original_aspect_ratio=decrease,'
              f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1')

    with open(concat_path, 'w') as f:
        for p in img_paths:
            f.write(f"file '{p}'\nduration {duration}\n")
        f.write(f"file '{img_paths[-1]}'\n")

    total = len(img_paths) * duration
    cmd   = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_path]

    if audio_path:
        cmd += ['-stream_loop', '-1', '-i', audio_path]

    if out_fmt == 'webm':
        cmd += ['-vf', vf, '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '33', '-r', '30']
        cmd += ['-c:a', 'libopus', '-b:a', '192k'] if audio_path else ['-an']
        cmd += ['-f', 'webm']
    else:
        cmd += ['-vf', vf, '-c:v', 'libx264', '-preset', 'fast',
                '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '30']
        cmd += (['-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart']
                if audio_path else ['-an'])

    cmd += ['-t', str(total), output_path]
    return cmd


def generate_reel(payload: dict, workdir: str) -> tuple:
    """Modo individual: imágenes llegan como base64."""
    fmt      = payload.get('format', 'vertical')
    duration = float(payload.get('duration', 3))
    fit      = payload.get('fit', 'contain')
    out_fmt  = payload.get('outFormat', 'mp4')
    images   = payload.get('images', [])
    audio    = payload.get('audio')

    if not images:
        raise ValueError('No se recibieron imágenes')

    img_dir = os.path.join(workdir, 'imgs')
    os.makedirs(img_dir)
    img_paths = []
    for i, img in enumerate(images):
        ext  = img.get('ext', 'jpg').strip('.').lower()
        path = os.path.join(img_dir, f'{i:05d}.{ext}')
        with open(path, 'wb') as f:
            f.write(decode_data_url(img['data']))
        img_paths.append(path)

    audio_path = None
    if audio:
        audio_path = os.path.join(workdir, 'audio.mp3')
        with open(audio_path, 'wb') as f:
            f.write(decode_data_url(audio))

    base_name   = os.path.splitext(images[0].get('name', 'reel'))[0]
    filename    = f'{base_name}.{out_fmt}'
    output_path = os.path.join(workdir, filename)
    concat_path = os.path.join(workdir, 'list.txt')

    cmd = build_ffmpeg_cmd(img_paths, audio_path, output_path, concat_path,
                           fmt, duration, fit, out_fmt)
    print(f'  ffmpeg individual: {len(img_paths)} imgs × {duration}s [{fmt}, {fit}, {out_fmt}]')
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])

    with open(output_path, 'rb') as f:
        return f.read(), filename


def generate_for_folder(folder_path: str, audio_path, config: dict, workdir: str) -> str:
    """Genera un video para una carpeta. Lee imágenes directamente del disco."""
    fmt      = config.get('format', 'vertical')
    duration = float(config.get('duration', 4))
    fit      = config.get('fit', 'contain')
    out_fmt  = config.get('outFormat', 'mp4')

    imgs = sorted(
        f for f in os.listdir(folder_path)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    )
    if not imgs:
        raise ValueError('No se encontraron imágenes')

    img_paths = [os.path.join(folder_path, f) for f in imgs]
    base_name = os.path.splitext(imgs[0])[0]
    output_path = os.path.join(folder_path, f'{base_name}.{out_fmt}')

    # concat en workdir para no contaminar la carpeta de imágenes
    safe_name   = ''.join(c if c.isalnum() else '_' for c in os.path.basename(folder_path))
    concat_path = os.path.join(workdir, f'list_{safe_name}.txt')

    cmd = build_ffmpeg_cmd(img_paths, audio_path, output_path, concat_path,
                           fmt, duration, fit, out_fmt)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-400:])

    return output_path


def run_batch(job_id: str, dirs: list, audio_path, config: dict):
    with _jobs_lock:
        workdir = _jobs[job_id]['workdir']

    for i, folder in enumerate(dirs):
        name = os.path.basename(folder)
        with _jobs_lock:
            _jobs[job_id]['current'] = name
        try:
            out    = generate_for_folder(folder, audio_path, config, workdir)
            result = {'dir': name, 'ok': True, 'output': os.path.basename(out)}
            print(f'  ✓ {name} → {os.path.basename(out)}')
        except Exception as e:
            result = {'dir': name, 'ok': False, 'error': str(e)}
            print(f'  ✗ {name}: {e}')
        with _jobs_lock:
            _jobs[job_id]['done'] = i + 1
            _jobs[job_id]['results'].append(result)

    with _jobs_lock:
        _jobs[job_id]['complete'] = True
        _jobs[job_id]['current']  = None

    shutil.rmtree(workdir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if not shutil.which('ffmpeg'):
        print('Error: ffmpeg no está instalado.  sudo apt install ffmpeg')
        sys.exit(1)

    url = f'http://localhost:{PORT}'
    print(f'\n  Reel Generator  →  {url}')
    print('  Ctrl+C para detener.\n')

    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    server = ThreadedHTTPServer(('localhost', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  Detenido.')


if __name__ == '__main__':
    main()
