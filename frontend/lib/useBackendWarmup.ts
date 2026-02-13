'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { getGraphQLEndpoint, shouldSkipWarmup } from '@/lib/graphql-endpoint';

// Simple health check query
const HEALTH_QUERY = `
  query HealthCheck {
    __typename
  }
`;

export type BackendStatus = 'idle' | 'warming' | 'ready' | 'error';

/**
 * Hook to warm up the backend on cold start.
 * Pings the GraphQL endpoint on mount to wake up the Fly.io machine.
 * Skips warmup only for localhost in non-production environments.
 * 
 * @returns { status, isWarm, error, retry }
 */
export function useBackendWarmup() {
    const [status, setStatus] = useState<BackendStatus>('idle');
    const [error, setError] = useState<string | null>(null);
    const [justLoaded, setJustLoaded] = useState(false);
    const attemptRef = useRef(0);
    const maxAttempts = 3;
    const isMountedRef = useRef(true);

    const warmup = useCallback(async () => {
        const endpoint = getGraphQLEndpoint();

        // Skip warmup only for local development.
        if (shouldSkipWarmup(endpoint)) {
            setStatus('ready');
            return true;
        }

        if (!isMountedRef.current) return false;

        attemptRef.current += 1;
        setStatus('warming');
        setError(null);

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000);

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: HEALTH_QUERY }),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!isMountedRef.current) return false;

            if (response.ok) {
                if (status === 'warming') {
                    setJustLoaded(true);
                    setTimeout(() => setJustLoaded(false), 3000);
                }
                setStatus('ready');
                return true;
            } else {
                throw new Error(`Server returned ${response.status}`);
            }
        } catch (err: any) {
            if (!isMountedRef.current) return false;

            if (attemptRef.current < maxAttempts) {
                setTimeout(() => {
                    if (isMountedRef.current) {
                        warmup();
                    }
                }, 2000);
                return false;
            } else {
                if (isMountedRef.current) {
                    setStatus('error');
                    setError(
                        err.name === 'AbortError'
                            ? 'Connection timed out'
                            : (err.message || 'Failed to connect to backend')
                    );
                }
                return false;
            }
        }
    }, []);

    const retry = useCallback(() => {
        attemptRef.current = 0;
        warmup();
    }, [warmup]);

    useEffect(() => {
        isMountedRef.current = true;
        warmup();

        return () => {
            isMountedRef.current = false;
        };
    }, [warmup]);

    return {
        status,
        isWarm: status === 'ready',
        isWarming: status === 'warming',
        justLoaded,
        error,
        retry,
    };
}
