#!/bin/bash

KITTY_DIR="/home/$USER/.local/kitty"
BIN_DIR="/home/$USER/bin"

[[ -d $BIN_DIR ]] || mkdir -p  $BIN_DIR
[[ -d $KITTY_DIR ]] || mkdir -p "$KITTY_DIR"

TEMP=$(command mktemp -d "/tmp/kitty-install-XXXXXXXXXXXX")
mkdir -p "$TEMP/mp"

case "$(command uname -m)" in
    amd64 | x86_64) ARCH="x86_64" ;;
    aarch64*) ARCH="arm64" ;;
    armv8*) ARCH="arm64" ;;
    *) echo "kitty binaries not available for architecture"; exit 1 ;;
esac

VERSION=$(curl -s https://api.github.com/repos/kovidgoyal/kitty/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
TAR="kitty-${VERSION/v/}-$ARCH.txz"
URL="https://github.com/kovidgoyal/kitty/releases/download/$VERSION/$TAR"
if ! curl -s "$URL" -L -o "$TEMP/$TAR"; then
    echo "Download failed"
    exit 1
fi
tar -xJof "$TEMP/$TAR" -C "$TEMP/mp" 
cp -a "$TEMP"/mp/* "$KITTY_DIR"

ln -sf "$KITTY_DIR/bin/kitty" "$KITTY_DIR/bin/kitten" "$BIN_DIR"

cp "$KITTY_DIR"/share/applications/kitty.desktop ~/.local/share/applications/
cp "$KITTY_DIR"/share/applications/kitty-open.desktop ~/.local/share/applications/
sed -i "s|Icon=kitty|Icon=$KITTY_DIR/share/icons/hicolor/256x256/apps/kitty.png|g" ~/.local/share/applications/kitty*.desktop
sed -i "s|Exec=kitty|Exec=$BIN_DIR/kitty|g" ~/.local/share/applications/kitty*.desktop

mkdir -p ~/.config/kitty
cp -i kitty.conf ~/.config/kitty/kitty.conf

rm -rf "$TEMP"
exit 0
