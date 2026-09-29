// Must match the genre names in cpp-core, ml and audio-producer; ml/tests checks this.
export const GENRES = ["EDM_CHILL", "EDM_DROP", "RETROWAVE", "CINEMATIC", "HOUSE"] as const;
export type Genre = (typeof GENRES)[number];

export const typeDefs = `#graphql
  enum Genre { ${GENRES.join(" ")} }
  enum ImageType { JPEG PNG }
  enum Feedback { UP DOWN }
  enum Status { PENDING QUEUED PROCESSING COMPLETED FAILED }

  type Generation {
    id: ID!
    status: Status!
    genre: Genre
    confidence: Float
    feedback: Feedback
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

  type Mutation {
    createGeneration(genre: Genre, imageType: ImageType!): NewGeneration!
    startGeneration(jobId: ID!): Generation!
    rateGeneration(jobId: ID!, feedback: Feedback!): Generation!
  }
`;
