// cpp-core's HTTP API. Stateless: bytes in, result out.
//   POST /features  body: image bytes             -> {"features": [8 numbers]}
//   POST /compose   body: {"features", "genre"}   -> MIDI file bytes
//   GET  /health                                  -> {"ok": true}
// Bad input returns 400 (permanent); unexpected errors return 500 (retryable).
#pragma once

void runHttpServer(int port);
