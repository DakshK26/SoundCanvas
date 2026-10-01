// The built-in examples. Each one is a photo and a song made from it ahead of time, stored as
// /public/examples/<id>.jpg and <id>.wav. Examples.tsx shows them as cards, app/playground/page.tsx
// checks the example URL param against this list, and Playground.tsx loads the photo and WAV.
import { Genre, SongGenre } from '@/types/graphql';

// The genre is the one the stored WAV was made with, and color tints the card's genre badge.
export interface Example {
    id: string;
    genre: SongGenre;
    description: string;
    color: string;
}

export const EXAMPLES: Example[] = [
    { id: 'cinematic', genre: Genre.CINEMATIC, description: 'Epic orchestral soundscapes', color: '#3D405B' },
    { id: 'edm_chill', genre: Genre.EDM_CHILL, description: 'Relaxing electronic vibes', color: '#81B29A' },
    { id: 'edm_drop', genre: Genre.EDM_DROP, description: 'High-energy drops and builds', color: '#F2CC8F' },
    { id: 'house', genre: Genre.HOUSE, description: 'Energetic beats for the dance floor', color: '#E07A5F' },
];

// Returns undefined for an unknown id, so a made-up example param in the URL is ignored.
// Next.js serves everything in /public from the site root, which is why the paths skip "public".
export const findExample = (id: string | null) => EXAMPLES.find((example) => example.id === id);
export const exampleImage = (id: string) => `/examples/${id}.jpg`;
export const exampleSong = (id: string) => `/examples/${id}.wav`;
