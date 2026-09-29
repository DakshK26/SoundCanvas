// Not auth: anyone with the id can see that browser's songs.
const STORAGE_KEY = 'soundcanvas-client-id';

export function getClientId(): string {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
        id = crypto.randomUUID();
        localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
}
