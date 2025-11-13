# Phase 12 - Regression Testing Plan

Complete test matrix for ensuring SoundCanvas stability and correctness.

---

## Test Matrix: Image Types × Genres

### Test Scenarios

Test all combinations of:

**Image Types (5):**
1. **A. Bright Outdoor** - Sunny landscape, beach, bright sky
2. **B. Dark Indoor** - Night scene, dark room, low light
3. **C. Blue Sea/Ocean** - Water-dominant, blue tones
4. **D. Abstract Colorful** - Abstract art, colorful patterns
5. **E. Random Object** - Meme, trash can, random object

**Genres (4 + Auto):**
1. Auto (AI decides)
2. RAP
3. HOUSE
4. RNB

**Total Test Cases:** 5 images × 5 genre settings = **25 test cases**

---

## Test Case Template

For each test case, verify:

### ✅ Success Criteria
- [ ] Image uploads successfully to S3
- [ ] Generation starts (status → RUNNING)
- [ ] Generation completes (status → COMPLETE)
- [ ] Audio file exists in S3
- [ ] Audio file size > 0 bytes
- [ ] Audio duration > 20 seconds
- [ ] Audio plays without errors
- [ ] No clipping or broken noise
- [ ] Genre label matches expected (not "auto" for completed jobs)
- [ ] History shows the generation
- [ ] History allows playback
- [ ] Download button works

### 📊 Data to Collect
- Job ID
- Start time
- Completion time
- Duration (seconds)
- Audio file size (MB)
- Tempo BPM
- Scale type
- Final genre (if Auto was selected)

---

## Detailed Test Cases

### A. Bright Outdoor Photos

#### A1. Bright Outdoor + Auto
**Expected:** Upbeat genre (HOUSE, EDM_DROP), higher tempo (120-140 BPM)

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio duration 20-60s
- [ ] Audio has energetic feel
- [ ] Genre is NOT "auto" (should be HOUSE or EDM)
- [ ] Playable from history

#### A2. Bright Outdoor + RAP
**Expected:** Rap beat, 80-110 BPM, trap elements

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio has rap beat characteristics
- [ ] Genre shows "RAP" in history
- [ ] Download works

#### A3. Bright Outdoor + HOUSE
**Expected:** Four-on-the-floor kick, 120-130 BPM

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio has house beat
- [ ] Genre shows "HOUSE"

#### A4. Bright Outdoor + RNB
**Expected:** Smooth R&B groove, 70-100 BPM

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio has R&B feel
- [ ] Genre shows "RNB"

---

### B. Dark Indoor Photos

#### B1. Dark Indoor + Auto
**Expected:** Chill/ambient genre (EDM_CHILL, RNB), slower tempo (60-100 BPM)

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio has chill/ambient feel
- [ ] Genre is NOT "auto" (should be EDM_CHILL or RNB)
- [ ] Lower tempo than bright images

#### B2. Dark Indoor + RAP
**Expected:** Dark trap beat, 70-90 BPM

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio has dark rap feel
- [ ] Genre shows "RAP"

#### B3. Dark Indoor + HOUSE
**Expected:** Deep house, 120-128 BPM

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio has deep house feel
- [ ] Genre shows "HOUSE"

#### B4. Dark Indoor + RNB
**Expected:** Smooth slow jam, 60-80 BPM

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio has slow R&B feel
- [ ] Genre shows "RNB"

---

### C. Blue Sea/Ocean

#### C1. Blue Sea + Auto
**Expected:** Chill/ambient (EDM_CHILL), 90-110 BPM, "watery" feel

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio has ambient/chill feel
- [ ] Genre is NOT "auto"

#### C2. Blue Sea + RAP
- [ ] Works without errors
- [ ] Audio plays

#### C3. Blue Sea + HOUSE
- [ ] Works without errors
- [ ] Audio plays

#### C4. Blue Sea + RNB
- [ ] Works without errors
- [ ] Audio plays

---

