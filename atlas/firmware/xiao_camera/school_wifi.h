#pragma once

#include <stdint.h>

// The school profile is optional. Existing hotspot credentials are untouched.
bool connectSchoolWifi(void (*statusLed)(bool), uint32_t timeoutMs);
void disableSchoolWifi();
