#include "school_wifi_policy.h"

static_assert(!schoolWifiProfileUsable({false, true, "s", "u", "u", "p", "", ""}),
              "Unconfigured school must remain disabled");
static_assert(!schoolWifiProfileUsable({true, false, "s", "u", "u", "p", "", ""}),
              "No implicit certificate bypass");
static_assert(schoolWifiProfileUsable({true, true, "s", "u", "u", "p", "", ""}),
              "Explicit unverified opt-in is supported");
static_assert(schoolWifiProfileUsable({true, false, "s", "u", "u", "p", "ca", "server"}),
              "Complete trust settings are supported");
static_assert(!schoolWifiProfileUsable({true, true, "s", "u", "u", "p", "ca", ""}),
              "Partial CA configuration must fail closed");
static_assert(!schoolWifiProfileUsable({true, true, "s", "u", "u", "p", "", "server"}),
              "Partial domain configuration must fail closed");
static_assert(!schoolWifiProfileUsable({true, true, "s", "u", "", "p", "", ""}),
              "An empty username is rejected");
static_assert(!schoolWifiProfileUsable({true, true, "s", "u", "u", "", "", ""}),
              "An empty password is rejected");
static_assert(!schoolWifiProfileUsable({true, true, nullptr, "u", "u", "p", "", ""}),
              "Null profile pointers are rejected");
static_assert(!schoolWifiProfileUsable({true, true,
              "123456789012345678901234567890123", "u", "u", "p", "", ""}),
              "Oversized SSIDs are rejected");
