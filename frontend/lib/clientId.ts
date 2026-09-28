// random id per browser, saved in localStorage the first time.
// gateway uses it for history / feedback / rate limit.
// NOTE: NOT auth. anyone who copies the id sees that browser's songs. fine for a demo, no accounts
const STORAGE_KEY = 'soundcanvas-client-id';

export function getClientId(): string {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
        id = crypto.randomUUID();
        localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
}
