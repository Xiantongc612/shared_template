# Kotlin Multiplatform application generator

## Output boundary

- Path: `kmp/`
- Production artifact: no artifact in the normal validate/release chain
- Development command: `gradle -p kmp run` on a desktop host
- Formatting commands: `gradle -p kmp ktlintFormat`
- Validation commands: `gradle -p kmp ktlintCheck` and desktop compilation
- Test commands: `gradle -p kmp test`
- Manual packaging: `package-kmp` uploads unsigned Android APK, macOS DMG, and Windows MSI Actions artifacts

## Local architecture

The component uses Compose Multiplatform for shared UI and logic in
`composeApp/src/commonMain`. Android, iOS, and desktop entry points live in their
platform source sets. Desktop builds use Compose Desktop/JVM; macOS and Windows
do not use Kotlin/Native desktop targets.

The generated application identity comes from `kmp_identifier`. The component
does not share source with the frontend or Tauri client, and it does not include
store publication, signing, notarization, or deployment credentials.

Linux validation covers common, Android, and desktop JVM compilation. Apple
simulator compilation and native desktop packaging require their respective
host operating systems and are available only through the manually dispatched
workflow.
