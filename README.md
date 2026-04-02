# Alfred Firefox Bookmarks

An Alfred workflow to search, filter, and open your Firefox bookmarks.

## Usage

- `bm [query]` — Search your Firefox bookmarks
  - `↩` — Open bookmark in `app_default`
  - `⌘+↩` — Open bookmark in `app_cmd`
  - `⌥+↩` — Open bookmark in `app_alt`
  - `^+↩` — Open bookmark in `app_ctrl`
  - `⇧+↩` — Open bookmark in `app_shift`
  - `fn+↩` — Open bookmark in `app_fn`
  - Combined modifiers (e.g. `⇧+^+↩`) — Open bookmark in `app_shift_ctrl`
- `bmsettings` — Open `settings.json` in your default JSON editor
- `bmupdate` — Force a refresh of the bookmark cache
- `bmhelp` — Open the help file in your browser

## Configuration

Run `bmsettings` to open `settings.json`. The available options are:

```json
{
  "firefox_profile": null,
  "app_default": "Firefox",
  "app_cmd": "Browser",
  "app_alt": null,
  "app_ctrl": null,
  "app_shift": null,
  "app_fn": null
}
```

| Key | Description |
|-----|-------------|
| `firefox_profile` | Absolute path to your Firefox profile directory. Set to `null` to auto-detect the default profile. |
| `app_default` | App opened with ↩. Use `"Browser"` for the system default browser, or an app name like `"Firefox"`, `"Safari"`, `"Google Chrome"`. |
| `app_cmd` | App opened with ⌘+↩ |
| `app_alt` | App opened with ⌥+↩ |
| `app_ctrl` | App opened with ^+↩ |
| `app_shift` | App opened with ⇧+↩ |
| `app_fn` | App opened with fn+↩ |

Any `app_*` value can also be a list to open in multiple apps simultaneously:
```json
"app_cmd": ["Firefox", "Safari"]
```

### Multi-Key Modifier Combinations

You can bind any combination of modifier keys by joining them with underscores in the settings key. The modifiers are mapped directly to Alfred's combined modifier syntax.

```json
{
  "app_shift_ctrl": "Google Chrome",
  "app_cmd_alt": "Safari",
  "app_cmd_shift": ["Firefox", "Google Chrome"]
}
```

| Key | Modifier Combo |
|-----|---------------|
| `app_cmd_alt` | ⌘+⌥+↩ |
| `app_cmd_ctrl` | ⌘+^+↩ |
| `app_cmd_shift` | ⌘+⇧+↩ |
| `app_shift_ctrl` | ⇧+^+↩ |
| `app_alt_ctrl` | ⌥+^+↩ |
| `app_cmd_alt_ctrl` | ⌘+⌥+^+↩ |

Any combination of `cmd`, `alt`, `ctrl`, `shift`, and `fn` is supported — just join them with underscores.

## Requirements

- Alfred 4+ with Powerpack
- Python 3 (ships with macOS)
- Firefox with at least one profile

## Installation

Download the latest `.alfredworkflow` from the [Releases](https://github.com/b-Johnson/alfred-firefox-bookmarks/releases) page and double-click to install.
