# Phase 10 - Person A Implementation Guide

## ✅ Completed Implementation

This document describes the **Person A (Frontend)** implementation for Phase 10 of the SoundCanvas project.

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **GraphQL Client**: Apollo Client 3.x
- **File Upload**: react-dropzone

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx                    # Root layout with Apollo Provider
│   ├── page.tsx                      # Landing/marketing page
│   ├── playground/
│   │   └── page.tsx                  # Main app page with tabs
│   └── globals.css
├── components/
│   ├── ui/                           # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── select.tsx
│   │   ├── table.tsx
│   │   ├── tabs.tsx
│   │   └── spinner.tsx
│   ├── ApolloProvider.tsx            # Apollo Client provider wrapper
│   ├── AudioPlayer.tsx               # Audio playback with metadata
│   ├── History.tsx                   # Generation history view
│   └── Playground.tsx                # Upload + generation UI
├── graphql/
│   └── operations.ts                 # All GraphQL queries/mutations
├── lib/
│   ├── apollo-client.ts              # Apollo Client configuration
│   └── utils.ts                      # shadcn utilities
├── types/
│   └── graphql.ts                    # TypeScript types for GraphQL
└── .env.local                        # Environment configuration
```

## Features Implemented

### ✅ A1. Project Setup

- [x] Next.js 14 with TypeScript and Tailwind
- [x] Apollo Client 3.x for GraphQL
- [x] react-dropzone for file uploads
- [x] shadcn/ui components (button, card, select, table, tabs, spinner)
- [x] Environment configuration (.env.local)

### ✅ A2. Core Screens & Flows

#### Landing Page (`app/page.tsx`)
- [x] Hero section with marketing copy
- [x] Feature highlights (3-column grid)
- [x] "How It Works" section (4-step process)
- [x] CTA buttons to Playground
- [x] Responsive design with gradient background

#### Playground (`components/Playground.tsx`)
- [x] **Image Upload Area**
  - Drag & drop support
  - Click to browse
  - Image preview thumbnail
  - File type validation (PNG, JPG, JPEG, WebP)
  
- [x] **Controls**
  - Genre dropdown: Auto / RAP / HOUSE / RNB / EDM_CHILL / EDM_DROP
  - Mode toggle: ML Model / Heuristic
  
- [x] **Generate Button**
  - Calls `createGeneration` mutation
  - Gets pre-signed S3 upload URL
  - Uploads image directly to S3
  - Calls `startGeneration` mutation
  - Starts polling `generationStatus`
  
- [x] **Status Polling**
  - Polls every 2.5 seconds
  - Auto-cleanup after 5 minutes
  - Shows loading spinner during PENDING/RUNNING
  
- [x] **Audio Player**
  - HTML5 audio element
  - Pre-signed S3 URL streaming
  - Displays metadata: genre, tempo, scale, mood
  - Download WAV button
  
- [x] **Error Handling**
  - Upload failures
  - Generation failures
  - Network errors

#### History (`components/History.tsx`)
- [x] **Table View**
  - Image thumbnail
  - Creation date
  - Genre badge
  - Tempo (BPM)
  - Play/Download actions
  
- [x] **Pagination**
  - 10 items per page
  - Previous/Next buttons
  
- [x] **Actions**
  - Play audio in browser
  - Download WAV file

### ✅ A3. GraphQL Client Wiring

#### Apollo Client Configuration (`lib/apollo-client.ts`)
- [x] HTTP Link to GraphQL endpoint
- [x] InMemoryCache
- [x] Network-only fetch policy (no stale data)

#### GraphQL Operations (`graphql/operations.ts`)

**Mutations:**
```graphql
createGeneration(input: CreateGenerationInput!)
  → jobId, imageUploadUrl, imageId

startGeneration(jobId: ID!)
  → Generation object with status
```

**Queries:**
```graphql
generationStatus(jobId: ID!)
  → status, audioUrl, imageUrl, params, errorMessage

myGenerations(limit: Int!, offset: Int!)
  → [Generation] array
```

#### TypeScript Types (`types/graphql.ts`)
- [x] Enums: GenerationStatus, Genre, Mode
- [x] Interfaces: CreateGenerationInput, GenerationParams, Generation
- [x] Full type safety across components

### ✅ A4. State & UX Polish

- [x] **Loading States**
  - Disabled Generate button during upload
  - Spinner with "Uploading image..." / "Composing your track..."
  
- [x] **Error Handling**
  - User-friendly error messages
  - Failed status handling
  - Network error recovery
  
- [x] **Responsive Layout**
  - Mobile-first design
  - Single column on mobile
  - Grid layouts on desktop
  - Sticky header navigation

### ✅ A5. Frontend Build & Deploy

#### NPM Scripts
```json
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint"
}
```

#### Build Output
- Artifacts in `.next/` for Node.js deployment
- Can export to `out/` for static hosting

## Generation Flow (Implemented)

```
1. User uploads image via drag-drop or browse
   ↓
2. createGeneration() mutation
   ← Returns: { jobId, imageUploadUrl, imageId }
   ↓
3. Frontend uploads image to S3 (PUT to imageUploadUrl)
   ↓
4. startGeneration(jobId) mutation
   ← Triggers backend processing
   ↓
5. Poll generationStatus(jobId) every 2.5s
   ← Returns: { status, audioUrl, params, errorMessage }
   ↓
6. When status === COMPLETE:
   - Display AudioPlayer with audioUrl
   - Show metadata (genre, tempo, scale, mood)
   - Enable download button
   ↓
7. User plays audio or downloads WAV
```

## Environment Configuration

Create `frontend/.env.local`:

```bash
# Development
NEXT_PUBLIC_GRAPHQL_ENDPOINT=http://localhost:4000/graphql

