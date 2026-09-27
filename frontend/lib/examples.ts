// The example images and their pre-rendered songs in /public/examples.
// Each example's files are named after its id: <id>.jpg and <id>.wav.
import { Genre, SongGenre } from '@/types/graphql';

export interface Example {
    id: string;
    genre: SongGenre;
    description: string;
    color: string; // the genre badge colour
}

export const EXAMPLES: Example[] = [
    { id: 'cinematic', genre: Genre.CINEMATIC, description: 'Epic orchestral soundscapes', color: '#3D405B' },
    { id: 'edm_chill', genre: Genre.EDM_CHILL, description: 'Relaxing electronic vibes', color: '#81B29A' },
    { id: 'edm_drop', genre: Genre.EDM_DROP, description: 'High-energy drops and builds', color: '#F2CC8F' },
    { id: 'house', genre: Genre.HOUSE, description: 'Energetic beats for the dance floor', color: '#E07A5F' },
];

export const findExample = (id: string | null) => EXAMPLES.find((example) => example.id === id);
export const exampleImage = (id: string) => `/examples/${id}.jpg`;
export const exampleSong = (id: string) => `/examples/${id}.wav`;
