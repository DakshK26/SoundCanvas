// Hand-written copies of the types in api/src/schema.ts; keep them in sync.

export enum GenerationStatus {
    PENDING = 'PENDING',
    QUEUED = 'QUEUED',
    PROCESSING = 'PROCESSING',
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED',
}

export enum Genre {
    AUTO = 'AUTO', // frontend only, sent as null so the model picks
    EDM_CHILL = 'EDM_CHILL',
    EDM_DROP = 'EDM_DROP',
    CINEMATIC = 'CINEMATIC',
    HOUSE = 'HOUSE',
}

export type SongGenre = Exclude<Genre, Genre.AUTO>;

export const GENRE_LABELS: Record<SongGenre, string> = {
    [Genre.HOUSE]: 'House',
    [Genre.EDM_CHILL]: 'EDM Chill',
    [Genre.EDM_DROP]: 'EDM Drop',
    [Genre.CINEMATIC]: 'Cinematic',
};

export function isSongGenre(value: string | null): value is SongGenre {
    return value !== null && value in GENRE_LABELS;
}

export type ImageType = 'JPEG' | 'PNG';

export interface Generation {
    id: string;
    status: GenerationStatus;
    genre: SongGenre | null;
    confidence: number | null;
    imageUrl: string;
    audioUrl: string | null;
    errorMessage: string | null;
    createdAt: string;
}

export interface ImageUpload {
    url: string;
    fields: { name: string; value: string }[];
}
