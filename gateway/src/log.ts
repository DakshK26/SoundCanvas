// JSON lines logging. cloudwatch insights picks the fields up automatically so you can do
// stuff like `stats avg(ms) by step` or `filter jobId = "..."` - way nicer than grepping text
type Fields = Record<string, unknown>;

function write(level: "info" | "warn" | "error", message: string, fields: Fields): void {
  console.log(JSON.stringify({ time: new Date().toISOString(), level, message, ...fields }));
}

export const log = {
  info: (message: string, fields: Fields = {}) => write("info", message, fields),
  warn: (message: string, fields: Fields = {}) => write("warn", message, fields),
  error: (message: string, fields: Fields = {}) => write("error", message, fields),
};
