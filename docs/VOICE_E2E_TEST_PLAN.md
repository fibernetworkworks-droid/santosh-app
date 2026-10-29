# Voice call: end-to-end test plan (v0.241.0, voice Phases 1-5)

Who: the owner, on her own Android phone, with the new APK. Time: about 75 minutes in one sitting, or the four
rounds on different days. Every test has a "pass if" line. Mark each one in **Profile > Call ki jaanch** where it
exists there (the 18 ear / phone checks); the rest are noted here.

## 0. Setup (5 min)
1. VPS: deploy v0.241.0 (commands below), then `pm2 logs santosh --lines 50` shows no errors at start.
2. Install the APK for v0.241.0 and open Hoola. Profile shows v0.241.0.
3. Profile > Call ki jaanch opens. Before any call it says "Abhi koi call record nahi hui" or shows older calls.
4. A quiet room for Round A. Earphones and a second phone (or a friend) for Round C.

## Round A: talk (20 min, quiet room). Ear test checks 1-10
| # | Do | Pass if |
|---|----|---------|
| A1 | Start a call, say "Hello, kaise ho?" | He answers within about a second, one short natural line (**hello_speed**) |
| A2 | Tell a 20-30 s story with pauses | He does not jump in; at most a soft "haan... / achha..."; he answers at the end (**long_story**) |
| A3 | While he speaks a long reply, say "ruko ruko" | He stops at once; your words are not lost (**interrupt**) |
| A4 | "Aaj ke 3 kaam batao" | One by one, with pauses, not in one breath (**list_pace**) |
| A5 | "Aaj din bahut kharab gaya" | Soft, slow voice; no cheerful "wah!" (**feeling_low**) |
| A6 | "Mera order aa gaya, bahut khush hoon!" | Glad voice, one normal line, no over-acting (**feeling_glad**) |
| A7 | "Aaj ka mausam batao" | An "ek second" at his normal loudness (not louder or quieter than him), then the answer; no long silence (**tool_wait**) |
| A8 | Give a long job ("ek document banao..."), keep talking | When it is done he tells you ONCE at a pause, never cutting you off (**job_news**) |
| A9 | Whole call in Hinglish with a few English words | He stays in Hinglish (**hinglish**) |
| A10 | Ask for something that shows a card (e.g. open something on PC), then say "haan karo" | The card goes ahead without a tap; a money card never goes ahead by voice (**yes_approve**) |
| A11 | Ask the same question twice in a row | He answers, but does not repeat his earlier reply word for word |
| A12 | Sit silent next to a fan or TV for 30 s mid-call | He does not answer the noise and does not say "connection dheema hai" |

## Round B: long call (20 min)
| # | Do | Pass if |
|---|----|---------|
| B1 | Keep one call going for 15+ minutes (Google moves the connection near the 10-minute mark) | No cut line, no "hello" again; he still remembers what you said at the start (**long_call**) |
| B2 | At about minute 12 ask "shuru mein maine kya kaha tha?" | He tells you correctly |
| B3 | Hang up, then call again within a minute | The new call carries on ("wahi kaam pe chalte hain"), no fresh hello (**server_restart**) |

## Round C: real phone (20 min). Phone checks 11-18
| # | Do | Pass if |
|---|----|---------|
| C1 | Mid-call, turn Wi-Fi off | A few seconds of "jud raha hoon", then the same conversation; anything he said during the gap is played (**net_switch**) |
| C2 | Have someone call your number, pick up, talk, hang up | Hoola stays silent on hold; afterwards it carries on (**gsm_call**) |
| C3 | Let a WhatsApp call come in | Hoola goes quiet and takes no sound; comes back after (**whatsapp_call**) |
| C4 | Plug in earphones, then a Bluetooth headset, then take them out | Sound moves at once each time; the call keeps going (**headset**) |
| C5 | "Spotify pe koi gaana lagao", then talk | Song and call both run; he does not treat the lyrics as your words (**song**) |
| C6 | Lock the phone for 1 minute and keep talking | The call keeps going both ways (**lock_screen**) |
| C7 | Walk away until the signal is weak, then come back | The call heals or ends honestly with "dobara bulaaiye", never a dead line |
| C8 | Restart the server mid-call (`pm2 restart santosh`) | The phone hears "Server update ho raha hai", the call ends cleanly, and the next call picks up the thread |

## Round D: numbers (10 min, after Rounds A-C)
Open **Profile > Call ki jaanch** (pull to refresh):
| # | Check | Pass if |
|---|-------|---------|
| D1 | Calls list | Every call you just made is there with a grade (achhi / theek / kharab) and how it ended |
| D2 | Reply start: normal / slowest 10% / slowest 1% | p50 under 1,200 ms, p90 under 2,500 ms, p99 under 4,000 ms |
| D3 | Dead air, talk-over, repeats | Dead air small (under ~5 s per call); talk-over and repeats near 0 per 100 |
| D4 | C8 call | Shows "server update" as the end; C1 shows no "line toot gayi" if it healed |
| D5 | Ear test list | Marks for all 18 checks; after the second version you test, each card shows "pehle se behtar / kharab / pehle jaisa" |
| D6 | Alert | No red "Dhyaan dijiye" banner unless the calls were really slow or broke; at most one push a day |
| D7 | Rate a call 👎 | That call turns "kharab" with "aapne 👎 diya" |

## What to send back
- The Call ki jaanch screenshot (top card + recent calls).
- Any Galat with a note. The note is saved per version, so the next fix can be measured against it.
- VPS: `curl -s -H "Authorization: Bearer <her key>" https://<host>/api/voice/quality?days=1` output if a number looks wrong
  (numbers only, no call words in it).

## Deploy
```
cd ~/santosh_app && git fetch && git checkout main && git reset --hard origin/main
cp -r ~/santosh_app/server/app ~/apps/santosh-core/ && pm2 restart santosh --update-env --kill-timeout 12000
```
