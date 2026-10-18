#pragma once

#include <stddef.h>

struct PersonalWifiProfile {
  bool configured;
  bool wpa3Only;
  const char *ssid;
  const char *password;
};

constexpr size_t personalWifiTextLength(const char *text) {
  size_t length = 0;
  while (text[length] != '\0') {
    ++length;
  }
  return length;
}

constexpr bool personalWifiHexKey(const char *text) {
  for (size_t i = 0; i < 64; ++i) {
    if (!((text[i] >= '0' && text[i] <= '9') ||
          (text[i] >= 'a' && text[i] <= 'f') ||
          (text[i] >= 'A' && text[i] <= 'F'))) {
      return false;
    }
  }
  return true;
}

constexpr bool personalWifiProfileUsable(const PersonalWifiProfile &p) {
  if (!p.configured || !p.ssid || !p.password) {
    return false;
  }
  const size_t ssidLength = personalWifiTextLength(p.ssid);
  const size_t passwordLength = personalWifiTextLength(p.password);
  return ssidLength > 0 && ssidLength <= 32 &&
         ((passwordLength >= 8 && passwordLength <= 63) ||
          (!p.wpa3Only && passwordLength == 64 && personalWifiHexKey(p.password)));
}
