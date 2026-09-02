# AI Use, Team Authorship, Privacy, And Rights

## AI Use Register

WRO 2026 requires the report to identify which AI systems were used, for what
purpose, and to what extent. Update `../templates/AI_USE_REGISTER.csv` whenever
a new tool or major use is introduced.

Likely ATLAS entries include:

- object-detection model and training platform;
- language model used by the running prototype;
- speech-to-text and text-to-speech systems;
- local fallback models;
- coding or research assistants;
- image generation or design tools used for booth/report materials.

For each entry, record what the team authored, what the tool generated, how the
team verified it, and whether it appears in the live robot.

## Team Authorship Evidence

- Git history tied to team members where practical;
- CAD versions and physical prototype photographs;
- labelled training scripts and experiment logs;
- test plans, raw results, and decision notes;
- rehearsal recordings showing each member's understanding;
- source licences and third-party component list.

The goal is not to pretend tools were unused. The goal is to prove that the
team made, understood, tested, and can defend the project.

## Privacy Questions Judges May Ask

- Does ATLAS record or retain visitor audio?
- Are images or video stored?
- Does it perform facial recognition?
- What text is sent to cloud providers?
- How long does conversational context last?
- Can a visitor delete or avoid a profile?
- What happens without internet?
- How are API keys and admin controls protected?

Keep answers consistent with:

- [ATLAS privacy policy](../../handoff/policies/PRIVACY.md)
- [Cloud LLM disclosure](../../handoff/policies/CLOUD_LLM_DISCLOSURE.md)

## Artwork And Dataset Rights

- Record the source URL and licence for every artwork image.
- Distinguish public-domain artwork from rights in a modern photograph or scan.
- Record who captured each training image and the permission/terms under which
  it is used.
- Avoid identifiable visitor faces in the dataset unless explicit, documented
  consent and a justified retention plan exist.
- Attribute required sources in the report, video, booth, and website.

## Security Before Publishing

- Scan Git changes for API keys and credentials.
- Never place secrets in screenshots, logs, QR-code targets, or sample configs.
- Rotate any credential that has been pasted into a chat, issue, document, or
  public repository.
- Store travel documents and minors' information outside the public GitHub
  repository.
