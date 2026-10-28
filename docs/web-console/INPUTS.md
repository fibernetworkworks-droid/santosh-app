# Hoola inputs: files, photos and live voice

Implements the five input capabilities in Hoola web branding. Existing file, conversation and live-voice APIs remain authoritative; no mobile, voice backend, model or PC source is changed.

Uploads, drag-and-drop and clipboard files use one pipeline. Six slots are reserved synchronously before image decoding to prevent concurrent-input overflows. Pending attachments block Send, show upload/ready state and image thumbnails, and can be cancelled. Switching conversations or signing out aborts pending uploads. Mixed image/text paste retains native text insertion. Limits remain six files and 25 MB each; large supported images retain the existing resize behavior.

A dedicated chat voice button starts the existing two-way voice service. The + menu also opens Voice. Cumulative captions update in place; turn_done events establish new caption rows. Mute and hang-up are accessible. Connection callbacks are scoped to the originating call, conversation and login. Cancelled microphone permissions cannot open a later call. The voice transcript UI is cleared on sign-out.

Completed voice turns are already stored by backend voice._save_turn and published as normal conversation messages. View saved conversation reloads the original call's conversation from the server; no transcript is written to browser localStorage. Partial live captions are not claimed as persisted. No audio recording/download feature is added.

Validation: 17 existing unit/contract tests; existing workspace browser walkthrough; new input/voice browser walkthrough covering picker, concurrent drop/paste limit, send guard, thumbnails, mixed paste, cancellation, simulated duplex audio, cumulative captions, mute, cleanup and saved-chat navigation; four backend voice tests including transcript persistence. Providers and audio are simulated: real microphone quality and live provider availability are not established by these tests.

Implementation is committed locally. Deployment remains separate.
