// examples = images + songs already rendered, sitting in /public/examples.
// naming: <id>.jpg + <id>.wav (so adding one = drop in 2 files + a line here)
import { Genre, SongGenre } from '@/types/graphql';

export interface Example {
    id: string;
    genre: SongGenre;
    description: string;
    color: string; // badge colour
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
