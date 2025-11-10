import { dbGetHistory } from "../db";

export const Query = {
  history: async (_: unknown, args: { limit?: number }) => {
    const limit = args.limit ?? 20;
    return dbGetHistory(limit);
  },
};
