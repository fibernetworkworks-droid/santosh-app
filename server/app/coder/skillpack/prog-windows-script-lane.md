---
name: prog-windows-script-lane
description: AHK/AutoIt/VBA scripts - the third automation lane
---
GOAL: reach the apps the other two lanes cannot - legacy Windows software, tray-only
apps, Office files - by WRITING a script she can read, not by pressing keys.

THE THREE LANES, in order of choice:
1. ax_* pehle (ax_snapshot / ax_find / ax_click / ax_set_value) - the accessibility
   tree is the most reliable door.
2. pixels doosre (screenshot / click / type) - when the tree does not expose the
   control but the eye can see it.
3. THIS lane aakhri, ya script-native asks par: AutoHotkey for hotkeys + window
   choreography, AutoIt for Win32 controls (ControlClick, WinList), VBA when the app
   IS Office - Excel/Word/Access macros are its native tongue and beat any UI driving.

AUTOHOTKEY v2 house style: the file starts with #Requires AutoHotkey v2.0 and
#SingleInstance Force; SetTitleMatchMode RegEx when titles vary; WinWait ->
WinActivate -> WinWaitActive, Send only after that; hotkeys ^!j:: style. Every block
gets a short Hinglish comment - the file is hers to keep and edit.

DELIVERY (the law):
- The script is a FILE: shown in chat with one line per block explaining what it does,
  then saved/pushed through the confirm card. Nothing runs by itself.
- Execution rides the gated run door (exit code + output shown) or her own
  double-click - uske tap ke bina ek bhi script nahi chalti.
- AutoHotkey missing? Offer the winget install door - her tap again.
- A macro that deletes, sends, or touches money: the script text is read back to her
  and her haan comes BEFORE the file even lands.

NEVER: Send keys to Win+R / Task Manager / lock-screen class surfaces (the same
blocked-keys law the PC lane keeps); disable AV or UAC; registry writes beyond the
app's own HKCU key; a network call inside the script unless the ask itself is a
network ask (then the library registry picks the package); a macro-enabled file sent
to her unasked.
