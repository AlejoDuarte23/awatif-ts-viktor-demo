import solverSource from "virtual:solver-bundle";
import workerRuntime from "virtual:worker-runtime";
import type { Analysis, Solution } from "./types.ts";

function createAnalysisWorker(): { worker: Worker; workerUrl: string } {
  const workerUrl = URL.createObjectURL(
    new Blob([solverSource, "\n", workerRuntime], {
      type: "text/javascript",
    }),
  );
  try {
    return { worker: new Worker(workerUrl), workerUrl };
  } catch (error) {
    URL.revokeObjectURL(workerUrl);
    throw error;
  }
}

function solveOnMainThread(analysis: Analysis): Solution {
  if (!globalThis.BasePlateSolver) {
    const script = document.createElement("script");
    script.textContent = solverSource;
    document.head.appendChild(script);
    script.remove();
  }
  if (!globalThis.BasePlateSolver) throw new Error("The WebView blocked the Awatif solver.");
  return globalThis.BasePlateSolver.solveAnalysis(analysis);
}

export function solveInBackground(analysis: Analysis, onFallback: () => void): Promise<Solution> {
  return new Promise((resolve, reject) => {
    const solveWithoutWorker = () => {
      onFallback();
      window.setTimeout(() => {
        try {
          resolve(solveOnMainThread(analysis));
        } catch (error) {
          reject(error);
        }
      }, 0);
    };
    let worker: Worker;
    let workerUrl: string;
    try {
      ({ worker, workerUrl } = createAnalysisWorker());
    } catch {
      solveWithoutWorker();
      return;
    }

    const cleanupWorker = () => {
      window.clearTimeout(workerTimeout);
      worker.terminate();
      URL.revokeObjectURL(workerUrl);
    };
    const workerTimeout = window.setTimeout(() => {
      cleanupWorker();
      reject(new Error("The Awatif worker did not finish within 90 seconds. Try the Coarse mesh."));
    }, 90_000);
    worker.onmessage = ({ data }: MessageEvent<Solution | { error: string }>) => {
      cleanupWorker();
      if ("error" in data) reject(new Error(data.error));
      else resolve(data);
    };
    worker.onerror = (event) => {
      event.preventDefault();
      cleanupWorker();
      solveWithoutWorker();
    };
    worker.postMessage(analysis);
  });
}
