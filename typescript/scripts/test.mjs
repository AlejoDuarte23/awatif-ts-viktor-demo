import { build } from "esbuild";
import { spawnSync } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
await mkdir(resolve(root, ".test-build"), { recursive: true });
const output = resolve(root, ".test-build/analysis.test.mjs");
await build({
  absWorkingDir: root,
  entryPoints: ["tests/analysis.test.ts"],
  outfile: output,
  bundle: true,
  platform: "node",
  format: "esm",
  target: "node22",
});
const result = spawnSync(process.execPath, ["--test", output], { stdio: "inherit" });
process.exit(result.status ?? 1);
