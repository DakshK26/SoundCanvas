'use client';

// The app page: Playground, Examples and History tabs. The URL keeps the tab
// and any chosen example, so an example link opens straight into the Playground.
import { Suspense, useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft } from 'lucide-react';
import Playground from '@/components/Playground';
import History from '@/components/History';
import Examples from '@/components/Examples';

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
