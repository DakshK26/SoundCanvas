'use client';

import { useState, useEffect, useRef } from 'react';

const GRAPHQL_ENDPOINT = process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT || 'http://localhost:4000/graphql';

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
 * 
 * @returns { status, isWarm, error, retry }
 */
export function useBackendWarmup() {
    const [status, setStatus] = useState<BackendStatus>('idle');
    const [error, setError] = useState<string | null>(null);
    const attemptRef = useRef(0);
    const maxAttempts = 3;

    const warmup = async () => {
        attemptRef.current += 1;
        setStatus('warming');
        setError(null);

        try {
            const response = await fetch(GRAPHQL_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: HEALTH_QUERY }),
            });

            if (response.ok) {
                setStatus('ready');
                return true;
            } else {
                throw new Error(`Server returned ${response.status}`);
            }
        } catch (err: any) {
            console.error('Backend warmup attempt failed:', err);

            if (attemptRef.current < maxAttempts) {
                // Retry after a delay (backend may be starting)
                setTimeout(() => warmup(), 2000);
                return false;
            } else {
                setStatus('error');
                setError(err.message || 'Failed to connect to backend');
                return false;
            }
        }
    };

    const retry = () => {
        attemptRef.current = 0;
        warmup();
    };

    useEffect(() => {
        warmup();
    }, []);

    return {
        status,
        isWarm: status === 'ready',
        isWarming: status === 'warming',
        error,
        retry,
    };
}
