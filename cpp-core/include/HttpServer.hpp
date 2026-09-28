// cpp-core http api. stateless, bytes in -> result out, nothing stored
//   POST /features  body: image bytes             -> {"features": [8 numbers]}
//   POST /compose   body: {"features", "genre"}   -> MIDI file bytes
//   GET  /health                                  -> {"ok": true}
// 400 = bad input (worker won't retry), 500 = unexpected (worker retries)
#pragma once

void runHttpServer(int port);
