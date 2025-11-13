import { ApolloClient, InMemoryCache, HttpLink } from '@apollo/client';

const httpLink = new HttpLink({
    uri: process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT || 'http://localhost:4000/graphql',
});

const apolloClient = new ApolloClient({
    link: httpLink,
    cache: new InMemoryCache(),
    defaultOptions: {
        watchQuery: {
            fetchPolicy: 'network-only',
        },
        query: {
            fetchPolicy: 'network-only',
        },
    },
});

export default apolloClient;
