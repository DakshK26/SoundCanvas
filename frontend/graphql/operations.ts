// Every GraphQL query and mutation the frontend sends, in one place. Playground.tsx and
// GenerationHistory.tsx import these and run them through the client in lib/apolloClient.ts.
// The API answers each one in api/src/resolvers.ts, using the schema in api/src/schema.ts.

import { gql, TypedDocumentNode } from '@apollo/client';
import { Generation, GenerationStatus, ImageType, ImageUpload, SongGenre } from '@/types/graphql';

// A fragment is a named list of fields that queries can paste in with ...GenerationFields.
// Both queries below use it, so the polled generation and the history rows always have the
// same shape, which is the Generation interface in types/graphql.ts.
const GENERATION_FIELDS = gql`
  fragment GenerationFields on Generation {
    id
    status
    genre
    confidence
    imageUrl
    audioUrl
    errorMessage
    createdAt
  }
`;

// TypedDocumentNode<Result, Variables> tells TypeScript what each operation returns and which
// variables it needs, so useMutation and useQuery are typed without extra generics.

// Step one of a new generation. Called by generate() in Playground.tsx and answered by
// Mutation.createGeneration in api/src/resolvers.ts. It makes the PENDING row and returns its id
// plus a presigned S3 form for the image. A null genre means "let the model pick".
export const CREATE_GENERATION: TypedDocumentNode<
    { createGeneration: { id: string; upload: ImageUpload } },
    { genre: SongGenre | null; imageType: ImageType }
> = gql`
  mutation CreateGeneration($genre: Genre, $imageType: ImageType!) {
    createGeneration(genre: $genre, imageType: $imageType) {
      id
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

// Step two, sent after the image is in S3. Called by generate() in Playground.tsx and answered
// by Mutation.startGeneration in api/src/resolvers.ts, which checks the upload and puts a job on
// the SQS queue. The generation comes back as QUEUED.
export const START_GENERATION: TypedDocumentNode<
    { startGeneration: { id: string; status: GenerationStatus } },
    { id: string }
> = gql`
  mutation StartGeneration($id: ID!) {
    startGeneration(id: $id) {
      id
      status
    }
  }
`;

// One generation by id. Playground.tsx polls this in pollUntilDone() until the status is
// COMPLETED or FAILED. Answered by Query.generation in api/src/resolvers.ts, which returns null
// for an id that belongs to another browser.
export const GET_GENERATION: TypedDocumentNode<{ generation: Generation | null }, { id: string }> = gql`
  ${GENERATION_FIELDS}
  query Generation($id: ID!) {
    generation(id: $id) {
      ...GenerationFields
    }
  }
`;

// This browser's recent generations, newest first. Used by GenerationHistory.tsx for the History
// tab and answered by Query.myGenerations in api/src/resolvers.ts. Which browser is asking comes
// from the X-Client-Id header, not from a variable.
export const MY_GENERATIONS: TypedDocumentNode<{ myGenerations: Generation[] }, { limit?: number }> = gql`
  ${GENERATION_FIELDS}
  query MyGenerations($limit: Int) {
    myGenerations(limit: $limit) {
      ...GenerationFields
    }
  }
`;
