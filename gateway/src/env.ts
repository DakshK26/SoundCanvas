// Reads required settings from environment variables. ECS injects them from
// Terraform; a missing one stops the process at startup.
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing environment variable ${name}`);
  return value;
}
