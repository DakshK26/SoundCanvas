// An anonymous id for this browser, made once and kept in localStorage.
// The gateway uses it to scope history, feedback and rate limits to one browser.
// It is not a login: anyone who copies the id can see that browser's songs.
const STORAGE_KEY = 'soundcanvas-client-id';

export function getClientId(): string {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
        id = crypto.randomUUID();
        localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
}
