// One random UUID per browser, kept in localStorage. The API uses it to group history and
// rate-limit songs. Not auth: anyone with the id can see that browser's songs.
const STORAGE_KEY = 'soundcanvas-client-id';

export function getClientId(): string {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
        id = crypto.randomUUID();
        localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
}
