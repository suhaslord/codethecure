// Portable CPU inference for the exact exported three-convolution checkpoint.
// Kept separate from the worker so Node can verify it against PyTorch fixtures.
function convolution(input, channels, size, weights, bias, outputs) {
  const result = new Float32Array(outputs * size * size);
  const plane = size * size;
  for (let oc = 0; oc < outputs; oc++) {
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        let sum = bias[oc];
        for (let ic = 0; ic < channels; ic++) {
          const offset = (oc * channels + ic) * 9;
          for (let ky = 0; ky < 3; ky++) {
            const iy = y + ky - 1;
            if (iy < 0 || iy >= size) continue;
            for (let kx = 0; kx < 3; kx++) {
              const ix = x + kx - 1;
              if (ix >= 0 && ix < size)
                sum +=
                  input[ic * plane + iy * size + ix] *
                  weights[offset + ky * 3 + kx];
            }
          }
        }
        result[oc * plane + y * size + x] = Math.max(0, sum);
      }
    }
  }
  return result;
}

function pool(input, channels, size, factor) {
  const next = size / factor;
  const result = new Float32Array(channels * next * next);
  for (let c = 0; c < channels; c++)
    for (let y = 0; y < next; y++)
      for (let x = 0; x < next; x++) {
        let maximum = -Infinity;
        for (let dy = 0; dy < factor; dy++)
          for (let dx = 0; dx < factor; dx++) {
            maximum = Math.max(
              maximum,
              input[
                c * size * size + (y * factor + dy) * size + x * factor + dx
              ],
            );
          }
        result[c * next * next + y * next + x] = maximum;
      }
  return result;
}

function adaptiveAverage(input) {
  const result = new Float32Array(64 * 4 * 4);
  for (let c = 0; c < 64; c++)
    for (let y = 0; y < 4; y++)
      for (let x = 0; x < 4; x++) {
        let sum = 0;
        for (let dy = 0; dy < 4; dy++)
          for (let dx = 0; dx < 4; dx++)
            sum += input[c * 256 + (y * 4 + dy) * 16 + x * 4 + dx];
        result[c * 16 + y * 4 + x] = sum / 16;
      }
  return result;
}

function linear(input, weights, bias, relu) {
  const output = new Float32Array(bias.length);
  for (let o = 0; o < bias.length; o++) {
    let sum = bias[o];
    for (let i = 0; i < input.length; i++)
      sum += input[i] * weights[o * input.length + i];
    output[o] = relu ? Math.max(0, sum) : sum;
  }
  return output;
}

export function makeModel(manifest, buffer) {
  const floats = new Float32Array(buffer);
  const params = Object.fromEntries(
    manifest.parameters.map((p) => [
      p.name,
      floats.subarray(p.offset, p.offset + p.length),
    ]),
  );
  return (pixels) => {
    let x = Float32Array.from(pixels, (v) => v / 255);
    x = convolution(
      x,
      1,
      64,
      params["features.0.weight"],
      params["features.0.bias"],
      16,
    );
    x = pool(x, 16, 64, 2);
    x = convolution(
      x,
      16,
      32,
      params["features.3.weight"],
      params["features.3.bias"],
      32,
    );
    x = pool(x, 32, 32, 2);
    x = convolution(
      x,
      32,
      16,
      params["features.6.weight"],
      params["features.6.bias"],
      64,
    );
    x = adaptiveAverage(x);
    x = linear(
      x,
      params["classifier.0.weight"],
      params["classifier.0.bias"],
      true,
    );
    x = linear(
      x,
      params["classifier.3.weight"],
      params["classifier.3.bias"],
      false,
    );
    const difference = (x[1] - x[0]) / manifest.temperature;
    const malignant = 1 / (1 + Math.exp(difference));
    return [malignant, 1 - malignant];
  };
}

function roundEven(value) {
  const floor = Math.floor(value),
    fraction = value - floor;
  return fraction === 0.5 ? floor + (floor % 2) : Math.round(value);
}

export function transform(
  original,
  noise,
  { gain = 0, speckle = 0, shadow = 0 },
) {
  const output = new Uint8Array(4096),
    multiplier = 10 ** (gain / 20);
  for (let i = 0; i < output.length; i++) {
    let value = (original[i] / 255) * multiplier;
    if (speckle) value *= 1 + speckle * noise[i];
    if (shadow) {
      const y = Math.floor(i / 64),
        x = i % 64;
      const column = Math.exp(-0.5 * ((x / 64 - 0.55) / 0.14) ** 2);
      const depth = Math.max(0, Math.min(1, (y / 64 - 0.25) / 0.75));
      value *= 1 - shadow * column * depth;
    }
    output[i] = roundEven(Math.max(0, Math.min(1, value)) * 255);
  }
  return output;
}

export function reasons(clean, changed) {
  const result = [];
  if (clean[0] >= clean[1] !== changed[0] >= changed[1])
    result.push("Prediction changed");
  if (Math.max(...changed) < 0.8) result.push("Confidence below 80%");
  if (Math.abs(changed[0] - clean[0]) > 0.15)
    result.push("Malignant-class probability shifted over 15 pp");
  return result;
}
