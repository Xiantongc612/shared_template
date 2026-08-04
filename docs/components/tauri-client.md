# Tauri desktop client generator

## Output boundary

- Path: `client/`
- Production artifact: platform-specific desktop bundles under `client/src-tauri/target/release/bundle/`
- Development command: `bun run --cwd client tauri dev`
- Formatting commands: Biome for `client/` and rustfmt for `client/src-tauri/`
- Validation commands: Biome, TypeScript, rustfmt verification, Cargo check, and Clippy
- Test commands: `bun run --cwd client test` and Cargo test
- Desktop bundle command: `bun run --cwd client tauri build --bundles deb,appimage`

## Local architecture

The client owns its React/Vite UI in `client/src` and its Rust Tauri shell in
`client/src-tauri`. It does not import the selected web frontend. Optional
client integrations are rendered independently from frontend integrations.
The `client_identifier` Copier answer supplies the lowercase reverse-domain
application identifier in `tauri.conf.json`.

Only desktop targets are generated. A native bundle requires the platform's
Tauri prerequisites. Generated automation installs WebKitGTK 4.1, GTK 3, and
related packages and produces AppImage and Debian bundles on Linux. macOS and
Windows bundles require their respective operating systems and are not built by
the generated workflows.

`devbox run init` derives platform icon files under `client/src-tauri/icons/`
from the managed `client/src-tauri/app-icon.svg`. Replace that source artwork and
remove at least one configured icon to regenerate an incomplete set. A complete
set is left unchanged.
