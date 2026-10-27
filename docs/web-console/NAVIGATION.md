# Hoola web navigation

Implements the five navigation capabilities in Hoola branding: conversation sidebar, remembered collapse/expand, paginated Chats and tasks, accessible overflow menus, and inline rename.

History loads 200 conversations per page through the existing authenticated console list endpoint with a new optional offset. The shared list helper defaults to offset zero; mobile callers keep their existing behavior. Archived conversations have a separate filter. Working filters the loaded conversations by real busy state; this is conversation history, not a new independent job database. Title filtering applies to loaded pages; existing global search searches message content.

Rename uses the existing PATCH endpoint, validates nonempty titles, saves once on Enter/Save, cancels on Escape or leaving the field, and preserves input after errors. Menus support arrow keys, Home/End, Escape and focus restoration. Sidebar collapse state is remembered. History supports keyboard focus containment and touch widths.

Validation: seven backend conversation/history tests; thirteen progress/result tests; browser checks for 205 paginated conversations, title filter, working filter, rename save/cancel, menu Escape, collapse persistence, and desktop/phone layouts. Prior creative workspace and progress checks remain included.

Release requires console assets plus the small console pagination change in chats.py and main.py. A console-only deployment does not install pagination. Existing prefill fixes and the running console must be preserved. No Flutter, Android, desktop, PC, model routing or voice changes.
