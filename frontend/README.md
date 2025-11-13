# SoundCanvas Frontend

React + Next.js + TypeScript + GraphQL frontend for SoundCanvas - AI-powered music generation from images.

## Tech Stack

- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **Apollo Client** for GraphQL
- **react-dropzone** for file uploads

## Features

### Landing Page
- Marketing homepage with feature highlights
- "Try it" CTA to Playground
- Responsive design

### Playground
- **Image Upload**: Drag & drop or browse to select images
- **Genre Selection**: Choose from RAP, HOUSE, R&B, EDM_CHILL, EDM_DROP, or Auto
- **Mode Toggle**: ML Model vs Heuristic generation
- **Real-time Status**: Polls generation status every 2.5 seconds
- **Audio Player**: HTML5 audio player with track metadata
- **Download**: Save generated WAV files

### History
- **Track List**: View all past generations
- **Pagination**: Browse through history with Previous/Next
- **Quick Actions**: Play and download from history
- **Metadata Display**: Shows genre, tempo, creation date

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- GraphQL API endpoint (see `gateway` service)

### Installation

```bash
cd frontend
npm install
```

### Configuration

Create a `.env.local` file:

```bash
NEXT_PUBLIC_GRAPHQL_ENDPOINT=http://localhost:4000/graphql
```

For production:
```bash
NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://api.soundcanvas.yourdomain.com/graphql
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm run start
```

## Project Structure

```
frontend/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout with Apollo Provider
│   ├── page.tsx                  # Landing page
│   ├── playground/
│   │   └── page.tsx              # Playground with tabs
│   └── globals.css               # Global styles
├── components/
│   ├── ui/                       # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── select.tsx
│   │   ├── table.tsx
│   │   ├── tabs.tsx
│   │   └── spinner.tsx
│   ├── ApolloProvider.tsx        # Apollo Client wrapper
│   ├── AudioPlayer.tsx           # Audio playback component
│   ├── History.tsx               # Generation history view
│   └── Playground.tsx            # Main upload & generate UI
├── graphql/
│   └── operations.ts             # GraphQL queries & mutations
├── lib/
│   ├── apollo-client.ts          # Apollo Client config
│   └── utils.ts                  # Utility functions
├── types/
│   └── graphql.ts                # TypeScript types for GraphQL
└── .env.local                    # Environment variables
```

## GraphQL Operations

### Mutations

- **createGeneration**: Initialize generation and get S3 upload URL
- **startGeneration**: Trigger processing after image upload

### Queries

- **generationStatus**: Poll for completion status
- **myGenerations**: Fetch user's generation history

## Flow

1. **User uploads image** → `createGeneration` mutation returns `jobId` and `imageUploadUrl`
2. **Frontend uploads image to S3** → Direct PUT to pre-signed URL
3. **Frontend calls** `startGeneration(jobId)` → Triggers backend processing
4. **Poll** `generationStatus(jobId)` every 2.5s until status = COMPLETE
5. **Display audio player** with pre-signed S3 audio URL
6. **User downloads WAV** or views in History

## Deployment

### Option 1: Vercel (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel
```

Set `NEXT_PUBLIC_GRAPHQL_ENDPOINT` in Vercel environment variables.

### Option 2: AWS S3 + CloudFront

```bash
# Build
npm run build

# Deploy to S3
aws s3 sync out/ s3://your-bucket-name --delete

# Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

### Option 3: Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_GRAPHQL_ENDPOINT` | GraphQL API URL | `https://api.soundcanvas.com/graphql` |

## License

See parent project LICENSE.
