#pragma once

#include <stddef.h>

constexpr size_t schoolWifiTextLength(const char *text) {
  size_t length = 0;
  while (text[length] != '\0') {
    ++length;
  }
  return length;
}

struct SchoolWifiProfile {
  bool configured;
  bool allowUnverifiedServer;
  const char *ssid;
  const char *identity;
  const char *username;
  const char *password;
  const char *caPem;
  const char *serverName;
};

constexpr bool schoolWifiProfileUsable(const SchoolWifiProfile &p) {
  if (!p.configured || !p.ssid || !p.identity || !p.username || !p.password ||
      !p.caPem || !p.serverName) {
    return false;
  }
  if (schoolWifiTextLength(p.ssid) == 0 || schoolWifiTextLength(p.ssid) > 32 ||
      schoolWifiTextLength(p.identity) == 0 || schoolWifiTextLength(p.identity) > 127 ||
      schoolWifiTextLength(p.username) == 0 || schoolWifiTextLength(p.username) > 127 ||
      schoolWifiTextLength(p.password) == 0 || schoolWifiTextLength(p.password) > 64) {
    return false;
  }
  const bool hasCa = p.caPem[0] != '\0';
  const bool hasServer = p.serverName[0] != '\0';
  // Partial trust settings must not silently become an unverified connection.
  return (hasCa && hasServer) || (!hasCa && !hasServer && p.allowUnverifiedServer);
}
