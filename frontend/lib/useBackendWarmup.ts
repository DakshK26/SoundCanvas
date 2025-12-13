'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

const GRAPHQL_ENDPOINT = process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT || 'http://localhost:4000/graphql';

// Check if we're using localhost (development without backend)
const isLocalhost = GRAPHQL_ENDPOINT.includes('localhost') || GRAPHQL_ENDPOINT.includes('127.0.0.1');

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
 * Skips warmup if using localhost (development mode without backend).
 * 
 * @returns { status, isWarm, error, retry }
 */
export function useBackendWarmup() {
    // If localhost, immediately mark as ready (skip warmup)
    const [status, setStatus] = useState<BackendStatus>(isLocalhost ? 'ready' : 'idle');
    const [error, setError] = useState<string | null>(null);
    const attemptRef = useRef(0);
    const maxAttempts = 3;
    const isMountedRef = useRef(true);

    const warmup = useCallback(async () => {
        // Skip warmup for localhost
        if (isLocalhost) {
            setStatus('ready');
            return true;
        }

        if (!isMountedRef.current) return false;
        
        attemptRef.current += 1;
        setStatus('warming');
        setError(null);

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);

            const response = await fetch(GRAPHQL_ENDPOINT, {
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
        
        // Only run warmup if not localhost
        if (!isLocalhost) {
            warmup();
        }

        return () => {
            isMountedRef.current = false;
        };
    }, [warmup]);

    return {
        status,
        isWarm: status === 'ready',
        isWarming: status === 'warming',
        error,
        retry,
    };
}
