# ATLAS judge demo script

Target length: 5 to 7 minutes. One operator controls the admin dashboard while
one presenter wears ATLAS. Keep a second presenter ready to narrate recovery.

## Opening (30 seconds)

> Museums have more stories than labels can hold. ATLAS is a wearable AI
> museum guide that sees the artwork, listens to the visitor, and turns each
> question into a continuing conversation shaped to that person.

Do not claim ATLAS is fully offline. The prototype keeps vision, session state,
content, and controls on the Jetson, while configured speech and language
providers may use cloud services.

## Live sequence

1. **Start:** Open the admin **Demo** tab. Confirm the chosen language,
   profile, Shokz microphone, output route, camera feed, and green readiness.
   Press **Start demo**.
2. **Recognition:** Face the Mona Lisa for five seconds. Let ATLAS offer more,
   or press the headset multifunction button for a manual capture.
3. **Conversation:** Ask, "Who created this artwork?" Then ask, "What other
   famous paintings did he make?" The follow-up demonstrates short-term
   context without repeating Leonardo's name.
4. **Language switch:** Say, "Switch to French," then ask one question in
   French. ATLAS should answer in French with one voice for the whole answer.
5. **Personalization:** In the Demo tab, change the profile to child or visual
   impairment, apply it, and ask for a description of the artwork.
6. **Operations:** Switch output from Shokz to **Judge speaker**, set volume,
   and use **Test sound**. Show the Audio/Vision and Visitor tabs briefly.
7. **Close:** End the session manually. Explain that temporary visitor profile
   data is cleared and the system returns to idle.

## Recovery branches

- **Cloud voice fails:** ATLAS should use Piper once for the complete answer,
  not restart a voice for each sentence.
- **Camera is unavailable:** keep the dashboards open, state that vision is
  reconnecting, and use manual artwork override in Audio/Vision.
- **Artwork is uncertain:** press the multifunction button or use **Capture**.
- **Shokz output is lost:** route output to the judge speaker; the microphone
  remains on the headset.
- **The runtime becomes unsafe:** press **Emergency stop**, explain the latch,
  and clear it only after the problem is understood.
- **Live demo cannot recover in 30 seconds:** move to the prerecorded video.

## Closing line

> ATLAS does not replace the artwork or the people who care for it. It helps
> the next question happen.
