import { makeModel, transform, reasons } from "./inference.mjs";

let ready;
async function initialize() {
  const base = new URL("./public-data/", import.meta.url);
  const manifest = await (await fetch(new URL("manifest.json", base))).json();
  const get = async (name) => {
    const response = await fetch(new URL(name, base));
    if (!response.ok)
      throw new Error(`Could not load ${name}; reload to retry.`);
    const bytes = await response.arrayBuffer();
    const digest = [
      ...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    ]
      .map((x) => x.toString(16).padStart(2, "0"))
      .join("");
    if (digest !== manifest.files[name].sha256)
      throw new Error(`Integrity check failed for ${name}.`);
    return bytes;
  };
  const [weights, imageBytes, noiseBytes, sampleBytes] = await Promise.all(
    ["weights.bin", "images.bin", "noise.bin", "samples.json"].map(get),
  );
  return {
    model: makeModel(manifest, weights),
    images: new Uint8Array(imageBytes),
    noise: new Float64Array(noiseBytes),
    samples: JSON.parse(new TextDecoder().decode(sampleBytes)),
    manifest,
  };
}

function imageURL(pixels) {
  const canvas = new OffscreenCanvas(64, 64),
    context = canvas.getContext("2d");
  const rgba = new Uint8ClampedArray(4096 * 4);
  for (let i = 0; i < pixels.length; i++) {
    rgba.set([pixels[i], pixels[i], pixels[i], 255], i * 4);
  }
  context.putImageData(new ImageData(rgba, 64, 64), 0, 0);
  return canvas.convertToBlob({ type: "image/png" }).then(async (blob) => {
    const bytes = new Uint8Array(await blob.arrayBuffer());
    return "data:image/png;base64," + btoa(String.fromCharCode(...bytes));
  });
}

self.onmessage = async ({ data: { request, payload } }) => {
  try {
    ready ||= initialize();
    const { model, images, noise, samples, manifest } = await ready;
    const id = payload.sample_id;
    if (!Number.isInteger(id) || id < 0 || id >= samples.length)
      throw new Error("Invalid sample ID.");
    for (const [key, low, high] of [
      ["gain", -12, 12],
      ["speckle", 0, 0.6],
      ["shadow", 0, 0.9],
    ]) {
      if (
        !Number.isFinite(payload[key]) ||
        payload[key] < low ||
        payload[key] > high
      )
        throw new Error(`Invalid ${key}.`);
    }
    const original = images.subarray(id * 4096, (id + 1) * 4096),
      field = noise.subarray(id * 4096, (id + 1) * 4096);
    const clean = samples[id].probabilities,
      sweep = [];
    let changed, pixels;
    const count = payload.sweep === false ? 1 : 8;
    for (let i = 0; i <= count; i++) {
      const strength = i / count;
      pixels = transform(original, field, {
        gain: payload.gain * strength,
        speckle: payload.speckle * strength,
        shadow: payload.shadow * strength,
      });
      changed = i === 0 ? clean : model(pixels);
      sweep.push({
        strength,
        malignant_probability: changed[0],
        confidence: Math.max(...changed),
        flagged: reasons(clean, changed).length > 0,
      });
    }
    const flags = reasons(clean, changed),
      prediction = changed[0] >= changed[1] ? 0 : 1;
    const result = {
      sample: samples[id],
      settings: {
        gain: payload.gain,
        speckle: payload.speckle,
        shadow: payload.shadow,
        seed: manifest.seed + id,
      },
      original_image: await imageURL(original),
      transformed_image: await imageURL(pixels),
      probabilities: changed,
      prediction,
      confidence: Math.max(...changed),
      entropy: -changed.reduce(
        (sum, p) => sum + p * Math.log2(Math.max(p, 1e-12)),
        0,
      ),
      probability_shift: changed[0] - clean[0],
      correct: prediction === samples[id].label,
      flagged: flags.length > 0,
      reasons: flags,
      sweep,
    };
    self.postMessage({ request, result });
  } catch (error) {
    self.postMessage({ request, error: error.message });
  }
};