### D. Abstract Colorful Art

#### D1. Abstract + Auto
**Expected:** Varied depending on color analysis, should pick reasonable genre

- [ ] Image uploads
- [ ] Status reaches COMPLETE
- [ ] Audio plays
- [ ] Genre decision makes sense (not random)

#### D2. Abstract + RAP
- [ ] Works without errors

#### D3. Abstract + HOUSE
- [ ] Works without errors

#### D4. Abstract + RNB
- [ ] Works without errors

---

### E. Random Object (Edge Case)

#### E1. Random Object + Auto
**Expected:** Should not crash, picks default genre gracefully

- [ ] Image uploads
- [ ] Status reaches COMPLETE (or graceful FAILED)
- [ ] If COMPLETE, audio plays
- [ ] If FAILED, error message is user-friendly

#### E2. Random Object + RAP
- [ ] Works without errors or fails gracefully

#### E3. Random Object + HOUSE
- [ ] Works without errors or fails gracefully

#### E4. Random Object + RNB
- [ ] Works without errors or fails gracefully

---

## Failure Simulation Tests

### F1. Network Failures

**Test: Disconnect cpp-core service**
```bash
# Stop cpp-core container
docker stop soundcanvas-cpp-core
```

Expected:
- [ ] Job moves to FAILED status
- [ ] Error message: "Service temporarily unavailable. Please try again in a moment."
- [ ] App doesn't crash globally
- [ ] User can try again after service restarts

**Test: Disconnect audio-producer service**
```bash
# Stop audio-producer container
docker stop soundcanvas-audio-producer
```

Expected:
- [ ] Job moves to FAILED status
- [ ] Error message mentions audio rendering failure
- [ ] App remains functional

### F2. S3 Upload Failure

**Test: Invalid AWS credentials**
```bash
# Temporarily set invalid AWS keys
export AWS_ACCESS_KEY_ID="invalid"
```

Expected:
- [ ] Job moves to FAILED status
- [ ] Error message mentions upload failure
- [ ] No orphaned RUNNING jobs

### F3. Database Connection Loss

**Test: Stop MySQL container briefly**
```bash
docker stop soundcanvas-mysql
```

Expected:
- [ ] /health endpoint returns 503
- [ ] GraphQL returns appropriate error
- [ ] Recovers when DB comes back

### F4. Invalid State Transitions

**Test: Try to mark COMPLETE job as RUNNING**
```typescript
// In db.ts test
await updateGenerationStatus(completedJobId, 'RUNNING');
```

Expected:
- [ ] Throws error: "Invalid state transition"
- [ ] DB row unchanged
- [ ] Error logged with jobId

---

## Load Sanity Tests

### L1. Parallel Generation Test

**Test: Submit 5-10 generations simultaneously**

```bash
# Run script that creates 10 generations
./scripts/test_parallel_load.sh
```

Expected:
- [ ] All 10 jobs created successfully
- [ ] All 10 jobs reach COMPLETE or FAILED (none stuck in RUNNING)
- [ ] ECS tasks don't get killed (check CloudWatch)
- [ ] DB handles concurrent updates correctly
- [ ] S3 receives all audio files
- [ ] Average completion time < 2 minutes per job

### L2. Large Image Test

**Test: Upload 10MB image**

Expected:
- [ ] Upload succeeds (under 10MB limit from graphqlUploadExpress)
- [ ] Generation completes
- [ ] No memory issues in cpp-core

### L3. Rapid Polling Test

**Test: Frontend polls status every 100ms for 5 minutes**

Expected:
- [ ] GraphQL doesn't rate limit or crash
- [ ] DB connection pool handles load
- [ ] Status updates correctly

---

## Performance Benchmarks

Track these metrics for each test:

| Metric | Target | Actual |
|--------|--------|--------|
| Image upload time | < 5s | |
| MIDI generation time | < 30s | |
| Audio rendering time | < 60s | |
| Total end-to-end | < 90s | |
| Audio file size | 2-10 MB | |
| Audio duration | 20-60s | |

