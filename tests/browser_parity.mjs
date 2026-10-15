import fs from "node:fs";
import assert from "node:assert/strict";
import { makeModel, transform } from "../web/inference.mjs";
const root = process.argv[2] || "dist/public-data";
const read = (file) => fs.readFileSync(`${root}/${file}`);
const buffer = (file) => {
  const b = read(file);
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
};
const manifest = JSON.parse(read("manifest.json"));
const infer = makeModel(manifest, buffer("weights.bin"));
const images = new Uint8Array(buffer("images.bin")),
  noise = new Float64Array(buffer("noise.bin"));
let maximum = 0;
for (const fixture of JSON.parse(read("parity.json"))) {
  const pixels = transform(
    images.subarray(fixture.id * 4096, (fixture.id + 1) * 4096),
    noise.subarray(fixture.id * 4096, (fixture.id + 1) * 4096),
    fixture.settings,
  );
  assert.deepEqual(
    [...pixels],
    fixture.pixels,
    "Browser pixels must match NumPy exactly",
  );
  const actual = infer(pixels);
  maximum = Math.max(
    maximum,
    ...actual.map((v, i) => Math.abs(v - fixture.probabilities[i])),
  );
  assert.ok(
    actual.every((p, i) => Math.abs(p - fixture.probabilities[i]) < 1e-5),
    "CNN probability drift exceeds tolerance",
  );
}
console.log(
  `12 browser/PyTorch parity cases passed; max probability difference ${maximum}`,
);
