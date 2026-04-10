const http = require('http');

const PORT = 3001;

const server = http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    if (req.method === 'POST' && req.url === '/api/generate-case') {
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
    } else {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Endpoint no encontrado' }));
    }
});

server.listen(PORT, () => {
    console.log(`🚀 Proxy de Claude API levantado en http://localhost:${PORT}`);
    console.log(`📡 Endpoint: POST http://localhost:${PORT}/api/generate-case`);
});
