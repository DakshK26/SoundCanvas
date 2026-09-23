// Apollo client pointed at the gateway's GraphQL API (the load balancer URL in AWS).
import { ApolloClient, InMemoryCache, HttpLink } from '@apollo/client';

const apolloClient = new ApolloClient({
    link: new HttpLink({ uri: process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT }),
    cache: new InMemoryCache(),
    // Job status changes on the server, so always ask for the latest.
    defaultOptions: {
        watchQuery: { fetchPolicy: 'network-only' },
        query: { fetchPolicy: 'network-only' },
    },
});

export default apolloClient;
