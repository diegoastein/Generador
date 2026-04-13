/* ═══════════════════════════════════════════════════════════════════════════════
   NEOSYNC — Sincronización Firebase para NeoMonitor Expert Suite
   Arquitectura: Auth Anónima + Firestore, sin login de usuario
   ═══════════════════════════════════════════════════════════════════════════════ */

// ─── Firebase SDK via CDN (cargado dinámicamente) ─────────────────────────────
const FIREBASE_CONFIG = {
    apiKey: "AIzaSyCBM5uMOgbChSfr6DSxGISuMz945WqsDfU",
    authDomain: "studio-378906782-70dc4.firebaseapp.com",
    projectId: "studio-378906782-70dc4",
    storageBucket: "studio-378906782-70dc4.firebasestorage.app",
    messagingSenderId: "186978526622",
    appId: "1:186978526622:web:62d2bbf1c79bff6e00a28f"
};

// Colecciones válidas y sus claves en localStorage
const COLECCIONES = {
    novedades: 'neonovedades_library',
    casos:     'neocontent_library',
    quiz:      'neoquiz_library'
};

const NeoSync = (() => {
    let _db = null;
    let _auth = null;
    let _uid = null;
    let _status = 'offline';       // 'offline' | 'syncing' | 'ok'
    let _statusCallbacks = [];
    let _initPromise = null;

    // ─── Notificar cambios de estado ──────────────────────────────────────────
    const _setStatus = (s) => {
        _status = s;
        _statusCallbacks.forEach(cb => {
            try { cb(s); } catch (e) { console.warn('NeoSync status callback error:', e); }
        });
    };

    // ─── Cargar Firebase SDK dinámicamente ────────────────────────────────────
    const _loadScript = (src) => new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
        const s = document.createElement('script');
        s.src = src;
        s.onload = resolve;
        s.onerror = () => reject(new Error('No se pudo cargar: ' + src));
        document.head.appendChild(s);
    });

    // ─── Inicialización ───────────────────────────────────────────────────────
    const init = () => {
        if (_initPromise) return _initPromise;

        _initPromise = (async () => {
            _setStatus('syncing');
            try {
                // Cargar Firebase SDK modular compat (más compatible con vanilla JS)
                await _loadScript('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js');
                await _loadScript('https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js');
                await _loadScript('https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore-compat.js');

                // Inicializar app (evitar doble inicialización)
                if (!firebase.apps.length) {
                    firebase.initializeApp(FIREBASE_CONFIG);
                }

                _db = firebase.firestore();
                _auth = firebase.auth();

                // Auth anónima: esperar a que el usuario esté autenticado
                await new Promise((resolve, reject) => {
                    const unsub = _auth.onAuthStateChanged(async (user) => {
                        unsub();
                        if (user) {
                            _uid = user.uid;
                            resolve();
                        } else {
                            try {
                                const cred = await _auth.signInAnonymously();
                                _uid = cred.user.uid;
                                resolve();
                            } catch (e) {
                                reject(e);
                            }
                        }
                    });
                });

                _setStatus('ok');
                console.log('[NeoSync] Conectado. uid:', _uid);
            } catch (e) {
                console.error('[NeoSync] Error de inicialización:', e);
                _setStatus('offline');
                throw e;
            }
        })();

        return _initPromise;
    };

    // ─── Helper: referencia a un documento ───────────────────────────────────
    const _ref = (coleccion, id) => {
        if (!COLECCIONES[coleccion]) throw new Error('Colección desconocida: ' + coleccion);
        return _db.collection('neomonitor').doc(coleccion).collection('items').doc(String(id));
    };

    // ─── Helper: localStorage para una colección ─────────────────────────────
    const _getLocal = (coleccion) => {
        const key = COLECCIONES[coleccion];
        try { return JSON.parse(localStorage.getItem(key) || '[]'); }
        catch { return []; }
    };

    const _setLocal = (coleccion, items) => {
        localStorage.setItem(COLECCIONES[coleccion], JSON.stringify(items));
    };

    // ─── save: guarda/actualiza un item ──────────────────────────────────────
    const save = async (coleccion, item) => {
        // Siempre guardar en localStorage primero (funciona offline)
        const items = _getLocal(coleccion);
        const idx = items.findIndex(i => i.id === item.id);
        if (idx >= 0) items[idx] = item;
        else items.unshift(item);
        _setLocal(coleccion, items);

        // Sync a Firestore si hay conexión
        if (_status !== 'ok' || !_db) return;

        try {
            await _ref(coleccion, item.id).set(item);
        } catch (e) {
            console.warn('[NeoSync] save falló (Firestore), guardado local OK:', e.message);
        }
    };

    // ─── delete: elimina un item ──────────────────────────────────────────────
    const deleteItem = async (coleccion, id) => {
        // Borrar de localStorage
        const items = _getLocal(coleccion).filter(i => i.id !== id);
        _setLocal(coleccion, items);

        if (_status !== 'ok' || !_db) return;

        try {
            await _ref(coleccion, id).delete();
        } catch (e) {
            console.warn('[NeoSync] delete falló (Firestore), borrado local OK:', e.message);
        }
    };

    // ─── loadAll: descarga Firestore y mergea con localStorage ───────────────
    // Estrategia: gana el item con id (timestamp) más reciente en cada colección
    const loadAll = async (coleccion) => {
        const local = _getLocal(coleccion);

        if (_status !== 'ok' || !_db) return local;

        try {
            _setStatus('syncing');
            const snap = await _db
                .collection('neomonitor')
                .doc(coleccion)
                .collection('items')
                .get();

            const remoteItems = snap.docs.map(d => d.data());

            // Merge: crear mapa por id, gana el más reciente (id es timestamp numérico)
            const map = new Map();
            [...local, ...remoteItems].forEach(item => {
                const existing = map.get(item.id);
                if (!existing || Number(item.id) > Number(existing.id)) {
                    map.set(item.id, item);
                }
            });

            // Si hay items locales que no están en remoto, subirlos
            const remoteIds = new Set(remoteItems.map(i => i.id));
            const toUpload = local.filter(i => !remoteIds.has(i.id));
            if (toUpload.length > 0) {
                const batch = _db.batch();
                toUpload.forEach(item => batch.set(_ref(coleccion, item.id), item));
                await batch.commit();
            }

            const merged = Array.from(map.values()).sort((a, b) => Number(b.id) - Number(a.id));
            _setLocal(coleccion, merged);
            _setStatus('ok');
            return merged;
        } catch (e) {
            console.warn('[NeoSync] loadAll falló (Firestore), usando local:', e.message);
            _setStatus('offline');
            return local;
        }
    };

    // ─── API pública ──────────────────────────────────────────────────────────
    return {
        init,
        save,
        delete: deleteItem,
        loadAll,
        onStatusChange: (cb) => _statusCallbacks.push(cb),
        get status() { return _status; },
        get uid() { return _uid; }
    };
})();
