// cpp-core's HTTP API. Stateless: bytes in, result out.
//   POST /features  body: image bytes             -> {"features": [8 numbers]}
//   POST /compose   body: {"features", "genre"}   -> MIDI file bytes
//   GET  /health                                  -> {"ok": true}
#pragma once

void runHttpServer(int port);
