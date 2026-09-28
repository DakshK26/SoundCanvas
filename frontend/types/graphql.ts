// hand-written copies of the types in gateway/src/schema.ts. if the schema changes, change these too
// TODO(maybe): graphql-codegen so these can't drift

export enum GenerationStatus {
    PENDING = 'PENDING',       // row exists, image not uploaded yet
    QUEUED = 'QUEUED',         // sitting in SQS
    PROCESSING = 'PROCESSING', // a worker picked it up
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED',
}

export enum Genre {
    AUTO = 'AUTO', // frontend only! gets sent as null -> model picks
    EDM_CHILL = 'EDM_CHILL',
    EDM_DROP = 'EDM_DROP',
    RETROWAVE = 'RETROWAVE',
    CINEMATIC = 'CINEMATIC',
    HOUSE = 'HOUSE',
}

// what a finished song can actually be (AUTO is only for requests)
export type SongGenre = Exclude<Genre, Genre.AUTO>;

export const GENRE_LABELS: Record<SongGenre, string> = {
    [Genre.HOUSE]: 'House',
    [Genre.EDM_CHILL]: 'EDM Chill',
    [Genre.EDM_DROP]: 'EDM Drop',
    [Genre.RETROWAVE]: 'Retrowave',
    [Genre.CINEMATIC]: 'Cinematic',
};

// type guard for untrusted strings, e.g. ?genre= in the url
export function isSongGenre(value: string | null): value is SongGenre {
    return value !== null && value in GENRE_LABELS;
}

export type Feedback = 'UP' | 'DOWN';
export type ImageType = 'JPEG' | 'PNG';

export interface Generation {
    id: string;
    status: GenerationStatus;
    genre: SongGenre | null;
    confidence: number | null; // null if the user picked
    feedback: Feedback | null;
    imageUrl: string;
    audioUrl: string | null;
    errorMessage: string | null;
    createdAt: string;
}

// presigned S3 POST. send all the fields, file goes LAST
export interface ImageUpload {
    url: string;
    fields: { name: string; value: string }[];
}
