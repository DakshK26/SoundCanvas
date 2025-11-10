import { Query } from "./Query";
import { Mutation } from "./Mutation";
import { UploadScalar } from "./Upload";

export const resolvers = {
  Upload: UploadScalar,
  Query,
  Mutation,
};
