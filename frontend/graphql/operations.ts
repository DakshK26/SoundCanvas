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
      success
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
  query MyGenerations($limit: Int) {
    myGenerations(limit: $limit) {
      id
      userId
      imageKey
      audioKey
      genre
      tempoBpm
      status
      errorMessage
      createdAt
      imageUrl
      audioUrl
    }
  }
`;
