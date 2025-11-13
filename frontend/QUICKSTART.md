# Frontend Local Development Quick Start

## Prerequisites
- Node.js 20+ installed
- Gateway backend running on port 4000

## Setup Steps

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment
```bash
# Copy the example file
cp .env.example .env.local

# The default configuration points to localhost:4000
# No changes needed for local development
```

### 3. Start Development Server
```bash
npm run dev
```

Frontend will be available at: **http://localhost:3000**

### 4. Verify GraphQL Connection
The app should automatically connect to `http://localhost:4000/graphql`.

If you see connection errors:
1. Make sure gateway is running: `cd ../gateway && npm run dev`
2. Check gateway logs for errors
3. Verify Apollo Client endpoint in browser console

## Testing the Flow

### Happy Path Test:
1. Navigate to http://localhost:3000/playground
2. Drag/drop or select an image (any JPG/PNG)
3. Select genre (or leave as "Auto")
4. Click "Generate Track"
5. Watch status progress: PENDING → RUNNING → COMPLETE
6. Play the generated audio
7. Check History tab - your generation should appear

### Expected Behavior:
- ✅ Image uploads directly to S3 (no gateway proxy)
- ✅ Status polls every 2.5 seconds
- ✅ Audio player appears when complete
- ✅ History shows all generations with thumbnails

### Error Testing:
1. **Network Error:** Stop gateway → Try generating → See error banner
2. **Invalid Image:** Upload non-image file → See validation error
3. **Backend Failure:** (After Person B implements) Bad image → See "Generation failed" with error message

## Production Build Test

```bash
npm run build
```

Should output:
```
✓ Compiled successfully
✓ Finished TypeScript
✓ Collecting page data
✓ Generating static pages (5/5)
✓ Finalizing page optimization
```

## Environment Variables

### Local Development (.env.local)
```env
NEXT_PUBLIC_GRAPHQL_ENDPOINT=http://localhost:4000/graphql
NEXT_PUBLIC_APP_ENV=development
```

### Production (.env.production)
```env
NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://api.soundcanvas.yourdomain.com/graphql
NEXT_PUBLIC_APP_ENV=production
```

## Troubleshooting

### "Network Error" banner appears
- **Cause:** Gateway not running or wrong endpoint
- **Fix:** Start gateway with `cd ../gateway && npm run dev`
- **Verify:** Visit http://localhost:4000/graphql in browser

### "Failed to upload image" error
- **Cause:** S3 pre-signed URL expired or invalid
- **Fix:** Check gateway logs for S3 client errors
- **Verify:** Ensure `USE_S3=true` and credentials in gateway/.env

### Build fails with TypeScript errors
- **Cause:** Type mismatches between frontend and backend
- **Fix:** Run `npm run build` and check error messages
- **Verify:** GraphQL schema matches operations.ts

### Audio doesn't play
- **Cause:** Pre-signed URL expired (1-hour expiry)
- **Fix:** Refresh history to get new URLs
- **Verify:** Check Network tab for 403 errors on S3 URLs

## Next Steps

Once Person B deploys AWS infrastructure:
1. Update `NEXT_PUBLIC_GRAPHQL_ENDPOINT` to production URL
2. Deploy frontend to Vercel or S3+CloudFront
3. Run production smoke tests (see PHASE11_PERSON_A_COMPLETE.md)

---

Frontend is ready! 🎨→🎵
