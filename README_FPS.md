# MJSXJ05CM 20/25 FPS profile — v1.2.2 Stable

Stable selectable 20/25 FPS profile for Xiaomi MJSXJ05CM.

What is included:

- `fetch_av` frame loop is reduced from 40 ms to 30 ms.
- `libboardav.so.1.0.0` encoder init constants are changed from 20 FPS to 25 FPS.
- `fps25-controller` continuously guards ISP AE max shutter at 40 ms, including after day/night profile switches.
- Web FPS selector now exposes only the verified 20 and 25 FPS profiles.
- The web LED switch controls the real MJSXJ05CM status LED lines (GPIO76 blue, GPIO77 yellow) immediately and restores the selected state after reboot.

Verified on the test camera after reboot:

- RTSP: ~24.8-25.0 FPS
- ONVIF: active
- microphone audio in RTSP: active
- ONVIF/RTSP backchannel audio: active from the stable build
- SD recording: active

Switching back to the 20 FPS runtime:

Open in the authenticated web interface:

`http://CAMERA_IP/cgi-bin/fps25-rollback-runtime.cgi`

Diagnostics:

`http://CAMERA_IP/cgi-bin/fps-md5.cgi`