# Production (update after Person B deploys)
# NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://api.soundcanvas.yourdomain.com/graphql
```

## Running the Frontend

### Development Mode
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000

### Production Build
```bash
npm run build
npm run start
```

### Testing Locally (Without Backend)
The frontend is built and ready. To test:
1. Run `npm run dev`
2. Navigate to landing page (localhost:3000)
3. Click "Try it Free" → opens Playground
4. Upload an image (UI works, GraphQL calls will fail until backend is ready)

## Integration with Person B (Gateway)

### Required GraphQL Schema (Person B must implement)

```graphql
type Mutation {
  createGeneration(input: CreateGenerationInput!): CreateGenerationPayload!
  startGeneration(jobId: ID!): Generation!
}

type Query {
  generationStatus(jobId: ID!): GenerationStatusResponse!
  myGenerations(limit: Int!, offset: Int!): [Generation!]!
}

input CreateGenerationInput {
  genreOverride: String
  mode: String
}

type CreateGenerationPayload {
  jobId: ID!
  imageUploadUrl: String!
  imageId: ID!
}

type GenerationStatusResponse {
  status: GenerationStatus!
  audioUrl: String
  imageUrl: String
  params: GenerationParams
  errorMessage: String
}

type GenerationParams {
  genre: String!
  tempoBpm: Float!
  mood: String
  scaleType: String
}

type Generation {
  id: ID!
  userId: ID
  imageKey: String!
  audioKey: String
  genre: String!
  tempoBpm: Float!
  status: GenerationStatus!
  errorMessage: String
  createdAt: String!
  imageUrl: String
  audioUrl: String
}

enum GenerationStatus {
  PENDING
  RUNNING
  COMPLETE
  FAILED
}
```

### CORS Configuration (Person B)
Gateway must allow:
```javascript
{
  origin: ['http://localhost:3000', 'https://soundcanvas.yourdomain.com'],
  credentials: true
}
```

### S3 Pre-signed URLs (Person B)
- `createGeneration` returns **PUT** URL for image upload
- `generationStatus` returns **GET** URL for audio download
- Expiration: 15-60 minutes recommended

## Deployment Options

### Option 1: Vercel (Recommended)
```bash
npm install -g vercel
vercel
```
Set env var: `NEXT_PUBLIC_GRAPHQL_ENDPOINT`

### Option 2: AWS S3 + CloudFront
```bash
npm run build
aws s3 sync .next/static s3://bucket/static
# Configure CloudFront distribution
```

### Option 3: Docker + ECS
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## Key Implementation Decisions

1. **Direct S3 Upload**: Frontend uploads images directly to S3 using pre-signed URLs (reduces server load)
2. **Polling vs WebSockets**: Used polling for simplicity (can upgrade to WebSockets later)
3. **Client-Side Only**: Apollo Client runs only in browser (no SSR for GraphQL)
4. **Network-Only Fetch**: Prevents stale data from cache
5. **shadcn/ui**: Provides high-quality, accessible components without bloat

## Next Steps for Person A

1. ✅ Frontend implementation complete
2. ⏳ Wait for Person B to deploy GraphQL gateway
3. ⏳ Update `.env.local` with production GraphQL endpoint
4. ⏳ Test end-to-end flow
5. ⏳ Deploy frontend to Vercel/AWS

## Testing Checklist (Once Backend is Ready)

- [ ] Landing page loads correctly
- [ ] Navigation to Playground works
- [ ] Image upload (drag & drop)
- [ ] Image upload (click browse)
- [ ] Genre selection changes
- [ ] Mode toggle works
- [ ] Generate button disabled without image
- [ ] Generate button creates generation
- [ ] Image uploads to S3 successfully
- [ ] Status polling starts
- [ ] Audio player appears when complete
- [ ] Audio playback works
- [ ] Download button downloads WAV
- [ ] History tab loads past generations
- [ ] History pagination works
- [ ] Play/download from history works
- [ ] Error handling for failed generations
- [ ] Mobile responsive layout
- [ ] Error messages display correctly

## Support & Troubleshooting

### Common Issues

**GraphQL Connection Failed**
- Check `NEXT_PUBLIC_GRAPHQL_ENDPOINT` in `.env.local`
- Verify gateway is running
- Check browser console for CORS errors

**Image Upload Fails**
- Verify S3 bucket CORS allows PUT from frontend domain
- Check pre-signed URL expiration
- Ensure file size < 10MB

**Audio Not Playing**
- Check S3 audio URL CORS allows GET
- Verify WAV file is valid
- Check browser audio codec support

## Files Summary

| File | Purpose | Lines |
|------|---------|-------|
| `app/layout.tsx` | Root layout + Apollo Provider | ~40 |
| `app/page.tsx` | Landing page | ~140 |
| `app/playground/page.tsx` | Playground page with tabs | ~60 |
| `components/Playground.tsx` | Main upload/generate UI | ~280 |
| `components/AudioPlayer.tsx` | Audio playback component | ~80 |
| `components/History.tsx` | Generation history | ~180 |
| `components/ApolloProvider.tsx` | Apollo wrapper | ~10 |
| `graphql/operations.ts` | GraphQL queries/mutations | ~50 |
| `lib/apollo-client.ts` | Apollo Client config | ~20 |
| `types/graphql.ts` | TypeScript types | ~60 |
| **Total** | | **~920 lines** |

## Conclusion

Person A (Frontend) implementation is **100% complete** and ready for integration with Person B's backend. The app provides a polished, professional UI for image-to-music generation with full error handling, responsive design, and smooth UX.

**Ready for Person B to:**
1. Implement GraphQL schema
2. Set up S3 buckets
3. Deploy gateway to AWS
4. Provide production GraphQL endpoint
