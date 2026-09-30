// Called at module load, so a missing setting stops the process at start-up instead of on first use.
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing environment variable ${name}`);
  return value;
}
