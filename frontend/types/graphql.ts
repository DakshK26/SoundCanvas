// GraphQL Types

export enum GenerationStatus {
    PENDING = 'PENDING',
    RUNNING = 'RUNNING',
    COMPLETE = 'COMPLETE',
    FAILED = 'FAILED',
}

export enum Genre {
    AUTO = 'AUTO',
    RAP = 'RAP',
    HOUSE = 'HOUSE',
    RNB = 'RNB',
    EDM_CHILL = 'EDM_CHILL',
    EDM_DROP = 'EDM_DROP',
}

export enum Mode {
    MODEL = 'model',
    HEURISTIC = 'heuristic',
}

export interface CreateGenerationInput {
    genreOverride?: string;
    mode?: string;
}

export interface CreateGenerationPayload {
    jobId: string;
    imageUploadUrl: string;
    imageId: string;
}

export interface GenerationParams {
    genre: string;
    tempoBpm: number;
    mood?: string;
    scaleType?: string;
}

export interface GenerationStatusResponse {
    status: GenerationStatus;
    audioUrl?: string;
    imageUrl?: string;
    params?: GenerationParams;
    errorMessage?: string;
}

export interface Generation {
    id: string;
    userId?: string;
    imageKey: string;
    audioKey?: string;
    genre: string;
    tempoBpm: number;
    status: GenerationStatus;
    errorMessage?: string;
    createdAt: string;
    imageUrl?: string;
    audioUrl?: string;
}
