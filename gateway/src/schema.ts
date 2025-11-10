import { gql } from "apollo-server-express";

export const typeDefs = gql`
  scalar Upload

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

  type Query {
    history(limit: Int = 20): [SoundGeneration!]!
  }

  type Mutation {
    uploadAndGenerateSound(file: Upload!, mode: SoundMode!): SoundGeneration!
  }
`;
