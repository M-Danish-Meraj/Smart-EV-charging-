// Copy ../output/results.json (written by `python run_all.py`) into data/.
// The dashboard never hand-types a result: this file is its only data source.
import { copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "..", "output", "results.json");
const dst = join(here, "..", "data", "results.json");

if (!existsSync(src)) {
  console.error(`Missing ${src}. Run \`python run_all.py\` in the repo root first.`);
  process.exit(1);
}
copyFileSync(src, dst);
console.log(`copied ${src} -> ${dst}`);
