# SoundCanvas

Turn images into ambient sound.

## High-level idea

- User uploads an image.
- Backend extracts visual features and uses a model to map them to music parameters.
- A C++ audio engine generates ambient audio based on those parameters.

This repo is structured as multiple services (frontend, GraphQL gateway, C++ core, ML, infra).
