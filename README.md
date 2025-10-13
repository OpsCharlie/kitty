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

Edit `kitty.conf` to customize appearance and behavior. The current config includes:

- Transparent background
- Custom font (IosevkaTerm Nerd Font)
- No window decorations
- Colorscheme
