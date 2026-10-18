#include "camera_timing_policy.h"
#include "personal_wifi_policy.h"

static_assert(!cameraStreamStalledPolicy(false, 10000, 1, 5000),
              "An idle stream cannot stall");
static_assert(!cameraStreamStalledPolicy(true, 10000, 9999, 5000),
              "A recent frame cannot stall");
static_assert(!cameraStreamStalledPolicy(true, 10000, 10001, 5000),
              "A concurrent newer frame must not underflow into a false stall");
static_assert(!cameraStreamStalledPolicy(true, 0xffffffffU, 0, 5000),
              "A concurrent newer frame across millis wrap is not stalled");
static_assert(cameraStreamStalledPolicy(true, 5000, 0, 5000),
              "Timestamp zero is valid when the stream is active");
static_assert(!cameraStreamStalledPolicy(true, 4999, 0, 5000),
              "Stall threshold must not fire early");
static_assert(cameraStreamStalledPolicy(true, 10000, 5000, 5000),
              "An actual five-second stall must fire");
static_assert(cameraStreamStalledPolicy(true, 3000, 0xfffff830U, 5000),
              "An actual five-second stall across millis wrap must fire");
static_assert(!cameraStreamStalledPolicy(true, 2999, 0xfffff830U, 5000),
              "A wrapped 4999ms gap must not fire early");
static_assert(!cameraIntervalElapsed(0xfffffff0U, 0xffffff00U, 3000),
              "Reconnect must not flood just before wrap");
static_assert(!cameraIntervalElapsed(1000, 0xffffff00U, 3000),
              "Reconnect must wait for its full interval across wrap");
static_assert(cameraIntervalElapsed(2744, 0xffffff00U, 3000),
              "Reconnect is due after exactly 3000ms across wrap");
static_assert(cameraIntervalElapsed(0, 0U - 3000U, 3000),
              "Initial reconnect is immediate even at timestamp zero");

static_assert(!personalWifiProfileUsable({false, false, "ssid", "password"}),
              "Personal primary must be explicitly enabled");
static_assert(personalWifiProfileUsable({true, false, "ssid", "password"}),
              "WPA2 personal is supported");
static_assert(personalWifiProfileUsable({true, true, "ssid", "password"}),
              "WPA3-only accepts a passphrase");
static_assert(!personalWifiProfileUsable({true, false, "", "password"}),
              "Empty SSID is rejected");
static_assert(!personalWifiProfileUsable({true, false, nullptr, "password"}),
              "Null SSID is rejected");
static_assert(!personalWifiProfileUsable({true, false, "ssid", nullptr}),
              "Null password is rejected");
static_assert(!personalWifiProfileUsable({true, false, "ssid", "short"}),
              "A short WPA2 passphrase is rejected");
static_assert(!personalWifiProfileUsable({true, false,
              "123456789012345678901234567890123", "password"}),
              "SSID length counts bytes and cannot exceed 32");
static_assert(personalWifiProfileUsable({true, false, "ssid",
              "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}),
              "WPA2 accepts a 64-hex-digit raw PSK");
static_assert(!personalWifiProfileUsable({true, true, "ssid",
              "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}),
              "WPA3-only requires a passphrase, not a raw WPA2 PSK");
static_assert(!personalWifiProfileUsable({true, false, "ssid",
              "z123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}),
              "64-character non-hex values are not valid WPA2 keys");
