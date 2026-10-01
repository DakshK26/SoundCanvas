// One random UUID per browser, kept in localStorage. lib/apolloClient.ts sends it as the
// X-Client-Id header, and api/src/resolvers.ts uses it to group history and rate-limit songs.
// Not auth: anyone with the id can see that browser's songs.
const STORAGE_KEY = 'soundcanvas-client-id';

// localStorage keeps the value across reloads and tabs until the user clears site data. It only
// exists in the browser, which is why GenerationHistory.tsx turns off server rendering for its query.
export function getClientId(): string {
    let id = localStorage.getItem(STORAGE_KEY);
    // First visit, so make an id and save it for next time.
    if (!id) {
        id = crypto.randomUUID();
        localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
}
