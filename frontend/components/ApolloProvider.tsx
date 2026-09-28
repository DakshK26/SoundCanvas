'use client';

// wrapper bc ApolloProvider needs 'use client' and layout.tsx is a server component
import { ApolloProvider } from '@apollo/client';
import apolloClient from '@/lib/apollo-client';

export default function ApolloProviderWrapper({ children }: { children: React.ReactNode }) {
    return <ApolloProvider client={apolloClient}>{children}</ApolloProvider>;
}