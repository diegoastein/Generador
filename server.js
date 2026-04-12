const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = 8000;
const DIR = __dirname;

// MIME types
const mimeTypes = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.wav': 'audio/wav',
    '.mp3': 'audio/mpeg'
};

const server = http.createServer(async (req, res) => {
    const parsedUrl = url.parse(req.url, true);
    let pathname = parsedUrl.pathname;

    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // API endpoint: generate case
    if (req.method === 'POST' && pathname === '/api/generate-case') {
        let body = '';

        req.on('data', chunk => {
            body += chunk.toString();
        });

        req.on('end', async () => {
            try {
                const { caseDescription, apiKey } = JSON.parse(body);

                if (!apiKey || !caseDescription) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'apiKey y caseDescription son requeridos' }));
                    return;
                }

                const systemPrompt = `Eres un pediatra y neonatólogo experto en reanimación neonatal y pediátrica basado en la 8ª edición del Neonatal Resuscitation Program (NRP) y las guías AHA/AAP 2023. Tu respuesta DEBE estar en español rioplatense.

Genera un caso clínico educativo con exactamente 5 slides. RESTRICCIONES CRÍTICAS:
- "description": MÁXIMO 120 caracteres (1 oración corta)
- "title": MÁXIMO 50 caracteres
- "hr": número de 2-3 dígitos (ej: 85, 140, 180) o null
- "spo2": número de 2 dígitos (ej: 88, 92, 96) o null

RESPONDE SOLO CON JSON VÁLIDO (sin markdown, sin explicaciones adicionales):

{
  "title": "Título corto",
  "steps": [
    {"title": "Título 1", "description": "Texto muy breve máx 120 chars", "hr": 85, "spo2": 94},
    {"title": "Título 2", "description": "Texto muy breve máx 120 chars", "hr": 140, "spo2": 88},
    {"title": "Título 3", "description": "Texto muy breve máx 120 chars", "hr": null, "spo2": 92},
    {"title": "Título 4", "description": "Texto muy breve máx 120 chars", "hr": 110, "spo2": 95},
    {"title": "Título 5", "description": "Texto muy breve máx 120 chars", "hr": null, "spo2": null}
  ]
}`;

                const claudeResponse = await fetch('https://api.anthropic.com/v1/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-api-key': apiKey,
                        'anthropic-version': '2023-06-01'
                    },
                    body: JSON.stringify({
                        model: 'claude-sonnet-4-20250514',
                        max_tokens: 2048,
                        system: systemPrompt,
                        messages: [{ role: 'user', content: `Genera un caso clínico sobre: ${caseDescription}` }]
                    })
                });

                const claudeData = await claudeResponse.json();

                if (!claudeResponse.ok) {
                    res.writeHead(claudeResponse.status, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: claudeData.error?.message || 'Error en API de Claude' }));
                    return;
                }

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(claudeData));
            } catch (err) {
                console.error('Error:', err);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            }
        });
        return;
    }

    // API endpoint: generate quiz
    if (req.method === 'POST' && pathname === '/api/generate-quiz') {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', async () => {
            try {
                const { quizDescription, apiKey } = JSON.parse(body);
                if (!apiKey || !quizDescription) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'apiKey y quizDescription son requeridos' }));
                    return;
                }
                const systemPrompt = `Sos un médico intensivista experto en emergencias, reanimación neonatal, pediátrica y adultos, con dominio de NRP 8ª edición y guías AHA/AAP 2023. Tu objetivo es generar preguntas de quiz clínico de alto impacto para profesionales de la salud.

REGLAS ESTRICTAS:
- El escenario debe ser una situación CRÍTICA de reanimación o emergencia real (nunca un caso ambulatorio o leve)
- La pregunta debe ser de conducta clínica aguda (¿qué hacés primero?, ¿cuál es el fármaco?, ¿cuándo intubás?)
- EXACTAMENTE 3 opciones de respuesta — todas plausibles, solo una correcta
- "answer" debe coincidir EXACTAMENTE (carácter por carácter) con una de las 3 opciones
- "explanation" debe citar NRP/AHA/AAP con fundamento técnico breve
- Español rioplatense. Sin markdown. Solo JSON válido.

RESTRICCIONES DE LONGITUD:
- "title": máximo 50 caracteres
- "caseText": máximo 300 caracteres (2-3 oraciones)
- "question": máximo 150 caracteres
- cada opción: máximo 80 caracteres
- "explanation": máximo 400 caracteres

RESPONDE SOLO CON JSON:
{
  "title": "Título corto",
  "caseText": "Escenario clínico crítico...",
  "question": "¿Cuál es la conducta inmediata?",
  "options": ["Opción A", "Opción B", "Opción C"],
  "answer": "Opción A",
  "explanation": "Fundamento técnico basado en NRP/AHA/AAP..."
}`;

                const claudeResponse = await fetch('https://api.anthropic.com/v1/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-api-key': apiKey,
                        'anthropic-version': '2023-06-01'
                    },
                    body: JSON.stringify({
                        model: 'claude-sonnet-4-20250514',
                        max_tokens: 1024,
                        system: systemPrompt,
                        messages: [{ role: 'user', content: `Generá un quiz clínico sobre: ${quizDescription}` }]
                    })
                });
                const claudeData = await claudeResponse.json();
                if (!claudeResponse.ok) {
                    res.writeHead(claudeResponse.status, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: claudeData.error?.message || 'Error en API de Claude' }));
                    return;
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(claudeData));
            } catch (err) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            }
        });
        return;
    }

    // API endpoint: generate novedades
    if (req.method === 'POST' && pathname === '/api/generate-novedades') {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', async () => {
            try {
                const { description, apiKey } = JSON.parse(body);
                if (!apiKey || !description) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'apiKey y description son requeridos' }));
                    return;
                }
                const systemPrompt = `Sos un experto en comunicación médica digital y copywriter para redes sociales de salud. Trabajás para NeoMonitor, una plataforma web de simulación clínica para neonatología, pediatría y adultos, usada por médicos, enfermeros y residentes para entrenamiento clínico.

Cuando el usuario te describe una característica o novedad de NeoMonitor, generás un carrusel de Instagram/LinkedIn con 3 a 5 diapositivas que anuncian esa novedad de forma clara, profesional y atractiva.

RESTRICCIONES CRÍTICAS:
- "title": máximo 40 caracteres
- "subtitle": máximo 50 caracteres
- "body": máximo 200 caracteres (2-3 oraciones cortas)
- "tag": una etiqueta corta en mayúsculas (NUEVO, MEJORA, UPDATE, FEATURE, etc.)
- "palette": uno de estos valores: azul, ambar, verde, violeta, rojo, oscuro, cian

El tono es: profesional, directo, entusiasta, orientado al beneficio del usuario médico. Español rioplatense.

RESPONDE SOLO CON JSON VÁLIDO (sin markdown):
{
  "slides": [
    {"title": "...", "subtitle": "...", "body": "...", "tag": "NUEVO", "palette": "azul"},
    {"title": "...", "subtitle": "...", "body": "...", "tag": "MEJORA", "palette": "verde"}
  ]
}`;

                const claudeResponse = await fetch('https://api.anthropic.com/v1/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-api-key': apiKey,
                        'anthropic-version': '2023-06-01'
                    },
                    body: JSON.stringify({
                        model: 'claude-sonnet-4-20250514',
                        max_tokens: 2048,
                        system: systemPrompt,
                        messages: [{ role: 'user', content: `Generá slides de novedades para: ${description}` }]
                    })
                });
                const claudeData = await claudeResponse.json();
                if (!claudeResponse.ok) {
                    res.writeHead(claudeResponse.status, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: claudeData.error?.message || 'Error en API' }));
                    return;
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(claudeData));
            } catch (err) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            }
        });
        return;
    }

    // Static file serving
    if (pathname === '/') {
        pathname = '/index.html';
    }

    const filepath = path.join(DIR, pathname);

    // Security: prevent directory traversal
    if (!filepath.startsWith(DIR)) {
        res.writeHead(403, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Acceso denegado' }));
        return;
    }

    fs.readFile(filepath, (err, data) => {
        if (err) {
            res.writeHead(404, { 'Content-Type': 'text/html' });
            res.end('<h1>404 - No encontrado</h1>');
            return;
        }

        const ext = path.extname(filepath);
        const contentType = mimeTypes[ext] || 'application/octet-stream';

        res.writeHead(200, { 'Content-Type': contentType });
        res.end(data);
    });
});

server.listen(PORT, () => {
    console.log(`\n🚀 NeoMonitor Expert Suite levantado`);
    console.log(`📍 http://localhost:${PORT}`);
    console.log(`🔌 API: POST http://localhost:${PORT}/api/generate-case`);
    console.log(`\n✅ Todo listo. Abre http://localhost:${PORT} en tu navegador.\n`);
});
