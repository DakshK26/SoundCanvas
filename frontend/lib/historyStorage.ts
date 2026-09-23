// The History tab's storage: past generations kept in this browser's localStorage.
// Nothing here goes to the server; audio links point at S3 and expire (see History.tsx).
import { Generation } from '@/types/graphql';

const HISTORY_KEY = 'soundcanvas_history';
const MAX_HISTORY_ITEMS = 50;

/** All saved generations, newest first. */
export function getLocalHistory(): Generation[] {
    const stored = localStorage.getItem(HISTORY_KEY);
    return stored ? (JSON.parse(stored) as Generation[]) : [];
}

function saveHistory(history: Generation[]): void {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY_ITEMS)));
}

/** Adds a generation to the top, or replaces it if the id is already saved. */
export function addToLocalHistory(generation: Generation): void {
    saveHistory([generation, ...getLocalHistory().filter(g => g.id !== generation.id)]);
}

export function removeFromLocalHistory(id: string): void {
    saveHistory(getLocalHistory().filter(g => g.id !== id));
}

export function clearLocalHistory(): void {
    localStorage.removeItem(HISTORY_KEY);
}
