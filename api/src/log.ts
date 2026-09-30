// One JSON line per event. ECS ships stdout to CloudWatch, and Logs Insights can then filter and
// group on fields like generationId, step and ms.
type Fields = Record<string, unknown>;

function write(level: "info" | "warn" | "error", message: string, fields: Fields): void {
  console.log(JSON.stringify({ time: new Date().toISOString(), level, message, ...fields }));
}

export const log = {
  info: (message: string, fields: Fields = {}) => write("info", message, fields),
  warn: (message: string, fields: Fields = {}) => write("warn", message, fields),
  error: (message: string, fields: Fields = {}) => write("error", message, fields),
};
