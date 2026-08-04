#include <Arduino.h>
#include <ESPmDNS.h>
#include <WiFi.h>
#include "esp_camera.h"

#include "board_config.h"
#include "wifi_secrets.h"

namespace {

constexpr char kHostname[] = "atlas-camera";
constexpr uint32_t kWifiConnectTimeoutMs = 30000;

void setStatusLed(bool on) {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, on ? LOW : HIGH);
}

bool connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setHostname(kHostname);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("[WiFi] Connecting");
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED &&
         millis() - started < kWifiConnectTimeoutMs) {
    setStatusLed((millis() / 250) % 2 == 0);
    delay(100);
  }
  setStatusLed(false);

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\n[WiFi] Connection timed out; restarting.");
    return false;
  }

  Serial.println("\n[WiFi] Connected.");
  Serial.print("[WiFi] IP: ");
  Serial.println(WiFi.localIP());
  return true;
}

bool initializeCamera() {
  if (!psramFound()) {
    Serial.println("[Camera] PSRAM not found. Compile with PSRAM=opi.");
    return false;
  }

  camera_config_t config{};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 10;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = CAMERA_FB_IN_PSRAM;

  const esp_err_t error = esp_camera_init(&config);
  if (error != ESP_OK) {
    Serial.printf("[Camera] Init failed: 0x%x\n", error);
    return false;
  }

  sensor_t *sensor = esp_camera_sensor_get();
  if (sensor->id.PID == OV3660_PID) {
    sensor->set_vflip(sensor, 1);
    sensor->set_brightness(sensor, 1);
    sensor->set_saturation(sensor, -2);
  }
  sensor->set_framesize(sensor, FRAMESIZE_VGA);
  Serial.println("[Camera] Ready at 640x480 JPEG.");
  return true;
}

}  // namespace

void startCameraServer();

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  delay(500);
  Serial.println("\n[ATLAS] XIAO camera booting.");

  setStatusLed(true);
  if (!initializeCamera()) {
    while (true) {
      setStatusLed((millis() / 150) % 2 == 0);
      delay(50);
    }
  }

  if (!connectWifi()) {
    delay(1000);
    ESP.restart();
  }

  if (MDNS.begin(kHostname)) {
    MDNS.addService("http", "tcp", 80);
    Serial.printf("[mDNS] http://%s.local\n", kHostname);
  } else {
    Serial.println("[mDNS] Failed; use the numeric IP address above.");
  }

  startCameraServer();
  Serial.printf("[ATLAS] Controls: http://%s.local\n", kHostname);
  Serial.printf("[ATLAS] Stream:  http://%s.local:81/stream\n", kHostname);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Disconnected; restarting.");
    delay(500);
    ESP.restart();
  }
  delay(1000);
}
