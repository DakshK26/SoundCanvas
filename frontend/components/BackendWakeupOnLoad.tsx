'use client';

import { useEffect } from 'react';
import { getGraphQLEndpoint, shouldSkipWarmup } from '@/lib/graphql-endpoint';

const WARMUP_QUERY = `
  query Warmup {
    __typename
  }
`;

const WARMUP_FLAG = '__soundcanvas_warmup_sent__';

declare global {
    interface Window {
        __soundcanvas_warmup_sent__?: boolean;
    }
}

/**
 * Sends a single wake-up request as soon as the site is loaded,
 * so Fly can start before the user reaches the playground.
 */
export default function BackendWakeupOnLoad() {
    useEffect(() => {
        const endpoint = getGraphQLEndpoint();

        if (shouldSkipWarmup(endpoint)) {
            return;
        }

        if (window[WARMUP_FLAG]) {
            return;
        }

        window[WARMUP_FLAG] = true;

        void fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: WARMUP_QUERY }),
            keepalive: true,
        }).catch(() => {
            // Ignore errors here; the playground warmup banner handles user-facing retries.
        });
    }, []);

    return null;
}
