import { gql } from '@apollo/client';

export const CREATE_GENERATION = gql`
  mutation CreateGeneration($input: CreateGenerationInput!) {
    createGeneration(input: $input) {
      jobId
      imageUploadUrl
      imageId
    }
  }
`;

export const START_GENERATION = gql`
  mutation StartGeneration($jobId: ID!) {
    startGeneration(jobId: $jobId) {
      id
      status
      genre
      tempoBpm
    }
  }
`;

export const GENERATION_STATUS = gql`
  query GenerationStatus($jobId: ID!) {
    generationStatus(jobId: $jobId) {
      status
      audioUrl
      imageUrl
      params {
        genre
        tempoBpm
        mood
        scaleType
      }
      errorMessage
    }
  }
`;

export const MY_GENERATIONS = gql`
  query MyGenerations($limit: Int!, $offset: Int!) {
    myGenerations(limit: $limit, offset: $offset) {
      id
      createdAt
      genre
      tempoBpm
      imageUrl
      audioUrl
    }
  }
`;
