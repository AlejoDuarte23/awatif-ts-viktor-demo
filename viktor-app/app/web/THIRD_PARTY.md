# Browser dependencies

The build compiles these dependencies into the HTML WebView bundle. No CDN
request is needed at runtime.

- Three.js `0.185.1` and OrbitControls, from npm package `three`.
  Source: https://github.com/mrdoob/three.js. License: MIT.
- Awatif FEM TypeScript source in `awatif-fem/src/`. This is the source snapshot
  used to produce this app's previous solver bundle. Its existing metadata
  identifies it as Awatif v2.0.0. It includes the local oriented-shell and
  membrane assembly correction described in `AWATIF_PATCH.md`.
  Source: https://github.com/madil4/awatif. The license file from the local
  source checkout is retained at `awatif-fem/LICENSE`.
  The build imports `deform.ts` and `analyze.ts` directly through a local npm
  package. It uses the TypeScript solver. The upstream C++/WASM entry is excluded.
  Imports that refer only to types use `import type` for the new build.
  `awatif-fem/index.d.ts` describes the solver interface for strict app checks.
- Math.js `14.4.0`, from npm. Source: https://github.com/josdejong/mathjs.
  License: Apache-2.0.
- Roboto regular and bold, in `../assets/fonts/`.
  Source: https://fonts.google.com/specimen/Roboto.
  License: SIL Open Font License 1.1 (`../assets/fonts/OFL.txt`).

Keep the source and license notices with the generated app. The build copies
Awatif and font licenses to `viktor-app/app/web/`. Dependency license comments
are retained in the JavaScript bundle.
