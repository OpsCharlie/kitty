"""
Kitten for vim-aware pane navigation in kitty.

Based on vim-kitty-navigator by knubie.

This kitten checks if the foreground process is vim/nvim and:
- If yes: passes the key through to vim (for smart-splits.nvim)
- If no: executes kitty's neighboring_window action

Usage in kitty.conf:
    map ctrl+h kitten pass_keys.py left   ctrl+h
    map ctrl+j kitten pass_keys.py bottom ctrl+j
    map ctrl+k kitten pass_keys.py top    ctrl+k
    map ctrl+l kitten pass_keys.py right  ctrl+l
"""

import re

from kittens.tui.handler import result_handler
from kitty.key_encoding import KeyEvent, parse_shortcut


def is_window_vim(window, vim_id="n?vim"):
    """Check if the foreground process in the window is vim/nvim."""
    fp = window.child.foreground_processes
    return any(
        re.search(vim_id, p["cmdline"][0] if p["cmdline"] else "", re.I)
        for p in fp
    )


def encode_key_mapping(window, key_mapping):
    """Encode a key mapping to send to the window."""
    mods, key = parse_shortcut(key_mapping)
    event = KeyEvent(
        mods=mods,
        key=key,
        shift=bool(mods & 1),
        alt=bool(mods & 2),
        ctrl=bool(mods & 4),
        super=bool(mods & 8),
        hyper=bool(mods & 16),
        meta=bool(mods & 32),
    ).as_window_system_event()

    return window.encoded_key(event)


def main():
    pass


@result_handler(no_ui=True)
def handle_result(args, result, target_window_id, boss):
    """Handle the kitten result - either pass key or navigate."""
    # args: ['pass_keys.py', 'direction', 'key_mapping', optional 'vim_id']
    direction = args[1]
    key_mapping = args[2]
    vim_id = args[3] if len(args) > 3 else "n?vim"

    window = boss.window_id_map.get(target_window_id)

    if window is None:
        return

    if is_window_vim(window, vim_id):
        # In vim - send the key to vim for smart-splits to handle
        for keymap in key_mapping.split(">"):
            encoded = encode_key_mapping(window, keymap)
            window.write_to_child(encoded)
    else:
        # Not in vim - use kitty's window navigation
        boss.active_tab.neighboring_window(direction)
