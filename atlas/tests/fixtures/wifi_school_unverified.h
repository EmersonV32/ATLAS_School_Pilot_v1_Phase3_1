#pragma once
// Synthetic build fixture, never a real network/account.
constexpr bool WIFI_SCHOOL_CONFIGURED = true;
constexpr bool WIFI_SCHOOL_ALLOW_UNVERIFIED_SERVER = true;
constexpr char WIFI_SCHOOL_SSID[] = "fixture-school";
constexpr char WIFI_SCHOOL_IDENTITY[] = "fixture-user";
constexpr char WIFI_SCHOOL_USERNAME[] = "fixture-user";
constexpr char WIFI_SCHOOL_PASSWORD[] = "synthetic-only";
constexpr char WIFI_SCHOOL_CA_PEM[] = "";
constexpr char WIFI_SCHOOL_SERVER_NAME[] = "";
