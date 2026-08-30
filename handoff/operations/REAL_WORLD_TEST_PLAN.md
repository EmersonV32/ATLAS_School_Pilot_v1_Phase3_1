# Real-world test plan

Record every run in a shared table with build commit, Jetson temperature,
camera, audio route, network, result, and attached log filename.

## Test rounds

| Round | Setup | Minimum evidence | Pass condition |
| --- | --- | --- | --- |
| Desk baseline | Fixed artwork, quiet room | 10 interactions per class | No wrong artwork response |
| Gallery motion | Walking, oblique views, partial frames | 10 approaches per class | Stable prompt only on intended work |
| Crowd and noise | Two speakers, background audio | 20 questions | Intended visitor remains understandable |
| Network stress | Latency, brief outage, recovery | 10 conversations | Clear fallback; runtime stays active |
| Device recovery | Camera/Shokz unplug and reconnect | 5 cycles each | Dashboard remains reachable and recovers |
| Endurance | Full runtime and camera | 60 minutes | No unbounded memory, heat, or audio drift |
| Judge rehearsal | Exact script, timed | 3 complete runs | Each run finishes inside target time |

## Metrics

- Artwork correctness: correct stable artwork prompts / all stable prompts.
- False prompt rate: prompts when no intended artwork is held / test minutes.
- End-to-end response latency: question end to first audible response.
- Conversation completion: cycles completed without operator recovery.
- Recovery time: disconnect to healthy readiness.
- Voice consistency: answers completed with one voice / multi-sentence answers.

Do not average away a single dangerous result. A wrong confident artwork,
unrecoverable camera, stuck session, or exposed secret is a release blocker.
