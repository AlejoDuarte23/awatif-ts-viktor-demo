# awatif-ts-viktor-demo

Awatif TypeScript baseplate analysis in a VIKTOR WebView.

- `typescript/`: source and build tools.
- `viktor-app/`: VIKTOR app with the built WebView bundle.

Requires Node.js 22+, npm, and a configured VIKTOR CLI.

First setup, from the project folder:

```bash
cd typescript
npm ci
npm run build
cd ../viktor-app
viktor-cli create-app "Awatif TS VIKTOR Demo" --registered-name awatif-ts-viktor-demo
viktor-cli clean-start
```

After setup, run `viktor-cli start` from `viktor-app/`.

More commands: [CLAUDE.md](CLAUDE.md). For help with VIKTOR apps, use my [VIKTOR skills](https://github.com/AlejoDuarte23/viktor-skills).
