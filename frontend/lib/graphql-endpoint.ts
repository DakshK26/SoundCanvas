const DEFAULT_GRAPHQL_ENDPOINT = 'http://localhost:4000/graphql';

/**
 * Returns the configured GraphQL endpoint and normalizes bare host values
 * to include the /graphql path.
 */
export function getGraphQLEndpoint(): string {
    const rawEndpoint = process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT?.trim();

    if (!rawEndpoint) {
        return DEFAULT_GRAPHQL_ENDPOINT;
    }

    try {
        const url = new URL(rawEndpoint);
        if (!url.pathname || url.pathname === '/') {
            url.pathname = '/graphql';
        }
        return url.toString().replace(/\/$/, '');
    } catch {
        const trimmed = rawEndpoint.replace(/\/+$/, '');
        return trimmed.endsWith('/graphql') ? trimmed : `${trimmed}/graphql`;
    }
}

export function isLocalGraphQLEndpoint(endpoint = getGraphQLEndpoint()): boolean {
    return endpoint.includes('localhost') || endpoint.includes('127.0.0.1');
}

/**
 * Skip warmup only in local development.
 * In production, localhost endpoints should fail loudly instead of silently skipping.
 */
export function shouldSkipWarmup(endpoint = getGraphQLEndpoint()): boolean {
    return isLocalGraphQLEndpoint(endpoint) && process.env.NODE_ENV !== 'production';
}
