// The GraphQL operations the UI runs. The fragment is the fields every screen needs for a job.

import { gql, TypedDocumentNode } from '@apollo/client';
import { Feedback, Generation, GenerationStatus, ImageType, ImageUpload, SongGenre } from '@/types/graphql';

const GENERATION_FIELDS = gql`
  fragment GenerationFields on Generation {
    id
    status
    genre
    confidence
    feedback
    imageUrl
    audioUrl
    errorMessage
    createdAt
  }
`;

export const CREATE_GENERATION: TypedDocumentNode<
    { createGeneration: { jobId: string; upload: ImageUpload } },
    { genre: SongGenre | null; imageType: ImageType }
> = gql`
  mutation CreateGeneration($genre: Genre, $imageType: ImageType!) {
    createGeneration(genre: $genre, imageType: $imageType) {
      jobId
      upload {
        url
        fields {
          name
          value
        }
      }
    }
  }
`;

export const START_GENERATION: TypedDocumentNode<
    { startGeneration: { id: string; status: GenerationStatus } },
    { jobId: string }
> = gql`
  mutation StartGeneration($jobId: ID!) {
    startGeneration(jobId: $jobId) {
      id
      status
    }
  }
`;

export const GET_GENERATION: TypedDocumentNode<{ generation: Generation | null }, { jobId: string }> = gql`
  ${GENERATION_FIELDS}
  query Generation($jobId: ID!) {
    generation(jobId: $jobId) {
      ...GenerationFields
    }
  }
`;

export const MY_GENERATIONS: TypedDocumentNode<{ myGenerations: Generation[] }, { limit?: number }> = gql`
  ${GENERATION_FIELDS}
  query MyGenerations($limit: Int) {
    myGenerations(limit: $limit) {
      ...GenerationFields
    }
  }
`;

export const RATE_GENERATION: TypedDocumentNode<
    { rateGeneration: { id: string; feedback: Feedback | null } },
    { jobId: string; feedback: Feedback }
> = gql`
  mutation RateGeneration($jobId: ID!, $feedback: Feedback!) {
    rateGeneration(jobId: $jobId, feedback: $feedback) {
      id
      feedback
    }
  }
`;
