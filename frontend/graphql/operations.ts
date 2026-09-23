// The three GraphQL calls the Playground makes, in order:
// create a job, upload the image to S3 and start the job, then poll until it finishes.
import { gql } from '@apollo/client';

export const CREATE_GENERATION = gql`
  mutation CreateGeneration($genre: Genre) {
    createGeneration(genre: $genre) {
      jobId
      uploadUrl
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
  query Generation($jobId: ID!) {
    generation(jobId: $jobId) {
      id
      status
      genre
      confidence
      imageUrl
      audioUrl
      errorMessage
      createdAt
    }
  }
`;
