'use client';

import { Suspense, useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import Playground from '@/components/Playground';
import History from '@/components/History';
import Examples from '@/components/Examples';
import { useBackendWarmup } from '@/lib/useBackendWarmup';

// Map example IDs to their image paths
const EXAMPLE_IMAGES: Record<string, string> = {
    house: '/examples/house.jpg',
    edm_chill: '/examples/edm_chill.jpg',
    edm_drop: '/examples/edm_drop.jpg',
    cinematic: '/examples/cinematic.jpg',
};

function PlaygroundContent() {
    const searchParams = useSearchParams();
    const router = useRouter();

    // Get tab from URL, default to 'playground'
    const tabFromUrl = searchParams.get('tab') || 'playground';
    const [activeTab, setActiveTab] = useState(tabFromUrl);

    // Check if an example was selected
    const exampleId = searchParams.get('example');
    const genreOverride = searchParams.get('genre');

    // Get the image URL for the example
    const initialImageUrl = exampleId ? EXAMPLE_IMAGES[exampleId] : undefined;

    // Sync tab state with URL changes
    useEffect(() => {
        setActiveTab(tabFromUrl);
    }, [tabFromUrl]);

    // Handle tab changes - update URL
    const handleTabChange = (value: string) => {
        setActiveTab(value);
        // Preserve example and genre params when switching tabs
        const params = new URLSearchParams();
        params.set('tab', value);
        if (exampleId && value === 'playground') {
            params.set('example', exampleId);
        }
        if (genreOverride && value === 'playground') {
            params.set('genre', genreOverride);
        }
        router.push(`/playground?${params.toString()}`);
    };

    return (
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
            <TabsList className="grid w-full max-w-md mx-auto grid-cols-3 mb-8">
                <TabsTrigger value="playground">Playground</TabsTrigger>
                <TabsTrigger value="examples">Examples</TabsTrigger>
                <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>

            <TabsContent value="playground">
                <Playground
                    initialImageUrl={initialImageUrl}
                    initialGenre={genreOverride || undefined}
                    exampleId={exampleId || undefined}
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

function BackendWarmupBanner() {
    const { status, isWarming, justLoaded, error, retry } = useBackendWarmup();

    if (justLoaded) {
        return (
            <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-2xl flex items-center gap-3 mb-6">
                <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <div className="flex-1">
                    <p className="font-medium">Server ready!</p>
                    <p className="text-sm">You can now generate music.</p>
                </div>
            </div>
        );
    }

    if (status === 'ready' || status === 'idle') {
        return null;
    }

    if (status === 'error') {
        return (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-2xl flex items-center gap-3 mb-6">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <div className="flex-1">
                    <p className="font-medium">Unable to connect to server</p>
                    <p className="text-sm">{error || 'The backend service is unavailable.'}</p>
                </div>
                <Button variant="outline" size="sm" onClick={retry} className="border-red-300 hover:bg-red-100">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Retry
                </Button>
            </div>
        );
    }

    if (isWarming) {
        return (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-2xl flex items-center gap-3 mb-6">
                <Loader2 className="w-5 h-5 animate-spin flex-shrink-0" />
                <div className="flex-1">
                    <p className="font-medium">Waking up the server...</p>
                    <p className="text-sm">This may take a few seconds on the first visit.</p>
                </div>
            </div>
        );
    }

    return null;
}

export default function PlaygroundPage() {
    return (
        <div className="min-h-screen aurora-bg">
            {/* Header */}
            <header className="border-b border-[#E8E0D8] bg-white/70 backdrop-blur-sm sticky top-0 z-50">
                <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/">
                            <Button variant="ghost" size="sm" className="text-[#5C5549] hover:bg-[#F5F0EB]">
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back
                            </Button>
                        </Link>
                        <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#E07A5F] to-[#D4583D] flex items-center justify-center shadow-md">
                                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
                                </svg>
                            </div>
                            <h1 className="text-xl font-semibold text-[#1A1814]">
                                SoundCanvas
                            </h1>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="container mx-auto px-4 py-8">
                <BackendWarmupBanner />
                <Suspense fallback={
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E07A5F]"></div>
                    </div>
                }>
                    <PlaygroundContent />
                </Suspense>
            </main>
        </div>
    );
}
