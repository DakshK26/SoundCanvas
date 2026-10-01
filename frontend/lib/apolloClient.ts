// The one Apollo client the whole app shares. components/ApolloProvider.tsx hands it to every
// page, and the components use it to run graphql/operations.ts against the API in api/src/api.ts.
// Every request gets an X-Client-Id header, and every query and mutation goes to the network
// with nothing cached. NEXT_PUBLIC_GRAPHQL_ENDPOINT is baked in at build time, not read at runtime.
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
    // ApolloClient needs a cache object, but no-cache below means nothing is ever stored in it.
    cache: new InMemoryCache(),
    // no-cache means always ask the server and don't keep the answer. Nothing in the app reads
    // the cache: Playground copies each poll into its own state and History re-polls.
    defaultOptions: {
        watchQuery: { fetchPolicy: 'no-cache' },
        query: { fetchPolicy: 'no-cache' },
        mutate: { fetchPolicy: 'no-cache' },
    },
});

export default apolloClient;
