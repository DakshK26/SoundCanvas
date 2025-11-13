import { gql } from "apollo-server-express";

export const typeDefs = gql`
  scalar Upload

  # ============================================================================
  # Phase 5: Legacy Types (Backward Compatible)
  # ============================================================================
  
  enum SoundMode {
    HEURISTIC
    MODEL
  }

  type SoundParams {
    tempoBpm: Float!
    baseFrequency: Float!
    brightness: Float!
    volume: Float!
    durationSeconds: Float!
  }

  type SoundGeneration {
    id: ID!
    imagePath: String!
    audioPath: String!
    mode: SoundMode!
    params: SoundParams!
    createdAt: String!
  }

  # ============================================================================
  # Phase 10: New S3-Based Generation Types
  # ============================================================================

  enum GenerationStatus {
    PENDING
    RUNNING
    COMPLETE
    FAILED
  }

  type GenerationParams {
    genre: String!
    tempoBpm: Float!
    mood: String
    scaleType: String
  }

  type Generation {
    id: ID!
    userId: String
    imageKey: String!
    audioKey: String
    genre: String!
    tempoBpm: Float!
    status: GenerationStatus!
    errorMessage: String
    createdAt: String!
    imageUrl: String
    audioUrl: String
  }

  input CreateGenerationInput {
    genreOverride: String
    mode: String
  }

  type CreateGenerationPayload {
    jobId: ID!
    imageUploadUrl: String!
    imageId: String!
  }

  type GenerationStatusResponse {
    status: GenerationStatus!
    audioUrl: String
    imageUrl: String
    params: GenerationParams
    errorMessage: String
  }

  type MutationResponse {
    success: Boolean!
  }

  # ============================================================================
  # Queries and Mutations
  # ============================================================================

  type Query {
    # Phase 5: Legacy
    history(limit: Int = 20): [SoundGeneration!]!
    
    # Phase 10: New
    generationStatus(jobId: ID!): GenerationStatusResponse!
    myGenerations(limit: Int): [Generation!]!
  }

  type Mutation {
    # Phase 5: Legacy
    uploadAndGenerateSound(file: Upload!, mode: SoundMode!): SoundGeneration!
    
    # Phase 10: New
    createGeneration(input: CreateGenerationInput!): CreateGenerationPayload!
    startGeneration(jobId: ID!): MutationResponse!
  }
`;
