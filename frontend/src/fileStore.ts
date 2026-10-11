// The uploaded file itself never comes back from the server: it only stores the text and
// where each clause sits. To show highlights on the original, the browser keeps its own
// copy, in memory and in this browser's IndexedDB, for the same 24 hours the server keeps
// the review. Storage can be unavailable (private windows, blocked site data); then the
// copy lasts until the tab closes and the review falls back to a text view after that.

const DB_NAME = "leaselens";
const STORE = "files";
const TTL_MS = 24 * 60 * 60 * 1000;

export type StoredFile = { blob: Blob; name: string; type: string; savedAt: number };

const memory = new Map<string, StoredFile>();

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function withStore<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb();
  return new Promise<T>((resolve, reject) => {
    const request = run(db.transaction(STORE, mode).objectStore(STORE));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  }).finally(() => db.close());
}

export async function saveFile(documentId: string, file: File): Promise<void> {
  const entry: StoredFile = { blob: file, name: file.name, type: file.type, savedAt: Date.now() };
  memory.set(documentId, entry);
  try {
    await withStore("readwrite", (store) => store.put(entry, documentId));
  } catch {
    // Kept in memory only.
  }
}

export async function loadFile(documentId: string): Promise<StoredFile | null> {
  const cached = memory.get(documentId);
  if (cached) return cached;
  try {
    const entry = await withStore<StoredFile | undefined>("readonly", (store) => store.get(documentId));
    if (!entry) return null;
    if (Date.now() - entry.savedAt > TTL_MS) {
      void forgetFile(documentId);
      return null;
    }
    memory.set(documentId, entry);
    return entry;
  } catch {
    return null;
  }
}

export async function forgetFile(documentId: string): Promise<void> {
  memory.delete(documentId);
  try {
    await withStore("readwrite", (store) => store.delete(documentId));
  } catch {
    // Nothing stored.
  }
}

/** Drop copies older than the retention window, so nothing outlives the server's review. */
export async function purgeExpiredFiles(): Promise<void> {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    const cursorRequest = store.openCursor();
    cursorRequest.onsuccess = () => {
      const cursor = cursorRequest.result;
      if (!cursor) return;
      if (Date.now() - (cursor.value as StoredFile).savedAt > TTL_MS) cursor.delete();
      cursor.continue();
    };
    tx.oncomplete = () => db.close();
  } catch {
    // Storage unavailable: nothing to purge.
  }
}
