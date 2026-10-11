#pragma once
// Synthetic compile-only certificate bytes; never usable for authentication.
constexpr bool WIFI_SCHOOL_CONFIGURED = true;
constexpr bool WIFI_SCHOOL_ALLOW_UNVERIFIED_SERVER = false;
constexpr char WIFI_SCHOOL_SSID[] = "fixture-school";
constexpr char WIFI_SCHOOL_IDENTITY[] = "fixture-user";
constexpr char WIFI_SCHOOL_USERNAME[] = "fixture-user";
constexpr char WIFI_SCHOOL_PASSWORD[] = "synthetic-only";
constexpr char WIFI_SCHOOL_CA_PEM[] = "-----BEGIN CERTIFICATE-----\nMAA=\n-----END CERTIFICATE-----\n";
constexpr char WIFI_SCHOOL_SERVER_NAME[] = "radius.example.invalid";
