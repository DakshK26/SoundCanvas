/**
 * Local storage-based history management for SoundCanvas generations.
 * Each user's browser maintains their own history - no server-side storage.
 */

import { GenerationStatus } from '@/types/graphql';

const HISTORY_KEY = 'soundcanvas_history';
const MAX_HISTORY_ITEMS = 50;

export interface LocalGeneration {
    id: string;
    imageUrl: string | null;
    audioUrl: string | null;
    genre: string;
    tempoBpm: number | null;
    scaleType: string | null;
    status: GenerationStatus;
    createdAt: string;
    errorMessage: string | null;
}

/**
 * Get all generations from localStorage
 */
export function getLocalHistory(): LocalGeneration[] {
    if (typeof window === 'undefined') {
        return [];
    }

    try {
        const stored = localStorage.getItem(HISTORY_KEY);
        if (!stored) {
            return [];
        }
        return JSON.parse(stored) as LocalGeneration[];
    } catch (error) {
        console.error('Failed to parse history from localStorage:', error);
        return [];
    }
}

/**
 * Add a generation to localStorage history
 */
export function addToLocalHistory(generation: LocalGeneration): void {
    if (typeof window === 'undefined') {
        return;
    }

    try {
        const history = getLocalHistory();

        // Check if this generation already exists (by id)
        const existingIndex = history.findIndex(g => g.id === generation.id);
        if (existingIndex !== -1) {
            // Update existing entry
            history[existingIndex] = generation;
        } else {
            // Add to beginning (newest first)
            history.unshift(generation);
        }

        // Limit to max items
        const trimmedHistory = history.slice(0, MAX_HISTORY_ITEMS);

        localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmedHistory));
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
    }
}

/**
 * Remove a generation from localStorage history
 */
export function removeFromLocalHistory(id: string): void {
    if (typeof window === 'undefined') {
        return;
    }

    try {
        const history = getLocalHistory();
        const filtered = history.filter(g => g.id !== id);
        localStorage.setItem(HISTORY_KEY, JSON.stringify(filtered));
    } catch (error) {
        console.error('Failed to remove from localStorage:', error);
    }
}

/**
 * Clear all history from localStorage
 */
export function clearLocalHistory(): void {
    if (typeof window === 'undefined') {
        return;
    }

    try {
        localStorage.removeItem(HISTORY_KEY);
    } catch (error) {
        console.error('Failed to clear localStorage:', error);
    }
}

/**
 * Get the count of items in history
 */
export function getHistoryCount(): number {
    return getLocalHistory().length;
}
