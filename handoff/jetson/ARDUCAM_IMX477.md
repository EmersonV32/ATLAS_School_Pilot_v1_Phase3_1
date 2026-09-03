# Arducam UC-517 Rev D3 / IMX477

## ATLAS integration

The Arducam is an independent, admin-only CSI preview. It does not replace the
ESP32/XIAO artwork camera, feed YOLO, or participate in session startup. Open
**Admin > Arducam** to start its live view. Its API endpoints require the admin
token, and preview frames remain in memory rather than being written to disk.

## Known hardware and defaults

- The camera board is marked `UC-517 Rev D3`, which belongs to Arducam's IMX477
  family. The marking alone does not establish the exact lens/focus SKU.
- The active Jetson is a Seeed reComputer Super with a J401 carrier, Orin NX
  16 GB, JetPack 6.2, and L4T 36.4.x.
- The expected physical connector is CAM0. CAM0 is a connector name, not a
  stable Linux device number.
- ATLAS defaults to Argus `sensor-id=1`, 1920x1080 at 30 FPS. NVIDIA documents
  a JetPack 6 case where a camera on CAM0 is addressed as sensor ID 1.

## First hardware check

1. Power the Jetson fully off before inserting or reseating the CSI ribbon.
2. Confirm the ribbon orientation for both the J401 carrier and camera board.
3. Boot the Jetson and run:

   ```bash
   cd /home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated
   bash scripts/check_arducam.sh
   ```

4. The probe safely tries sensor IDs 1 and 0 without installing packages or
   modifying the kernel. If it reports sensor ID 0, set
   `hardware.arducam_sensor_id: 0` in `config/settings.yaml` and restart ATLAS.
5. Open **Admin > Arducam** and confirm the image, frame age, FPS, and reconnect
   count. The main ATLAS service must remain available if the camera is absent.

## Driver check

Do not install or replace a camera driver if the probe already passes. Arducam
documents a separate IMX477 driver installer for supported JetPack releases,
but its generic instructions target NVIDIA carrier boards. The ATLAS J401 is a
third-party carrier, so first record the exact L4T release, kernel, and detected
camera devices:

```bash
cat /etc/nv_tegra_release
uname -a
v4l2-ctl --list-devices
```

If both Argus probes fail, take a Jetson recovery snapshot before evaluating a
driver or device-tree change. Confirm compatibility with Arducam and Seeed for
the exact board and L4T release.

## Primary references

- [Arducam IMX477 specifications](https://docs.arducam.com/Nvidia-Jetson-Camera/Native-Camera/imx477/)
- [Arducam native-camera quick start](https://docs.arducam.com/Nvidia-Jetson-Camera/Native-Camera/Quick-Start-Guide/)
- [Arducam Jetson camera support matrix](https://docs.arducam.com/Nvidia-Jetson-Camera/Introduction-to-Arducam-Jetson-Cameras/)
- [NVIDIA Orin Nano camera connector guidance](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/howto.html)
- [NVIDIA camera software architecture](https://docs.nvidia.com/jetson/archives/r35.6.1/DeveloperGuide/SD/CameraDevelopment/CameraSoftwareDevelopmentSolution.html)
- [Jetson Linux 36.4.4 release notes](https://docs.nvidia.com/jetson/archives/r36.4.4/ReleaseNotes/Jetson_Linux_Release_Notes_r36.4.4.pdf)
