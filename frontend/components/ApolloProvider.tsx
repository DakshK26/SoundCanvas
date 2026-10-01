'use client';

// Puts the shared client from lib/apolloClient.ts into React context, so any component can call
// useQuery or useMutation without passing the client down. app/layout.tsx wraps every page in it.
// It is its own file because layout.tsx is a server component, and ApolloProvider needs 'use client'.
import { ApolloProvider } from '@apollo/client';
import apolloClient from '@/lib/apolloClient';

// children is the page Next.js is rendering, which layout.tsx passes through.
export default function ApolloProviderWrapper({ children }: { children: React.ReactNode }) {
    return <ApolloProvider client={apolloClient}>{children}</ApolloProvider>;
}