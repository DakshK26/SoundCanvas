// env vars come from the ECS task def (terraform) or docker-compose locally.
// crash on startup if one's missing - way better than a weird undefined error mid-job
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing environment variable ${name}`);
  return value;
}
