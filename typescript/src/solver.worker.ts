import { errorText } from "./dom.ts";
import type { Analysis, Solution } from "./types.ts";

const workerScope = globalThis as unknown as {
  onmessage: (event: MessageEvent<Analysis>) => void;
  postMessage: (message: Solution | { error: string }) => void;
};
workerScope.onmessage = ({ data }) => {
  try {
    if (!globalThis.BasePlateSolver) throw new Error("The Awatif solver did not start.");
    workerScope.postMessage(globalThis.BasePlateSolver.solveAnalysis(data));
  } catch (error) {
    workerScope.postMessage({ error: errorText(error) });
  }
};
