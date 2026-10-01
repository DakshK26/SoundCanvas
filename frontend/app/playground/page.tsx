'use client';

// The /playground page: three tabs that show components/Playground.tsx (create), Examples.tsx
// and GenerationHistory.tsx. The URL holds the tab and which example is open, so a refresh lands
// on the same screen. Links from app/page.tsx and the example cards in Examples.tsx set those params.

import { Suspense, useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft } from 'lucide-react';
import Playground from '@/components/Playground';
import GenerationHistory from '@/components/GenerationHistory';
import Examples from '@/components/Examples';
import { exampleImage, findExample } from '@/lib/examples';
import { isSongGenre } from '@/types/graphql';

// The part of the page that reads the URL. It is split out so it can sit inside <Suspense>
// below, because Next.js needs a Suspense boundary around anything that calls useSearchParams.
function PlaygroundContent() {
    // useSearchParams reads the ?tab=...&example=...&genre=... part of the URL.
    const searchParams = useSearchParams();
    const router = useRouter();

    const tabFromUrl = searchParams.get('tab') || 'playground';
    const [activeTab, setActiveTab] = useState(tabFromUrl);

    // Anyone can type anything into the URL, so both params are checked before use. An unknown
    // example id or genre just becomes null and is ignored.
    const exampleId = findExample(searchParams.get('example'))?.id ?? null;
    const genreParam = searchParams.get('genre');
    const genreOverride = isSongGenre(genreParam) ? genreParam : null;

    // Runs whenever the tab in the URL changes. Back and forward change the URL but not the
    // state, so this copies the URL's tab back into state.
    useEffect(() => {
        setActiveTab(tabFromUrl);
    }, [tabFromUrl]);

    // Switching tabs writes a new URL. The example and genre are only kept on the create tab,
    // so they do not linger in the URL while browsing examples or history.
    const handleTabChange = (value: string) => {
        setActiveTab(value);
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

            {/* Create tab. With an example open, Playground starts with that example's photo and genre. */}
            <TabsContent value="playground">
                <Playground
                    initialImageUrl={exampleId ? exampleImage(exampleId) : undefined}
                    initialGenre={genreOverride ?? undefined}
                    exampleId={exampleId ?? undefined}
                />
            </TabsContent>

            {/* Examples tab */}
            <TabsContent value="examples">
                <Examples />
            </TabsContent>

            {/* History tab */}
            <TabsContent value="history">
                        <GenerationHistory />
            </TabsContent>
        </Tabs>
    );
}

// The page shell: a header with a Back link to app/page.tsx, then the tabs.
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

            {/* Main Content. Suspense shows the spinner until the URL params are ready. */}
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
