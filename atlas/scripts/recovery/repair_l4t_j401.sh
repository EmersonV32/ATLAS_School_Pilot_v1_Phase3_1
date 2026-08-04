#!/usr/bin/env bash
set -euo pipefail

echo "[ATLAS repair] starting"
echo "[ATLAS repair] current L4T file:"
cat /etc/nv_tegra_release || true

echo "[ATLAS repair] backing up failing postinst scripts"
for pkg in nvidia-l4t-bootloader nvidia-l4t-kernel; do
  src="/var/lib/dpkg/info/${pkg}.postinst"
  if [ -f "$src" ] && [ ! -f "${src}.atlas-bak" ]; then
    sudo cp "$src" "${src}.atlas-bak"
  fi
  printf '#!/bin/sh\nexit 0\n' | sudo tee "$src" >/dev/null
  sudo chmod +x "$src"
done

echo "[ATLAS repair] configuring dpkg"
sudo dpkg --configure -a

echo "[ATLAS repair] holding NVIDIA L4T packages"
sudo apt-mark hold \
  nvidia-l4t-bootloader \
  nvidia-l4t-kernel \
  nvidia-l4t-kernel-dtbs \
  nvidia-l4t-kernel-headers \
  nvidia-l4t-kernel-oot-headers \
  nvidia-l4t-kernel-oot-modules \
  nvidia-l4t-display-kernel \
  nvidia-l4t-jetson-io \
  nvidia-l4t-core \
  nvidia-l4t-initrd

echo "[ATLAS repair] package states"
dpkg -l | grep -E 'nvidia-l4t-(bootloader|kernel|jetson-io|display|initrd|core)'

echo "[ATLAS repair] done"
