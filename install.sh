#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
venv="$project_root/.venv"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
bin_home="$HOME/.local/bin"
desktop_file="io.github.dlpwaters.SecretLoom.desktop"
icon_file="io.github.dlpwaters.SecretLoom.svg"

if [[ ! -x "$venv/bin/python" ]]; then
  python3 -m venv "$venv"
fi

"$venv/bin/python" -m pip install --disable-pip-version-check -e "$project_root"

mkdir -p -- "$bin_home" "$data_home/applications" "$data_home/icons/hicolor/scalable/apps"
ln -sfn -- "$project_root/bin/secretloom" "$bin_home/secretloom"
ln -sfn -- "$venv/bin/stegoforge" "$bin_home/stegoforge"
install -m 0644 "$project_root/share/applications/$desktop_file" "$data_home/applications/$desktop_file"
install -m 0644 "$project_root/share/icons/hicolor/scalable/apps/$icon_file" "$data_home/icons/hicolor/scalable/apps/$icon_file"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$data_home/applications"
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$data_home/icons/hicolor" >/dev/null 2>&1 || true
fi

printf '\nSecretLoom is installed.\n'
printf '  Shell:    secretloom\n'
printf '  Launcher: search for SecretLoom in the Omarchy app launcher\n'
printf '  CLI:      secretloom --help\n'
