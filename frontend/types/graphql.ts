// The TypeScript types for the GraphQL API. They are hand-written copies of api/src/schema.ts,
// so a change to the schema has to be made here too. graphql/operations.ts uses them to type each
// operation, and the components use them for props, state and genre labels.

// The life of a generation: PENDING waits for the image upload, QUEUED means a job is in SQS,
// PROCESSING means a worker has it, then COMPLETED or FAILED. The schema calls this enum Status.
export enum GenerationStatus {
    PENDING = 'PENDING',
    QUEUED = 'QUEUED',
    PROCESSING = 'PROCESSING',
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED',
}

// The schema's Genre enum plus AUTO, which only exists so the genre dropdown has a default.
export enum Genre {
    AUTO = 'AUTO', // frontend only, sent as null so the model picks
    EDM_CHILL = 'EDM_CHILL',
    EDM_DROP = 'EDM_DROP',
    CINEMATIC = 'CINEMATIC',
    HOUSE = 'HOUSE',
}

// A real genre the API accepts, which is every Genre except AUTO.
export type SongGenre = Exclude<Genre, Genre.AUTO>;

// Display names for the dropdown and example cards. Record<SongGenre, ...> makes TypeScript
// complain if a genre is added to the enum without a label here.
export const GENRE_LABELS: Record<SongGenre, string> = {
    [Genre.HOUSE]: 'House',
    [Genre.EDM_CHILL]: 'EDM Chill',
    [Genre.EDM_DROP]: 'EDM Drop',
    [Genre.CINEMATIC]: 'Cinematic',
};

// Checks an untrusted string, like the genre URL param in app/playground/page.tsx. The
// "value is SongGenre" return type lets TypeScript treat it as a SongGenre after the check.
export function isSongGenre(value: string | null): value is SongGenre {
    return value !== null && value in GENRE_LABELS;
}

// The two upload formats the API will sign an S3 form for.
export type ImageType = 'JPEG' | 'PNG';

// One generation as the API returns it, matching the GenerationFields fragment in
// graphql/operations.ts. imageUrl and audioUrl are presigned S3 links that expire, and
// confidence is null when the user chose the genre instead of the model.
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

// A presigned S3 POST form from createGeneration. Playground.tsx posts the fields and then the
// file to url, so the image goes straight to S3 without passing through the API.
export interface ImageUpload {
    url: string;
    fields: { name: string; value: string }[];
}
