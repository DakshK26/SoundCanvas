// The one Apollo client the whole app shares. components/ApolloProvider.tsx hands it to every
// page, and the components use it to run graphql/operations.ts against the API in api/src/api.ts.
// Every request gets an X-Client-Id header, and queries always hit the network so a poll is not
// served from the cache. NEXT_PUBLIC_GRAPHQL_ENDPOINT is baked in at build time, not read at runtime.
import { ApolloClient, ApolloLink, InMemoryCache, HttpLink } from '@apollo/client';
import { getClientId } from '@/lib/clientId';

// A link is a step every request passes through before it is sent. This one adds the browser's
// id from lib/clientId.ts as a header, which api/src/api.ts requires on every request.
const clientIdLink = new ApolloLink((operation, forward) => {
    operation.setContext(({ headers = {} }) => ({
        headers: { ...headers, 'X-Client-Id': getClientId() },
    }));
    return forward(operation);
});

// The header link runs first, then HttpLink actually sends the request to the API.
const apolloClient = new ApolloClient({
    link: clientIdLink.concat(new HttpLink({ uri: process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT })),
    cache: new InMemoryCache(),
    // network-only means always ask the server. Otherwise polling a generation just returns the
    // cached status. The cache is still filled, it is just never read first.
    defaultOptions: {
        watchQuery: { fetchPolicy: 'network-only' },
        query: { fetchPolicy: 'network-only' },
    },
});

export default apolloClient;
