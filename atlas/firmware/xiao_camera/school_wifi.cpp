#include <Arduino.h>
#include <WiFi.h>
#include "school_wifi.h"
#include "school_wifi_policy.h"

#if __has_include("wifi_school_secrets.h")
#include "wifi_school_secrets.h"
#else
#include "wifi_school_secrets.h.example"
#endif

#if CONFIG_ESP_WIFI_ENTERPRISE_SUPPORT
#include "esp_eap_client.h"
#endif

namespace {
const SchoolWifiProfile kSchool = {
    WIFI_SCHOOL_CONFIGURED, WIFI_SCHOOL_ALLOW_UNVERIFIED_SERVER,
    WIFI_SCHOOL_SSID, WIFI_SCHOOL_IDENTITY, WIFI_SCHOOL_USERNAME,
    WIFI_SCHOOL_PASSWORD, WIFI_SCHOOL_CA_PEM, WIFI_SCHOOL_SERVER_NAME};
}

void disableSchoolWifi() {
#if CONFIG_ESP_WIFI_ENTERPRISE_SUPPORT
  // Disabling enterprise mode clears its credentials/settings in the driver.
  esp_wifi_sta_enterprise_disable();
#endif
  WiFi.setMinSecurity(WIFI_AUTH_WPA2_PSK);
}

bool connectSchoolWifi(void (*statusLed)(bool), uint32_t timeoutMs) {
  if (!schoolWifiProfileUsable(kSchool)) {
    return false;
  }
#if !CONFIG_ESP_WIFI_ENTERPRISE_SUPPORT
  Serial.println("[WiFi] Enterprise support unavailable; using hotspot profile.");
  return false;
#else
  // Do not spend an authentication timeout at home when school is out of range.
  const int count = WiFi.scanNetworks();
  bool visible = false;
  for (int i = 0; i < count; ++i) {
    if (WiFi.SSID(i) == kSchool.ssid &&
        WiFi.encryptionType(i) == WIFI_AUTH_WPA2_ENTERPRISE) {
      visible = true;
      break;
    }
  }
  WiFi.scanDelete();
  if (!visible) {
    Serial.println("[WiFi] School enterprise network unavailable; using hotspot.");
    return false;
  }

  WiFi.setAutoReconnect(false);
  WiFi.disconnect(false, false);
  disableSchoolWifi();
  WiFi.setMinSecurity(WIFI_AUTH_WPA2_ENTERPRISE);
  bool ok = esp_eap_client_set_eap_methods(ESP_EAP_TYPE_PEAP) == ESP_OK;
  ok = ok && esp_eap_client_set_identity(
      reinterpret_cast<const unsigned char *>(kSchool.identity),
      strlen(kSchool.identity)) == ESP_OK;
  ok = ok && esp_eap_client_set_username(
      reinterpret_cast<const unsigned char *>(kSchool.username),
      strlen(kSchool.username)) == ESP_OK;
  ok = ok && esp_eap_client_set_password(
      reinterpret_cast<const unsigned char *>(kSchool.password),
      strlen(kSchool.password)) == ESP_OK;
  ok = ok && esp_eap_client_use_default_cert_bundle(false) == ESP_OK;
  if (kSchool.caPem[0]) {
    ok = ok && esp_eap_client_set_ca_cert(
        reinterpret_cast<const unsigned char *>(kSchool.caPem),
        strlen(kSchool.caPem) + 1) == ESP_OK;
    ok = ok && esp_eap_client_set_domain_name(kSchool.serverName) == ESP_OK;
    ok = ok && esp_eap_client_set_disable_time_check(false) == ESP_OK;
  } else {
    // Possible only after the operator explicitly accepted this risk locally.
    Serial.println("[WiFi] WARNING: school server certificate is NOT verified.");
  }
  ok = ok && esp_wifi_sta_enterprise_enable() == ESP_OK;
  if (ok) {
    Serial.println("[WiFi] Trying school PEAP profile (authentication untested).");
    WiFi.begin(kSchool.ssid);
    const uint32_t started = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - started < timeoutMs) {
      statusLed((millis() / 250) % 2 == 0);
      delay(100);
    }
    statusLed(false);
    if (WiFi.status() == WL_CONNECTED) {
      WiFi.setAutoReconnect(true);
      Serial.println("[WiFi] School authentication succeeded.");
      return true;
    }
  }
  // Never leave enterprise authentication active for the existing PSK hotspot.
  WiFi.disconnect(false, false);
  disableSchoolWifi();
  WiFi.setAutoReconnect(true);
  Serial.println("[WiFi] School profile failed; falling back to hotspot.");
  return false;
#endif
}
