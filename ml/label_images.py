"""
Hand-labeling tool for the human-labeled set.

Opens a page that shows one image at a time. Press 1-5 (or click) to pick the
genre that fits the image best; Backspace goes back one. Each answer is saved
to data/human_labels.csv immediately, so you can stop and resume any time.
The rule label is never shown, so the answers are independent of labeler.py.

Run:  python label_images.py   then open http://localhost:8765
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from labeler import GENRES
from splits import HUMAN_SET_SIZE, IMAGES_DIR, human_set, load_human_labels, save_human_labels

PORT = 8765

# What each genre sounds like, shown next to the buttons as a labeling guide.
GENRE_GUIDE = {
    "EDM_CHILL": "calm, airy electronic: relaxed, soft, peaceful",
    "EDM_DROP": "intense bass drops: aggressive, powerful, dark energy",
    "RETROWAVE": "80s synths: neon, nostalgic, stylish",
    "CINEMATIC": "film score: dramatic, epic, moody",
    "HOUSE": "upbeat dance music: bright, fun, social",
}


PAGE = """<!doctype html>
<html><head><title>SoundCanvas labeling</title><style>
  body { font-family: sans-serif; background: #111; color: #eee; text-align: center; margin: 20px; }
  img { max-height: 65vh; max-width: 90vw; border-radius: 8px; }
  button { font-size: 16px; margin: 6px; padding: 10px 16px; border-radius: 8px; cursor: pointer; }
  small { display: block; color: #aaa; }
</style></head><body>
<h3 id="progress"></h3>
<img id="image"><div id="buttons"></div>
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
  if (index < DATA.images.length) image.src = "/images/" + DATA.images[index];
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
    images = human_set()

    def do_GET(self):
        if self.path == "/":
            data = {"images": self.images, "labels": load_human_labels(), "genres": GENRES, "guide": GENRE_GUIDE}
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
        labels = load_human_labels()
        if body["genre"]:
            labels[body["image"]] = body["genre"]
        else:
            labels.pop(body["image"], None)
        save_human_labels(labels)
        self.respond(200, "text/plain", b"ok")

    def respond(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep the terminal quiet


if __name__ == "__main__":
    print(f"Labeling {HUMAN_SET_SIZE} images. Open http://localhost:{PORT}")
    HTTPServer(("localhost", PORT), LabelingHandler).serve_forever()
