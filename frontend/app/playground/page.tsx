'use client';

// the actual app: Playground / Examples / History tabs.
// tab + example live in the url (?tab=&example=&genre=) so links to an example work
import { Suspense, useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft } from 'lucide-react';
import Playground from '@/components/Playground';
import History from '@/components/History';
import Examples from '@/components/Examples';
import { exampleImage, findExample } from '@/lib/examples';
import { isSongGenre } from '@/types/graphql';

function PlaygroundContent() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const tabFromUrl = searchParams.get('tab') || 'playground';
    const [activeTab, setActiveTab] = useState(tabFromUrl);

    // url params = user input, ignore anything that isn't a real example/genre
    const exampleId = findExample(searchParams.get('example'))?.id ?? null;
    const genreParam = searchParams.get('genre');
    const genreOverride = isSongGenre(genreParam) ? genreParam : null;

    // back/forward changes the url but not the state -> sync it
    useEffect(() => {
        setActiveTab(tabFromUrl);
    }, [tabFromUrl]);

    // keep example + genre in the url only on the playground tab (so it's shareable)
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

            <TabsContent value="playground">
                <Playground
                    initialImageUrl={exampleId ? exampleImage(exampleId) : undefined}
                    initialGenre={genreOverride ?? undefined}
                    exampleId={exampleId ?? undefined}
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