---

## Test Execution Checklist

### Pre-Test Setup
- [ ] All services running (gateway, cpp-core, audio-producer, ml, MySQL)
- [ ] S3 buckets accessible
- [ ] RDS/MySQL database healthy
- [ ] Frontend dev server running
- [ ] Browser dev tools open (for network inspection)

### During Testing
- [ ] Record each test result in spreadsheet
- [ ] Save jobId for each generation
- [ ] Screenshot any errors
- [ ] Save audio files for quality check
- [ ] Monitor CloudWatch logs

### Post-Test Analysis
- [ ] Review all error logs
- [ ] Calculate success rate (target: >95%)
- [ ] Identify patterns in failures
- [ ] File GitHub issues for bugs found
- [ ] Update documentation with findings

---

## Automated Test Script (Optional)

```typescript
// scripts/run_regression_tests.ts
import axios from 'axios';
import fs from 'fs';

const GATEWAY_URL = 'http://localhost:4000/graphql';

const testImages = [
  { name: 'bright_outdoor', path: './test_images/bright_beach.jpg' },
  { name: 'dark_indoor', path: './test_images/dark_room.jpg' },
  { name: 'blue_ocean', path: './test_images/ocean.jpg' },
  { name: 'abstract', path: './test_images/abstract_art.jpg' },
  { name: 'random', path: './test_images/trash_can.jpg' },
];

const genres = ['auto', 'RAP', 'HOUSE', 'RNB'];

async function runTest(imagePath: string, genre: string) {
  // 1. Create generation
  // 2. Upload image
  // 3. Start generation
  // 4. Poll status
  // 5. Verify completion
  // 6. Check audio
}

// Run all combinations
for (const img of testImages) {
  for (const genre of genres) {
    await runTest(img.path, genre);
  }
}
```

---

## Bug Triage Priority

**P0 (Critical - Block Release):**
- Zero-length WAV files
- Genre stays "auto" after completion
- Crashes or infinite loops
- Data loss or corruption

**P1 (High - Fix Before Production):**
- Network error handling failures
- State transition violations
- S3 upload failures not surfaced

**P2 (Medium - Fix Soon):**
- UI polish issues
- Performance degradation
- Edge case handling

**P3 (Low - Nice to Have):**
- Logging improvements
- Error message wording
- Minor UI tweaks

---

## Success Criteria for Phase 12

**Definition of Done:**
- [ ] All 25 test cases pass (or fail gracefully with proper error messages)
- [ ] Zero-length WAV bug fixed
- [ ] Genre "auto" bug fixed
- [ ] No P0 bugs remaining
- [ ] <5 P1 bugs remaining
- [ ] Success rate >95% on regression matrix
- [ ] Load test completes without crashes
- [ ] All failure simulations handled correctly
- [ ] Performance benchmarks met
- [ ] Documentation updated

---

## Next Steps After Testing

1. **Fix critical bugs** found during testing
2. **Update documentation** with known limitations
3. **Create GitHub issues** for remaining P2/P3 bugs
4. **Update CHANGELOG** with Phase 12 improvements
5. **Deploy to staging** for final smoke test
6. **Deploy to production** when all criteria met

---

## Test Results Template

```markdown
## Test Results - [Date]

### Environment
- Gateway: v1.2.0
- cpp-core: v1.1.0
- audio-producer: v1.0.5
- Database: MySQL 8.0
- S3 Bucket: soundcanvas-uploads-staging

### Summary
- Total tests: 25
- Passed: 23
- Failed: 2
- Success rate: 92%

### Failed Tests
1. **B1. Dark Indoor + Auto**
   - Issue: Genre still shows "auto" after completion
   - JobId: abc-123
   - Fix: Updated orchestrator.ts line 67

2. **E1. Random Object + Auto**
   - Issue: Zero-length WAV file
   - JobId: def-456
   - Fix: Added audio validation in orchestrator.ts
```
