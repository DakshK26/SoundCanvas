'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Music, ArrowLeft } from 'lucide-react';
import Playground from '@/components/Playground';
import History from '@/components/History';
import Examples from '@/components/Examples';
import ThemeToggle from '@/components/ThemeToggle';

// Map example IDs to their image paths
const EXAMPLE_IMAGES: Record<string, string> = {
    house: '/examples/house.jpg',
    edm_chill: '/examples/edm_chill.jpg',
    edm_drop: '/examples/edm_drop.jpg',
    cinematic: '/examples/cinematic.jpg',
};

function PlaygroundContent() {
    const searchParams = useSearchParams();
    const defaultTab = searchParams.get('tab') || 'playground';

    // Check if an example was selected
    const exampleId = searchParams.get('example');
    const genreOverride = searchParams.get('genre');

    // Get the image URL for the example
    const initialImageUrl = exampleId ? EXAMPLE_IMAGES[exampleId] : undefined;

    return (
        <Tabs defaultValue={defaultTab} className="w-full">
            <TabsList className="grid w-full max-w-md mx-auto grid-cols-3 mb-8">
                <TabsTrigger value="playground">Playground</TabsTrigger>
                <TabsTrigger value="examples">Examples</TabsTrigger>
                <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>

            <TabsContent value="playground">
                <Playground
                    initialImageUrl={initialImageUrl}
                    initialGenre={genreOverride || undefined}
                />
            </TabsContent>

            <TabsContent value="examples">
                <Examples />
            </TabsContent>

            <TabsContent value="history">
                <History />
            </TabsContent>
        </Tabs>
    );
}

export default function PlaygroundPage() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-pink-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
            {/* Header */}
            <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50 dark:border-gray-700">
                <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/">
                            <Button variant="ghost" size="sm">
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back
                            </Button>
                        </Link>
                        <div className="flex items-center gap-2">
                            <Music className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 dark:from-purple-400 dark:to-pink-400 bg-clip-text text-transparent">
                                SoundCanvas
                            </h1>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="container mx-auto px-4 py-8">
                <Suspense fallback={
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                    </div>
                }>
                    <PlaygroundContent />
                </Suspense>
            </main>
        </div>
    );
}