// Apollo client pointed at the gateway's GraphQL API (the load balancer URL in AWS).
import { ApolloClient, ApolloLink, InMemoryCache, HttpLink } from '@apollo/client';
import { getClientId } from '@/lib/clientId';

// Adds this browser's anonymous id to every request (read by gateway/src/api.ts).
const clientIdLink = new ApolloLink((operation, forward) => {
    operation.setContext(({ headers = {} }) => ({
        headers: { ...headers, 'X-Client-Id': getClientId() },
    }));
    return forward(operation);
});

const apolloClient = new ApolloClient({
    link: clientIdLink.concat(new HttpLink({ uri: process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT })),
    cache: new InMemoryCache(),
    // Job status changes on the server, so always ask for the latest.
    defaultOptions: {
        watchQuery: { fetchPolicy: 'network-only' },
        query: { fetchPolicy: 'network-only' },
    },
});

export default apolloClient;
