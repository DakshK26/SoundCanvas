// Structured logs: one JSON object per line. CloudWatch Logs Insights can then
// filter and aggregate on fields, e.g. average `ms` per `step`, or every line for one `jobId`.
type Fields = Record<string, unknown>;

function write(level: "info" | "warn" | "error", message: string, fields: Fields): void {
  console.log(JSON.stringify({ time: new Date().toISOString(), level, message, ...fields }));
}

export const log = {
  info: (message: string, fields: Fields = {}) => write("info", message, fields),
  warn: (message: string, fields: Fields = {}) => write("warn", message, fields),
  error: (message: string, fields: Fields = {}) => write("error", message, fields),
};
