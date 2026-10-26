import { build } from "esbuild";
import { watch } from "node:fs";
import { copyFile, mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(root, "../viktor-app/app/web");
const watchMode = process.argv.includes("--watch");
const execute = promisify(execFile);
const common = {
  absWorkingDir: root,
  bundle: true,
  write: false,
  format: "iife",
  platform: "browser",
  target: "es2022",
  minify: true,
  legalComments: "inline",
};

async function compile() {
  if (watchMode) {
    await execute(
      process.execPath,
      [resolve(root, "node_modules/typescript/bin/tsc"), "--noEmit"],
      { cwd: root },
    );
  }
  const [solver, worker] = await Promise.all([
    build({ ...common, entryPoints: ["src/solver.ts"], globalName: "BasePlateSolver" }),
    build({ ...common, entryPoints: ["src/solver.worker.ts"] }),
  ]);
  const sources = {
    "virtual:solver-bundle": solver.outputFiles[0].text,
    "virtual:worker-runtime": worker.outputFiles[0].text,
  };
  const viewer = await build({
    ...common,
    entryPoints: ["src/viewer.ts"],
    plugins: [
      {
        name: "inline-solver",
        setup(plugin) {
          plugin.onResolve({ filter: /^virtual:/ }, (args) => ({
            path: args.path,
            namespace: "inline",
          }));
          plugin.onLoad({ filter: /.*/, namespace: "inline" }, (args) => ({
            contents: sources[args.path],
            loader: "text",
          }));
        },
      },
    ],
  });
  const read = (path) => readFile(resolve(root, path), "utf8");
  const [template, styles, regular, bold] = await Promise.all([
    read("src/index.html"),
    read("src/styles.css"),
    readFile(resolve(root, "assets/fonts/roboto-400.ttf")),
    readFile(resolve(root, "assets/fonts/roboto-700.ttf")),
  ]);
  const html = template
    .replace("/*__STYLES__*/", () => styles)
    .replace("__ROBOTO_400_BASE64__", () => regular.toString("base64"))
    .replace("__ROBOTO_700_BASE64__", () => bold.toString("base64"))
    .replace("/*__VIEWER_BUNDLE__*/", () =>
      viewer.outputFiles[0].text.replace(/<\/script/gi, "<\\/script"),
    );
  await mkdir(output, { recursive: true });
  await writeFile(resolve(output, "index.html.tmp"), html);
  await rename(resolve(output, "index.html.tmp"), resolve(output, "index.html"));
  await copyFile(resolve(root, "vendor/THIRD_PARTY.md"), resolve(output, "THIRD_PARTY.md"));
  await copyFile(resolve(root, "vendor/AWATIF_PATCH.md"), resolve(output, "AWATIF_PATCH.md"));
  await copyFile(resolve(root, "assets/fonts/OFL.txt"), resolve(output, "FONT_LICENSE.txt"));
  await copyFile(resolve(root, "vendor/awatif-fem/LICENSE"), resolve(output, "AWATIF_LICENSE.txt"));
  console.log(
    `Built viktor-app/app/web/index.html (${(Buffer.byteLength(html) / 1024).toFixed(0)} KiB)`,
  );
}

await compile();
if (watchMode) {
  let timer;
  let running = false;
  let pending = false;
  const rebuild = async () => {
    if (running) {
      pending = true;
      return;
    }
    running = true;
    try {
      await compile();
    } catch (error) {
      console.error(error.stdout || error.message);
    } finally {
      running = false;
      if (pending) {
        pending = false;
        void rebuild();
      }
    }
  };
  for (const directory of ["src", "assets", "vendor"]) {
    watch(resolve(root, directory), { recursive: true }, () => {
      clearTimeout(timer);
      timer = setTimeout(rebuild, 150);
    });
  }
  console.log("Watching TypeScript, HTML, CSS, fonts, and Awatif sources.");
}
