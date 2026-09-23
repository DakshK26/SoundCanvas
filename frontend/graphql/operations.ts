// The GraphQL calls the frontend makes. A song is made in three steps:
// create a job (get an upload form), upload the image to S3 and start the job,
// then poll until it finishes.
import { gql } from '@apollo/client';

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

export const CREATE_GENERATION = gql`
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

export const START_GENERATION = gql`
  mutation StartGeneration($jobId: ID!) {
    startGeneration(jobId: $jobId) {
      id
      status
    }
  }
`;

export const GET_GENERATION = gql`
  ${GENERATION_FIELDS}
  query Generation($jobId: ID!) {
    generation(jobId: $jobId) {
      ...GenerationFields
    }
  }
`;

export const MY_GENERATIONS = gql`
  ${GENERATION_FIELDS}
  query MyGenerations($limit: Int) {
    myGenerations(limit: $limit) {
      ...GenerationFields
    }
  }
`;

export const RATE_GENERATION = gql`
  mutation RateGeneration($jobId: ID!, $feedback: Feedback!) {
    rateGeneration(jobId: $jobId, feedback: $feedback) {
      id
      feedback
    }
  }
`;
