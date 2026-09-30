'use client';

// layout.tsx is a server component, and ApolloProvider needs 'use client'.
import { ApolloProvider } from '@apollo/client';
import apolloClient from '@/lib/apolloClient';

export default function ApolloProviderWrapper({ children }: { children: React.ReactNode }) {
    return <ApolloProvider client={apolloClient}>{children}</ApolloProvider>;
}