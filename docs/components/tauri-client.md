# Tauri desktop client generator

## Output boundary

- Path: `client/`
- Production artifact: platform-specific desktop bundles under `client/src-tauri/target/release/bundle/`
- Development command: `bun run --cwd client tauri dev`
- Validation commands: `bun run --cwd client check`, `bun test --cwd client`, and `bun run --cwd client build`
- Desktop bundle command: `bun run --cwd client tauri build`

## Local architecture

The client owns its React/Vite UI in `client/src` and its Rust Tauri shell in
`client/src-tauri`. It does not import the selected web frontend. Optional
client integrations are rendered independently from frontend integrations.

Only desktop targets are generated. A native bundle requires the platform's
Tauri prerequisites. On Linux these include WebKitGTK 4.1, GTK 3, and related
development packages; macOS and Windows bundles must be validated on their
respective operating systems.
