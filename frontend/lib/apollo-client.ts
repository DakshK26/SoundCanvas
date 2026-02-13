import { ApolloClient, InMemoryCache, HttpLink } from '@apollo/client';
import { getGraphQLEndpoint } from '@/lib/graphql-endpoint';

const httpLink = new HttpLink({
    uri: getGraphQLEndpoint(),
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
