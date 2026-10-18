#include <Arduino.h>
#include <WiFi.h>
#include "esp_wifi.h"
#include "personal_wifi.h"
#include "personal_wifi_policy.h"
#include "school_wifi.h"

#if __has_include("wifi_personal_secrets.h")
#include "wifi_personal_secrets.h"
#else
#include "wifi_personal_secrets.h.example"
#endif

namespace {
const PersonalWifiProfile kPersonal = {
    WIFI_PERSONAL_CONFIGURED, WIFI_PERSONAL_WPA3_ONLY,
    WIFI_PERSONAL_SSID, WIFI_PERSONAL_PASSWORD};
}

bool connectPersonalWifi(void (*statusLed)(bool), uint32_t timeoutMs) {
  if (!personalWifiProfileUsable(kPersonal)) {
    return false;
  }

  // XIAO ESP32-S3 can only see 2.4 GHz APs. Never downgrade to open/WPA1/EAP.
  const int count = WiFi.scanNetworks();
  bool visible = false;
  for (int i = 0; i < count; ++i) {
    const wifi_auth_mode_t auth = WiFi.encryptionType(i);
    const bool compatible = auth == WIFI_AUTH_WPA3_PSK ||
                            auth == WIFI_AUTH_WPA2_WPA3_PSK ||
                            (!kPersonal.wpa3Only && auth == WIFI_AUTH_WPA2_PSK);
    if (WiFi.SSID(i) == kPersonal.ssid && compatible) {
      visible = true;
      break;
    }
  }
  WiFi.scanDelete();
  if (!visible) {
    Serial.println("[WiFi] Primary personal network unavailable; trying fallbacks.");
    return false;
  }

  WiFi.setAutoReconnect(false);
  WiFi.disconnect(false, false);
  disableSchoolWifi();
  WiFi.setMinSecurity(kPersonal.wpa3Only ? WIFI_AUTH_WPA3_PSK : WIFI_AUTH_WPA2_PSK);
  // Configure first, then enforce PMF before the first WPA3-only association.
  WiFi.begin(kPersonal.ssid, kPersonal.password, 0, nullptr, false);
  wifi_config_t config{};
  bool ok = esp_wifi_get_config(WIFI_IF_STA, &config) == ESP_OK;
  if (ok) {
    config.sta.pmf_cfg.capable = true;
    config.sta.pmf_cfg.required = kPersonal.wpa3Only;
#if CONFIG_ESP_WIFI_ENABLE_WPA3_SAE
    config.sta.sae_pwe_h2e = WPA3_SAE_PWE_BOTH;
#endif
    ok = esp_wifi_set_config(WIFI_IF_STA, &config) == ESP_OK;
  }
  ok = ok && esp_wifi_connect() == ESP_OK;
  if (ok) {
    Serial.println("[WiFi] Trying primary personal network.");
    const uint32_t started = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - started < timeoutMs) {
      statusLed((millis() / 250) % 2 == 0);
      delay(100);
    }
    statusLed(false);
    if (WiFi.status() == WL_CONNECTED) {
      WiFi.setAutoReconnect(true);
      Serial.println("[WiFi] Primary personal network connected.");
      return true;
    }
  }
  WiFi.disconnect(false, false);
  disableSchoolWifi();
  WiFi.setAutoReconnect(true);
  Serial.println("[WiFi] Primary personal profile failed; trying fallbacks.");
  return false;
}
