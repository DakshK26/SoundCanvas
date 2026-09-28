// apollo client -> gateway graphql. in AWS NEXT_PUBLIC_GRAPHQL_ENDPOINT = the ALB url
// (NEXT_PUBLIC_ = baked in at BUILD time, not read at runtime!)
import { ApolloClient, ApolloLink, InMemoryCache, HttpLink } from '@apollo/client';
import { getClientId } from '@/lib/clientId';

// stick X-Client-Id on every request (gateway/src/api.ts reads it)
const clientIdLink = new ApolloLink((operation, forward) => {
    operation.setContext(({ headers = {} }) => ({
        headers: { ...headers, 'X-Client-Id': getClientId() },
    }));
    return forward(operation);
});

const apolloClient = new ApolloClient({
    link: clientIdLink.concat(new HttpLink({ uri: process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT })),
    cache: new InMemoryCache(),
    // no cache - polling a job's status is pointless if apollo just returns the cached PENDING
    defaultOptions: {
        watchQuery: { fetchPolicy: 'network-only' },
        query: { fetchPolicy: 'network-only' },
    },
});

export default apolloClient;
