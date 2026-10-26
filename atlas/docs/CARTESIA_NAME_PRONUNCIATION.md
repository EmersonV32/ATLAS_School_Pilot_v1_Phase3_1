# Cartesia name pronunciation — October 25

The public introduction added in `f90bf48` includes the uppercase brand name
`ATLAS`. The Cartesia request builder previously passed that spelling verbatim;
it had no name-pronunciation rule. Earlier wake greetings used local Piper,
so an earlier correct greeting is not proof that the same Cartesia path was used.

Cartesia recommends normal capitalization for names and warns that all-caps
words can be interpreted as initialisms:
https://docs.cartesia.ai/build-with-cartesia/capability-guides/prompting-tips

The Cartesia request boundary now changes only the complete uppercase token
`ATLAS` to `Atlas`. Both whole-answer and complete-segment streaming requests use
that builder. Public/UI copy, source introductions, other acronyms, localized
name spellings, model, voice ID, language, speed, volume and provider fallback
remain unchanged. Private name-bearing greetings remain local-only; this change
does not add any cloud request or persist text/audio.

Synthetic tests cover all 20 language introductions, word boundaries, repeated
names and possessives, empty terminal frames, and actual whole/streaming adapter
requests using fake transport and playback. These tests verify request contents,
not the sound produced by Cartesia. The all-caps ambiguity is a likely cause,
not an audibly proven diagnosis. Live acceptance requires the user to hear one
anonymous introduction through the existing selected Cartesia voice after an
explicitly approved, coordinated deployment. No live deployment or audible
acceptance is established by synthetic tests alone.

Local verification: 182 focused speech/identity/privacy tests passed. The full
guarded suite passed 3,789 tests with two skips across all 55 test files, each
covered once in four disjoint partitions. Maintained-source Ruff, secret,
recovery-bundle and whitespace checks passed. No UI files changed; the existing
navigation release's browser verification remains applicable. Deployment and
the audible greeting check are separate acceptance steps.

## Approved Jetson installation

The user approved applying now while not recording. The dashboard chat cleared
the exclusive deployment window after its navigation release. Runtime source
revision `4b2233c3d4961cbd8d929f27198cab727b034ba3` was installed with the existing
transactional source-only release tool and one controlled user-service restart.
No reboot, package, model, private configuration, voice setting or hardware
output change was made.

The 203-file archive SHA-256 is
`9bc56e025588679f662679cd90b17d8b3ec69e892bd4b86469a35dd9ff99f421`.
Native staged validation passed before source replacement. All 195 installed
managed files match the archive, and the 36 new synthetic pronunciation tests
also pass on the Jetson. The service is active/running with zero unexpected
restarts and exit status zero; public health/UI return 200 and unauthenticated
admin audio access returns 401. Boot ID, credential stat metadata and the pan
driver hash are unchanged; header PWM remains unexported. Credential contents
and visitor logs/audio were never inspected.

Rollback source is retained at
`/home/super-alex/atlas/backups/pronunciation-20261025/atlas-source-20261025-205822-1a3b346a`.
The user still needs to start a fresh demo and confirm the anonymous Cartesia
introduction by ear. A passing request test is not a guarantee of provider audio.
