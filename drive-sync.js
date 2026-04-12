/* ═══════════════════════════════════════════════════════════════════════════════
   NEOMONITOR DRIVE SYNC — Sincronización de biblioteca con Google Drive
   ═══════════════════════════════════════════════════════════════════════════════ */

const DriveSync = (() => {
    const GOOGLE_CLIENT_ID = '556848757705-q1402ovpah1g0akpaa1ke9gpa7nnqsr4.apps.googleusercontent.com';
    const SCOPES = ['https://www.googleapis.com/auth/drive.file'];
    const FILE_NAME = 'neomonitor_library.json';

    let gapiLoaded = false;
    let authInited = false;
    let isSignedIn = false;
    let fileId = null;
    let statusCallbacks = [];

    const LIBRARY_KEYS = ['neocontent_library', 'neonovedades_library', 'neoquiz_library', 'videosinc_library'];

    // ─── Callbacks ─────────────────────────────────────────────────────────────
    const notifyStatusChange = () => {
        statusCallbacks.forEach(cb => cb({ isSignedIn, fileId }));
    };

    // ─── Inicializar Google API ────────────────────────────────────────────────
    const loadGapi = () => {
        return new Promise((resolve, reject) => {
            if (gapiLoaded) { resolve(); return; }

            const script = document.createElement('script');
            script.src = 'https://apis.google.com/js/api.js';
            script.async = true;
            script.defer = true;

            script.onload = () => {
                gapi.load('client:auth2', () => {
                    gapiLoaded = true;
                    resolve();
                });
            };

            script.onerror = () => reject(new Error('No se pudo cargar Google API'));
            document.head.appendChild(script);
        });
    };

    const init = async (clientId = GOOGLE_CLIENT_ID) => {
        if (authInited) return;

        try {
            await loadGapi();

            await gapi.client.init({
                clientId,
                scope: SCOPES.join(' ')
            });

            // Escuchar cambios de sign-in
            gapi.auth2.getAuthInstance().isSignedIn.listen(handleSignInChange);

            // Verificar estado inicial
            isSignedIn = gapi.auth2.getAuthInstance().isSignedIn.get();
            authInited = true;

            if (isSignedIn) {
                await findOrCreateFile();
            }

            notifyStatusChange();
        } catch (err) {
            console.error('Error inicializando DriveSync:', err);
            authInited = true;
        }
    };

    const handleSignInChange = async (signedIn) => {
        isSignedIn = signedIn;
        if (isSignedIn) {
            try {
                await findOrCreateFile();
            } catch (err) {
                console.error('Error al conectar Drive:', err);
            }
        }
        notifyStatusChange();
    };

    // ─── Encontrar o crear archivo en Drive ────────────────────────────────────
    const findOrCreateFile = async () => {
        try {
            // Buscar archivo existente
            const result = await gapi.client.drive.files.list({
                q: `name='${FILE_NAME}' and trashed=false`,
                spaces: 'drive',
                pageSize: 1,
                fields: 'files(id,name,modifiedTime)'
            });

            const files = result.result.files;
            if (files && files.length > 0) {
                fileId = files[0].id;
                return;
            }

            // Crear archivo si no existe
            const fileContent = {
                neocontent_library: [],
                neonovedades_library: [],
                neoquiz_library: [],
                videosinc_library: [],
                lastSync: new Date().toISOString()
            };

            const file = new File(
                [JSON.stringify(fileContent, null, 2)],
                FILE_NAME,
                { type: 'application/json' }
            );

            const form = new FormData();
            form.append('metadata', new Blob([JSON.stringify({ name: FILE_NAME })], { type: 'application/json' }));
            form.append('file', file);

            const uploadResult = await gapi.client.request({
                path: '/upload/drive/v3/files?uploadType=multipart',
                method: 'POST',
                body: form
            });

            fileId = uploadResult.result.id;
        } catch (err) {
            console.error('Error manejando archivo en Drive:', err);
            throw err;
        }
    };

    // ─── Cargar bibliotecas desde Drive ────────────────────────────────────────
    const loadAll = async () => {
        if (!isSignedIn || !fileId) {
            return getLocalLibraries();
        }

        try {
            const fileContent = await gapi.client.drive.files.get({
                fileId,
                alt: 'media'
            });

            const driveData = fileContent.result;
            const localData = getLocalLibraries();

            // Merge inteligente
            const merged = mergeLibraries(localData, driveData);

            // Guardar merged en localStorage
            LIBRARY_KEYS.forEach(key => {
                localStorage.setItem(key, JSON.stringify(merged[key] || []));
            });

            return merged;
        } catch (err) {
            console.error('Error cargando desde Drive:', err);
            return getLocalLibraries();
        }
    };

    const getLocalLibraries = () => {
        const result = {};
        LIBRARY_KEYS.forEach(key => {
            try {
                result[key] = JSON.parse(localStorage.getItem(key) || '[]');
            } catch {
                result[key] = [];
            }
        });
        result.lastSync = localStorage.getItem('neomonitor_lastSync') || new Date().toISOString();
        return result;
    };

    // ─── Merge inteligente de bibliotecas ──────────────────────────────────────
    const mergeLibraries = (local, drive) => {
        const result = {};

        LIBRARY_KEYS.forEach(key => {
            const localItems = local[key] || [];
            const driveItems = drive[key] || [];

            // Crear mapa por ID
            const merged = new Map();

            // Agregar items locales
            localItems.forEach(item => {
                merged.set(item.id, item);
            });

            // Agregar items de Drive (sobrescribir si son más recientes)
            driveItems.forEach(item => {
                const existing = merged.get(item.id);
                if (!existing) {
                    merged.set(item.id, item);
                } else {
                    // Comparar fechas: queda el más reciente
                    const localDate = new Date(existing.dateTime || 0);
                    const driveDate = new Date(item.dateTime || 0);
                    if (driveDate > localDate) {
                        merged.set(item.id, item);
                    }
                }
            });

            result[key] = Array.from(merged.values()).sort((a, b) => b.id - a.id);
        });

        result.lastSync = new Date().toISOString();
        return result;
    };

    // ─── Guardar bibliotecas a Drive ───────────────────────────────────────────
    const saveAll = async (data) => {
        if (!isSignedIn || !fileId) {
            // Sin conexión: solo guardar en localStorage
            LIBRARY_KEYS.forEach(key => {
                if (data[key]) {
                    localStorage.setItem(key, JSON.stringify(data[key]));
                }
            });
            localStorage.setItem('neomonitor_lastSync', new Date().toISOString());
            return;
        }

        try {
            const fileContent = {
                neocontent_library: data.neocontent_library || [],
                neonovedades_library: data.neonovedades_library || [],
                neoquiz_library: data.neoquiz_library || [],
                videosinc_library: data.videosinc_library || [],
                lastSync: new Date().toISOString()
            };

            // Actualizar archivo en Drive
            await gapi.client.request({
                path: `/upload/drive/v3/files/${fileId}?uploadType=media`,
                method: 'PATCH',
                body: JSON.stringify(fileContent)
            });

            // Guardar también en localStorage
            LIBRARY_KEYS.forEach(key => {
                if (data[key]) {
                    localStorage.setItem(key, JSON.stringify(data[key]));
                }
            });
            localStorage.setItem('neomonitor_lastSync', fileContent.lastSync);
        } catch (err) {
            console.error('Error guardando a Drive:', err);
            // Fallback: guardar en localStorage
            LIBRARY_KEYS.forEach(key => {
                if (data[key]) {
                    localStorage.setItem(key, JSON.stringify(data[key]));
                }
            });
        }
    };

    // ─── Sign In / Sign Out ────────────────────────────────────────────────────
    const signIn = async () => {
        try {
            await gapi.auth2.getAuthInstance().signIn();
        } catch (err) {
            console.error('Error en Sign In:', err);
        }
    };

    const signOut = async () => {
        try {
            await gapi.auth2.getAuthInstance().signOut();
            fileId = null;
        } catch (err) {
            console.error('Error en Sign Out:', err);
        }
    };

    // ─── Listeners ─────────────────────────────────────────────────────────────
    const onStatusChange = (callback) => {
        statusCallbacks.push(callback);
    };

    return {
        init,
        loadAll,
        saveAll,
        signIn,
        signOut,
        isSignedIn: () => isSignedIn,
        isAuthed: () => authInited,
        onStatusChange
    };
})();
