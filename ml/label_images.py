"""
Labeling tool: gives each photo the genre its colour and mood fit best.

Opens a page that shows one photo at a time next to the genre guide. Press 1-5
(or click) to pick a genre; Backspace goes back one. Each answer is saved to
data/labels.csv immediately, so labeling can stop and resume at any time.
Labels describe colour and mood, not subject, because the model only sees the
8 colour features: a party and a quiet park with the same colours get the same genre.

Run:  python label_images.py   then open http://localhost:8765
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from data_files import IMAGES_DIR, all_images, load_labels, save_labels
from genres import GENRES

PORT = 8765
SAVE_LOCK = threading.Lock()

# The labeling guide, shown next to the buttons: the look that fits each genre.
GENRE_GUIDE = {
    "EDM_CHILL": "calm and airy: light, soft or pastel colours, gentle contrast, cool blues and greens",
    "EDM_DROP": "dark and intense: mostly dark with punchy contrast or deep saturated colour",
    "RETROWAVE": "neon and stylised: purple, magenta, pink or teal-and-orange casts, coloured lights at night",
    "CINEMATIC": "muted and moody: greys, browns and dim light, washed-out or desaturated colour",
    "HOUSE": "bright and upbeat: well lit, warm, vivid and colourful",
}


PAGE = """<!doctype html>
<html><head><title>SoundCanvas labeling</title><style>
  body { font-family: sans-serif; background: #111; color: #eee; text-align: center; margin: 20px; }
  img { max-height: 65vh; max-width: 90vw; border-radius: 8px; }
  button { font-size: 16px; margin: 6px; padding: 10px 16px; border-radius: 8px; cursor: pointer; }
  small { display: block; color: #aaa; }
</style></head><body>
<h3 id="progress"></h3>
<img id="image"><p id="name"></p><div id="buttons"></div>
<p>Keys 1-5 pick a genre. Backspace goes back one.</p>
<script>
const DATA = __DATA__;
let index = DATA.images.findIndex(name => !(name in DATA.labels));
if (index === -1) index = DATA.images.length;

function show() {
  const done = Object.keys(DATA.labels).length;
  document.getElementById("progress").textContent =
    index >= DATA.images.length ? `All ${done} labeled. You can close this tab.`
                                : `${done} / ${DATA.images.length} labeled`;
  const image = document.getElementById("image");
  image.style.display = index >= DATA.images.length ? "none" : "";
  const name = document.getElementById("name");
  if (index < DATA.images.length) {
    image.src = "/images/" + DATA.images[index];
    name.textContent = DATA.images[index];
  } else {
    name.textContent = "";
  }
}

async function save(name, genre) {
  await fetch("/label", { method: "POST", body: JSON.stringify({ image: name, genre }) });
  if (genre) DATA.labels[name] = genre; else delete DATA.labels[name];
}

async function pick(genre) {
  if (index >= DATA.images.length) return;
  await save(DATA.images[index], genre);
  index += 1;
  show();
}

async function back() {
  if (index === 0) return;
  index -= 1;
  await save(DATA.images[index], "");
  show();
}

DATA.genres.forEach((genre, i) => {
  const button = document.createElement("button");
  button.innerHTML = `${i + 1}. ${genre}<small>${DATA.guide[genre]}</small>`;
  button.onclick = () => pick(genre);
  document.getElementById("buttons").appendChild(button);
});
document.addEventListener("keydown", event => {
  const number = parseInt(event.key);
  if (number >= 1 && number <= DATA.genres.length) pick(DATA.genres[number - 1]);
  if (event.key === "Backspace") back();
});
show();
</script></body></html>"""


class LabelingHandler(BaseHTTPRequestHandler):
    images = all_images()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            # ?names=a.jpg,b.jpg limits this tab to those images, so several labelers can work at once.
            wanted = parse_qs(parsed.query).get("names", [None])[0]
            images = self.images
            if wanted:
                allowed = set(self.images)
                images = [name for name in wanted.split(",") if name in allowed]
            data = {"images": images, "labels": load_labels(), "genres": GENRES, "guide": GENRE_GUIDE}
            self.respond(200, "text/html", PAGE.replace("__DATA__", json.dumps(data)).encode())
        elif self.path.startswith("/images/") and self.path[len("/images/"):] in self.images:
            self.respond(200, "image/jpeg", (IMAGES_DIR / self.path[len("/images/"):]).read_bytes())
        else:
            self.respond(404, "text/plain", b"not found")

    def do_POST(self):
        """Saves one answer. An empty genre removes the answer (used by Backspace)."""
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if body["image"] not in self.images or body["genre"] not in GENRES + [""]:
            self.respond(400, "text/plain", b"bad label")
            return
        with SAVE_LOCK:  # read-modify-write of the CSV must not interleave across threads
            labels = load_labels()
            if body["genre"]:
                labels[body["image"]] = body["genre"]
            else:
                labels.pop(body["image"], None)
            save_labels(labels)
        self.respond(200, "text/plain", b"ok")

    def respond(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep the terminal quiet


if __name__ == "__main__":
    print(f"Labeling {len(LabelingHandler.images)} images. Open http://localhost:{PORT}")
    # Threaded so one stalled connection can't block every other request. Address reuse is
    # off so a second copy fails to start instead of silently sharing the port (Windows allows that).
    ThreadingHTTPServer.allow_reuse_address = False
    ThreadingHTTPServer(("localhost", PORT), LabelingHandler).serve_forever()
