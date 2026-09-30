// The GraphQL contract between the browser and the API. frontend/types/graphql.ts is a
// hand-written copy of these types.

// Must match the genre names in cpp-core, ml and audio-producer; ml/tests checks this.
export const GENRES = ["EDM_CHILL", "EDM_DROP", "CINEMATIC", "HOUSE"] as const;
export type Genre = (typeof GENRES)[number];

export const typeDefs = `#graphql
  enum Genre { ${GENRES.join(" ")} }
  enum ImageType { JPEG PNG }
  # PENDING waits for the upload, QUEUED is in SQS, PROCESSING is with a worker.
  enum Status { PENDING QUEUED PROCESSING COMPLETED FAILED }

  type Generation {
    id: ID!
    status: Status!
    genre: Genre
    # null when the user picked the genre, so the model never ran
    confidence: Float
    imageUrl: String!
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
    myGenerations(limit: Int = 20): [Generation!]!
  }

  # Making a song is two calls: createGeneration, upload to S3, then startGeneration.
  type Mutation {
    # leaving genre out lets the model pick
    createGeneration(genre: Genre, imageType: ImageType!): NewGeneration!
    startGeneration(jobId: ID!): Generation!
  }
`;
