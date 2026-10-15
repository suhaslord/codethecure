let worker,
  counter = 0;
const pending = new Map();
export async function browserAPI(path, payload) {
  if (path === "/api/report" || path === "/api/samples") {
    const filename = path.slice(5) + ".json";
    const response = await fetch(
      new URL(`./public-data/${filename}`, import.meta.url),
    );
    if (!response.ok)
      throw new Error("Public benchmark could not load. Reload to retry.");
    return response.json();
  }
  if (path !== "/api/experiment") throw new Error("Unknown browser API route.");
  if (!worker) {
    worker = new Worker(new URL("./browser-worker.mjs", import.meta.url), {
      type: "module",
    });
    worker.onmessage = ({ data }) => {
      const entry = pending.get(data.request);
      if (!entry) return;
      pending.delete(data.request);
      data.error
        ? entry.reject(new Error(data.error))
        : entry.resolve(data.result);
    };
    worker.onerror = () => {
      pending.forEach((entry) =>
        entry.reject(
          new Error(
            "Browser inference could not start. Try a current desktop browser or use the Python instructions.",
          ),
        ),
      );
      pending.clear();
      worker.terminate();
      worker = null;
    };
  }
  return new Promise((resolve, reject) => {
    const request = ++counter;
    pending.set(request, { resolve, reject });
    worker.postMessage({ request, payload });
  });
}

export function imageSource(id) {
  return window.GAINGUARD_STATIC
    ? `./public-data/image-${id}.png`
    : `/api/image?id=${id}`;
}
