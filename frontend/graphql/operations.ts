// The GraphQL operations the UI runs. The fragment holds the fields every screen shows.

import { gql, TypedDocumentNode } from '@apollo/client';
import { Generation, GenerationStatus, ImageType, ImageUpload, SongGenre } from '@/types/graphql';

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

export const GET_GENERATION: TypedDocumentNode<{ generation: Generation | null }, { id: string }> = gql`
  ${GENERATION_FIELDS}
  query Generation($id: ID!) {
    generation(id: $id) {
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
