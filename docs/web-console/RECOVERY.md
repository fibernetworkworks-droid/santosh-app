# Web console recovery

Prepared against main commit 120ed01705293c244bb9a6adac2e78e898f7ea35 (0.210.0).

The web features were previously installed as static files from separate release branches. The production deployment later copied server/app from main, whose console HTML, CSS and JS still contained the older interface. Newly added workspace files remained on disk but were no longer referenced by the active HTML. A check for the CSS file alone therefore incorrectly suggested that the integration was still active.

This recovery restores all web changes on the latest main without altering the newer backend, Drive, voice, mobile or PC work. The nine existing console cache stamps retain version 0.210.0. Web assets have independent cache keys.

Included: creative studio forms connected to chat; inline results and reference reuse; workspace width/expansion; removal of the top bar; larger bold sidebar text; continuous sidebar scrolling; draggable sidebar divider with remembered width; centered chat/composer and stable scrollbar gutters.

Validation: Chromium workflow/responsive walkthrough including alignment, sidebar drag/persistence and scrolling; 12 backend/deployment/session tests; 10 rendering tests; diff whitespace check.

Permanent release order: review and merge the web-only recovery into main, then deploy its seven console assets using the supplied static-only deployment workflow. Do not deploy the whole backend solely for this recovery. Keep [skip ci] on a web-only merge if no APK release is intended. The owner explicitly approved merging this recovery into main and deploying it.

The deployment workflow now checks the public HTML references the updated stylesheet and checks the public stylesheet contains the alignment rules, in addition to checking all installed asset bytes on the origin.

Earlier publication was blocked when automatic approval review reached its usage limit. Publication and deployment are being retried following the owner’s explicit approval.
