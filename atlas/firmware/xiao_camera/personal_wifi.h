#pragma once

#include <stdint.h>

// Optional primary personal network; existing school/hotspot profiles are kept.
bool connectPersonalWifi(void (*statusLed)(bool), uint32_t timeoutMs);
