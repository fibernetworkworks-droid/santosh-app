# Hoola — PowerToys Run plugin (W2b)

Alt+Space, `hoola`, Enter → Hoola Desktop opens.

- **ActionKeyword:** `hoola` · **ID:** `162E72D3C1D7464E865293A276993A7B` (never changes)
- Launches through the SAME user-level App Paths alias the Win+R MVP (W2a) writes
  (`HKCU\...\App Paths\hoola.exe`) — one launch truth; if the alias is off the plugin
  says so instead of guessing paths.
- Built by `build-desktop.yml` (`dotnet publish -p:Platform=x64`) against
  `Community.PowerToys.Run.Plugin.Dependencies` 0.97.0 (`net9.0-windows10.0.26100.0`,
  loads on the .NET 10 host of PowerToys 0.102+ and every .NET 9 PowerToys since 0.87).
- The build payload (`Community.PowerToys.Run.Plugin.Hoola.dll` + `plugin.json` + `Images\`)
  rides inside SantoshDesktop.exe; Hoola installs it itself to
  `%LOCALAPPDATA%\Microsoft\PowerToys\PowerToys Run\Plugins\Hoola` (user-level, no admin;
  phone se kahein: *"Hoola ko PowerToys Run se khulwao"*). PowerToys absent? The desktop
  falls back to the `Ctrl+Alt+H` global hotkey door (same window).
