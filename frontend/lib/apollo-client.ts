// The Apollo client the whole app shares. Every request gets X-Client-Id, and queries always
// hit the network so a poll is not served from the cache.
// NEXT_PUBLIC_GRAPHQL_ENDPOINT is baked in at build time, not read at runtime.
import { ApolloClient, ApolloLink, InMemoryCache, HttpLink } from '@apollo/client';
import { getClientId } from '@/lib/clientId';

const clientIdLink = new ApolloLink((operation, forward) => {
    operation.setContext(({ headers = {} }) => ({
        headers: { ...headers, 'X-Client-Id': getClientId() },
    }));
    return forward(operation);
});

const apolloClient = new ApolloClient({
    link: clientIdLink.concat(new HttpLink({ uri: process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT })),
    cache: new InMemoryCache(),
    // Otherwise polling a job just returns the cached status.
    defaultOptions: {
        watchQuery: { fetchPolicy: 'network-only' },
        query: { fetchPolicy: 'network-only' },
    },
});

export default apolloClient;
