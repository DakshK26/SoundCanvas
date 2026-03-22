'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Genre } from '@/types/graphql';
import { useRouter } from 'next/navigation';

// Example images with their preset genres
const EXAMPLES = [
    {
        id: 'cinematic',
        imagePath: '/examples/cinematic.jpg',
        genre: Genre.CINEMATIC,
        genreLabel: 'Cinematic',
        description: 'Epic orchestral soundscapes',
        color: '#3D405B',
    },
    {
        id: 'edm_chill',
        imagePath: '/examples/edm_chill.jpg',
        genre: Genre.EDM_CHILL,
        genreLabel: 'EDM Chill',
        description: 'Relaxing electronic vibes',
        color: '#81B29A',
    },
    {
        id: 'edm_drop',
        imagePath: '/examples/edm_drop.jpg',
        genre: Genre.EDM_DROP,
        genreLabel: 'EDM Drop',
        description: 'High-energy drops and builds',
        color: '#F2CC8F',
    },
    {
        id: 'house',
        imagePath: '/examples/house.jpg',
        genre: Genre.HOUSE,
        genreLabel: 'House',
        description: 'Energetic beats for the dance floor',
        color: '#E07A5F',
    },
];

export default function Examples() {
    const router = useRouter();

    const handleExampleClick = (example: typeof EXAMPLES[0]) => {
        router.push(`/playground?tab=playground&example=${example.id}&genre=${example.genre}`);
    };

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6">
            <Card className="bg-white/80 backdrop-blur-sm border-[#E8E0D8] shadow-lg">
                <CardHeader>
                    <CardTitle className="flex items-center gap-3 text-[#1A1814]">
                        Example Images
                    </CardTitle>
                    <CardDescription className="text-[#8C8279]">
                        Click on any example to try it out with a preset genre
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        {EXAMPLES.map((example) => (
                            <div
                                key={example.id}
                                onClick={() => handleExampleClick(example)}
                                className="group cursor-pointer overflow-hidden rounded-2xl border border-[#E8E0D8] bg-white shadow-md hover:shadow-xl transition-all duration-300 hover:scale-[1.02]"
                            >
                                <div className="relative aspect-[4/3] overflow-hidden">
                                    <img
                                        src={example.imagePath}
                                        alt={`${example.genreLabel} example`}
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                                    <div className="absolute bottom-0 left-0 right-0 p-4">
                                        <span 
                                            className="inline-block px-3 py-1 rounded-full text-xs font-semibold text-white"
                                            style={{ backgroundColor: example.color }}
                                        >
                                            {example.genreLabel}
                                        </span>
                                    </div>
                                </div>
                                <div className="p-4">
                                    <p className="text-sm text-[#5C5549]">
                                        {example.description}
                                    </p>
                                    <p 
                                        className="text-xs mt-2 font-medium group-hover:translate-x-1 transition-transform"
                                        style={{ color: example.color }}
                                    >
                                        Try this one →
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
