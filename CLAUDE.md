# Awatif base plate: build and run

## Project rules

- Write the viewer and solver control code in `typescript/src/`.
- Use the Awatif TypeScript source in `typescript/vendor/awatif-fem/`.
- Keep the local shell correction. It is needed for the vertical tube and stiffeners.
- Keep the geometry and mesh preparation in `viktor-app/app/model.py`.
- Do not edit `viktor-app/app/web/index.html` by hand. It is generated.
- Keep the source, lockfile, tests, and generated bundle in the same commit.
- Do not add external runtime scripts, fonts, or WASM downloads.
- Do not add `from __future__` imports or file header docstrings to Python files.
- Use modern Python type hints such as `list[float]` and `dict[str, float]`.

## Requirements

- Node.js 22 or later and npm.
- `uv` for the Python development environment.
- VIKTOR CLI, signed in to the correct environment.
- The app must use the registered name `awatif-ts-viktor-demo`.
- Use the Python version in `viktor-app/viktor.config.toml`.

Run all commands below from `awatif-ts-viktor-demo/`, unless stated otherwise.

## Compile and update the WebView

```bash
cd typescript
npm ci
npm run build
npm test
npm run format:check
```

`npm run build` runs strict TypeScript checks. It then builds the Awatif solver,
worker, and Three.js viewer. It writes the complete HTML bundle directly to
`../viktor-app/app/web/index.html`. No manual copy is needed.

If the build fails, correct the source and run it again. Keep the last valid
bundle until a new build succeeds. Do not remove the bundle from version control.

Run `npm run format` to apply Prettier to the TypeScript, HTML, CSS, and build
scripts. The upstream Awatif snapshot is excluded from automatic formatting.

## Python development environment

From `awatif-ts-viktor-demo/`:

```bash
cd viktor-app
uv sync --locked
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy
uv run python -m unittest discover -s tests
```

Use `uv run ruff check --fix app tests` and `uv run ruff format app tests` to
apply Python fixes and formatting. Use `uv run` for Python development commands.
On macOS, the native VIKTOR SDK is excluded. The mesh, input, and HTML tests
can still run. A live VIKTOR session requires a supported CLI environment.

After a dependency change, update `pyproject.toml`, run `uv lock`, and export
the locked runtime requirements for the VIKTOR CLI:

```bash
uv export --no-dev --no-hashes --no-header --no-annotate --no-emit-project -o requirements.txt
```

Commit `pyproject.toml`, `uv.lock`, and `requirements.txt` together.

## Install and start VIKTOR

From `awatif-ts-viktor-demo/`:

```bash
cd viktor-app
viktor-cli install
viktor-cli start
```

Use the app URL printed by the CLI. Do not start the CLI from `typescript/`
or from the parent folder. The app configuration is inside `viktor-app/`.

For a first clean install, run this from `viktor-app/`:

```bash
viktor-cli clean-start
```

If the platform app does not yet exist, register it first:

```bash
viktor-cli create-app "Awatif TS VIKTOR Demo" --registered-name awatif-ts-viktor-demo
viktor-cli clean-start
```

Use the existing app if it is already registered. Run `viktor-cli install`
again after a change to `requirements.txt`.

## Edit with two terminals

Terminal 1, from `awatif-ts-viktor-demo/`:

```bash
cd typescript
npm run watch
```

Terminal 2, from `awatif-ts-viktor-demo/`:

```bash
cd viktor-app
viktor-cli start
```

Save the TypeScript, HTML, CSS, or Awatif source. Wait for the build success
message. Click **Reload geometry** in VIKTOR to load the new bundle. If the
view does not update, stop and start `viktor-cli start` again. Python reads
the generated file for each new WebView result.

## Checks before commit or publish

From `typescript/`:

```bash
npm test
npm run format:check
npm run build
```

From `viktor-app/`, in the VIKTOR test environment:

```bash
viktor-cli test
```

The Python mesh, input, and HTML tests can also run without the full SDK:

```bash
uv run python -m unittest discover -s tests
```

These unit tests need `meshpy==2026.1`. A local Python environment must have
this package installed. A VIKTOR CLI install provides the app requirements.

In a browser or VIKTOR, check that the model loads, **Calculate** gives finite
results, changing a load changes the results, and mesh and deformation controls
work. Check the worker path and the fallback used when workers are blocked.

Publish from `viktor-app/` only after the checks pass and the user requests it.
