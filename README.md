# Kitty Dropdown Terminal Setup

This project provides a deployment script for installing Kitty terminal emulator with a custom configuration that enables dropdown terminal functionality similar to Guake.

## Files

- `__deploy.sh`: Installation script that downloads and installs Kitty, sets up desktop entries, and copies the config.
- `kitty.conf`: Custom Kitty configuration with dropdown-style settings (borderless, top-positioned window).
- `toggle_kitty.sh`: Script to toggle Kitty window visibility for dropdown behavior.

## Installation

1. Run the deploy script:

   ```bash
   ./__deploy.sh
   ```

## Dropdown

```
gsettings --schemadir ~/.local/share/gnome-shell/extensions/toggle-alacritty@itstime.tech/schemas \
  set org.gnome.shell.extensions.toggle-alacritty command "/home/$USER/bin/kitty --single-instance"
```


## Configuration

Edit `kitty.conf` to customize appearance and behavior. The current config includes:

- Transparent background
- Custom font (IosevkaTerm Nerd Font)
- Dropdown window settings (hide decorations, top placement)
