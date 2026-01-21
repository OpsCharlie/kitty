# Kitty Dropdown Terminal Setup

This project provides a deployment script for installing Kitty terminal emulator with a custom configuration that enables dropdown terminal functionality similar to Guake.

## Files

- `__deploy.sh`: Installation script that downloads and installs Kitty, sets up desktop entries, and copies the config.
- `kitty.conf`: Custom Kitty configuration with dropdown-style settings (borderless, top-positioned window).

## Installation

1. Run the deploy script:

   ```bash
   ./__deploy.sh
   ```

## Dropdown

Install the Gnome Extension: Quake Terminal.

## Configuration

This configuration replicates tmux-like functionality in kitty with seamless nvim integration.

### Features

- Seamless `ctrl+h/j/k/l` navigation between kitty panes and nvim splits
- tmux-like keybindings for splits, tabs, and pane management
- Custom tab bar with system stats (CPU, memory, network, disk I/O, etc.)
- Works alongside tmux (smart-splits auto-detects the environment)

### Keybindings

#### Splits

| Key            | Action                                 |
| -------------- | -------------------------------------- |
| `ctrl+shift+!` | Vertical split                         |
| `ctrl+shift+-` | Horizontal split                       |
| `ctrl+shift+w` | Close pane                             |
| `ctrl+shift+z` | Zoom/unzoom pane (toggle stack layout) |

#### Navigation

| Key            | Action                           |
| -------------- | -------------------------------- |
| `ctrl+h/j/k/l` | Move between panes (vim-aware)   |
| `shift+arrows` | Move between panes (alternative) |
| `ctrl+shift+/` | Search pane                      |

#### Resize

| Key                 | Action             |
| ------------------- | ------------------ |
| `ctrl+shift+arrows` | Resize panes       |
| `ctrl+shift+=`      | Increase font size |
| `ctrl+shift+;`      | Decrease font size |

#### Tabs

| Key              | Action            |
| ---------------- | ----------------- |
| `ctrl+shift+t`   | New tab           |
| `ctrl+shift+q`   | Close tab         |
| `alt+left/right` | Previous/next tab |
| `alt+1-9`        | Go to tab N       |

### Python Scripts (Kittens)

#### `pass_keys.py` - Vim-aware Navigation

**Purpose:** Enables seamless `ctrl+h/j/k/l` navigation between kitty panes AND nvim splits.

**How it works:**

- When you press `ctrl+h`, kitty calls this kitten
- It checks if the foreground process is nvim/vim
- **If nvim:** passes the key through to nvim (smart-splits.nvim handles it)
- **If not nvim:** calls kitty's `neighboring_window` to switch panes

**Without this:** Keys would either only work in kitty OR only in nvim, not both.

---

#### `neighboring_window.py` - Smart-splits Kitten

**Purpose:** Allows nvim's smart-splits to tell kitty to focus a neighboring pane.

**How it works:**

- When you're at the edge of an nvim split and press `ctrl+l`
- Smart-splits detects there's no more nvim split in that direction
- It runs `kitty @ kitten neighboring_window.py right`
- This kitten tells kitty to focus the pane to the right

**Without this:** You could jump INTO nvim from kitty, but not OUT of nvim to kitty.

---

#### `relative_resize.py` - Smart-splits Kitten

**Purpose:** Allows nvim's smart-splits to resize kitty panes from within nvim.

**How it works:**

- If you use smart-splits resize commands (`alt+h/j/k/l`)
- When at the edge of nvim, it can resize the kitty pane instead

---

#### `split_window.py` - Smart-splits Kitten

**Purpose:** Allows nvim to create new kitty splits programmatically.

---

#### `tab_bar.py` - Custom Tab Bar

**Purpose:** Renders the custom status bar with system stats.

**How it works:**

- Kitty calls `draw_tab()` function for each tab
- Reads from `/proc` and `/sys` to get system metrics
- Returns formatted text with colors for the tab bar

**Displays:** Temperature, battery, uptime, CPU load, memory %, disk I/O, network speeds

---

### Script Summary

| Script                  | Direction      | Purpose                                      |
| ----------------------- | -------------- | -------------------------------------------- |
| `pass_keys.py`          | kitty -> nvim  | Pass keys through to nvim when vim is active |
| `neighboring_window.py` | nvim -> kitty  | Let nvim switch kitty panes                  |
| `relative_resize.py`    | nvim -> kitty  | Let nvim resize kitty panes                  |
| `split_window.py`       | nvim -> kitty  | Let nvim create kitty splits                 |
| `tab_bar.py`            | kitty internal | Custom status bar rendering                  |

### Known Limitations

- **No mouse drag resize:** Kitty doesn't support mouse-based split resizing (use keyboard shortcuts instead)
