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

export type Feedback = 'UP' | 'DOWN';

export interface Generation {
    id: string;
    status: GenerationStatus;
    genre: string | null;
    confidence: number | null; // null when the user picked the genre
    feedback: Feedback | null;
    imageUrl: string;
    audioUrl: string | null;
    errorMessage: string | null;
    createdAt: string;
}
