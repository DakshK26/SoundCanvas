// Types matching the gateway's GraphQL schema (gateway/src/schema.ts).

export enum GenerationStatus {
    PENDING = 'PENDING',       // waiting for the image upload
    QUEUED = 'QUEUED',         // on the SQS queue
    PROCESSING = 'PROCESSING', // the worker is making the song
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED',
}

export enum Genre {
    AUTO = 'AUTO', // frontend only: sent as "no genre" so the model picks
    EDM_CHILL = 'EDM_CHILL',
    EDM_DROP = 'EDM_DROP',
    RETROWAVE = 'RETROWAVE',
    CINEMATIC = 'CINEMATIC',
    HOUSE = 'HOUSE',
}

/** A genre a song can have: every Genre except AUTO. */
export type SongGenre = Exclude<Genre, Genre.AUTO>;

export const GENRE_LABELS: Record<SongGenre, string> = {
    [Genre.HOUSE]: 'House',
    [Genre.EDM_CHILL]: 'EDM Chill',
    [Genre.EDM_DROP]: 'EDM Drop',
    [Genre.RETROWAVE]: 'Retrowave',
    [Genre.CINEMATIC]: 'Cinematic',
};

/** True for the five genre names the API accepts, e.g. when read from a URL. */
export function isSongGenre(value: string | null): value is SongGenre {
    return value !== null && value in GENRE_LABELS;
}

export type Feedback = 'UP' | 'DOWN';
export type ImageType = 'JPEG' | 'PNG';

export interface Generation {
    id: string;
    status: GenerationStatus;
    genre: SongGenre | null;
    confidence: number | null; // null when the user picked the genre
    feedback: Feedback | null;
    imageUrl: string;
    audioUrl: string | null;
    errorMessage: string | null;
    createdAt: string;
}

/** A presigned S3 POST: send every field, then the file last, to url. */
export interface ImageUpload {
    url: string;
    fields: { name: string; value: string }[];
}
