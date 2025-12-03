'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Genre } from '@/types/graphql';
import { Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';

// Example images with their preset genres
const EXAMPLES = [
    {
        id: 'house',
        imagePath: '/examples/house.jpg',
        genre: Genre.HOUSE,
        genreLabel: 'House',
        description: 'Energetic beats for the dance floor',
    },
    {
        id: 'edm_chill',
        imagePath: '/examples/edm_chill.jpg',
        genre: Genre.EDM_CHILL,
        genreLabel: 'EDM Chill',
        description: 'Relaxing electronic vibes',
    },
    {
        id: 'edm_drop',
        imagePath: '/examples/edm_drop.jpg',
        genre: Genre.EDM_DROP,
        genreLabel: 'EDM Drop',
        description: 'High-energy drops and builds',
    },
    {
        id: 'cinematic',
        imagePath: '/examples/cinematic.jpg',
        genre: Genre.CINEMATIC,
        genreLabel: 'Cinematic',
        description: 'Epic orchestral soundscapes',
    },
];

export default function Examples() {
    const router = useRouter();

    const handleExampleClick = (example: typeof EXAMPLES[0]) => {
        // Navigate to playground with the example image and genre
        router.push(`/playground?tab=playground&example=${example.id}&genre=${example.genre}`);
    };

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Sparkles className="w-6 h-6" />
                        Example Images
                    </CardTitle>
                    <CardDescription>
                        Click on any example to try it out in the playground with a preset genre
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        {EXAMPLES.map((example) => (
                            <div
                                key={example.id}
                                onClick={() => handleExampleClick(example)}
                                className="group cursor-pointer overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-md hover:shadow-xl transition-all duration-300 hover:scale-[1.02]"
                            >
                                <div className="relative aspect-[4/3] overflow-hidden">
                                    <img
                                        src={example.imagePath}
                                        alt={`${example.genreLabel} example`}
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                                    <div className="absolute bottom-0 left-0 right-0 p-4">
                                        <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-purple-600 text-white">
                                            {example.genreLabel}
                                        </span>
                                    </div>
                                </div>
                                <div className="p-4">
                                    <p className="text-sm text-gray-600 dark:text-gray-300">
                                        {example.description}
                                    </p>
                                    <p className="text-xs text-purple-600 dark:text-purple-400 mt-2 font-medium group-hover:text-purple-700 dark:group-hover:text-purple-300">
                                        Click to try this example →
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
