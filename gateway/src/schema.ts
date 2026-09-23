// The GraphQL API the frontend talks to.
export const typeDefs = `#graphql
  enum Genre { EDM_CHILL EDM_DROP RETROWAVE CINEMATIC HOUSE }

  "PENDING: waiting for the image upload. QUEUED: in SQS. PROCESSING: the worker has it."
  enum Status { PENDING QUEUED PROCESSING COMPLETED FAILED }

  type Generation {
    id: ID!
    status: Status!
    genre: Genre
    "How sure the model was, 0 to 1. Null when the user picked the genre."
    confidence: Float
    imageUrl: String!
    "Set once the status is COMPLETED."
    audioUrl: String
    errorMessage: String
    createdAt: String!
  }

  type NewGeneration {
    jobId: ID!
    "Presigned S3 URL. PUT the image here, then call startGeneration."
    uploadUrl: String!
  }

  type Query {
    generation(jobId: ID!): Generation
  }

  type Mutation {
    "Leave genre empty to let the model choose."
    createGeneration(genre: Genre): NewGeneration!
    startGeneration(jobId: ID!): Generation!
  }
`;
