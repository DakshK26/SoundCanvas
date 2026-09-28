// the graphql schema the frontend uses.
// every request has an X-Client-Id header (anonymous uuid per browser) - history,
// ratings and the rate limit are all scoped to it

// NOTE: these 5 names are shared by every service (cpp, ml, audio). ml/tests checks they all match
export const GENRES = ["EDM_CHILL", "EDM_DROP", "RETROWAVE", "CINEMATIC", "HOUSE"] as const;
export type Genre = (typeof GENRES)[number];

export const typeDefs = `#graphql
  enum Genre { ${GENRES.join(" ")} }
  enum ImageType { JPEG PNG }
  enum Feedback { UP DOWN }

  "PENDING: waiting for the image upload. QUEUED: in SQS. PROCESSING: the worker has it."
  enum Status { PENDING QUEUED PROCESSING COMPLETED FAILED }

  type Generation {
    id: ID!
    status: Status!
    genre: Genre
    "How sure the model was, 0 to 1. Null when the user picked the genre."
    confidence: Float
    feedback: Feedback
    imageUrl: String!
    "Set once the status is COMPLETED."
    audioUrl: String
    errorMessage: String
    createdAt: String!
  }

  type FormField {
    name: String!
    value: String!
  }

  "A presigned S3 POST form: send the fields plus the file (last) to url."
  type ImageUpload {
    url: String!
    fields: [FormField!]!
  }

  type NewGeneration {
    jobId: ID!
    upload: ImageUpload!
  }

  type Query {
    generation(jobId: ID!): Generation
    "This browser's songs, newest first."
    myGenerations(limit: Int = 20): [Generation!]!
  }

  type Mutation {
    "Step 1. Leave genre empty to let the model choose."
    createGeneration(genre: Genre, imageType: ImageType!): NewGeneration!
    "Step 2, after uploading the image."
    startGeneration(jobId: ID!): Generation!
    "Thumbs up or down on a finished song; kept to retrain the model."
    rateGeneration(jobId: ID!, feedback: Feedback!): Generation!
  }
`;
