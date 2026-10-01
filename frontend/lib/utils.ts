// shadcn helper: join class names and let Tailwind merge conflicting ones, so cn('p-2', 'p-4')
// gives just 'p-4'. The components in components/ui/ use it to accept a className override.

import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
