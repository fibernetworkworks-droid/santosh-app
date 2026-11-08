---
name: me-typography
description: Fonts and icons - template typography, license laws
---
GOAL: template ka look 90% typography decide karta hai - font sahi to
card premium, font galat to puri mehnat bekaar. Do syllabus:
brabadu/awesome-fonts (free fonts, display, workhorse, variable,
pairings ka catalog) aur vicky002/awesome-icons (icon sets ka
catalog). Hoola har template me inhi upar typography laws chalata
hai - fonts aur icons bhi ASSET hai, unka license pehle.

TYPING LAWS (har template pe, bina exception):
1. MAX 2 FAMILIES: ek DISPLAY (sirf headline/bade size pe, attitude
   wala) + ek WORKHORSE (body, captions, buttons - har size pe
   padhne layak). Teesri family ghusi to design galt hai, lane nahi.
2. EK SIZE LADDER: sizes fixed steps me - jaise 12/14/16/20/28/40.
   Template bhar me wahi ladder; har card apni nayi size invent nahi
   karta. Same ladder photo_banao ke cards, graphic ke posters,
   hoola_frames ke titles pe bhi chalta hai - ek template family,
   ek scale.
3. LOADING sirf app/fonts lane se: font file wahin register hoti
   hai, tenant ke andar hi; template me random CDN link nahi.
   Register hua ya nahi - render karke dekhna hi proof hai.
4. ICONS EK FAMILY: ek template me icon set ek hi family ka - stroke
   weight, corner radius, filled/outline sab match kare. Do families
   mix = design me chori dikhti hai. awesome-icons se pehle family
   chuno, phir usi ke andar raho.
5. LICENSE CHECK + NOTE: OFL ya clear free license? Commercial use
   allowed? Attribution chahiye? Har font/icon ke saath license line
   remember me save - source, license, date. Sold template me
   unlicensed font = sabse bada paap.

WORKFLOW (short): need samjho (display ka mood, body ki density) ->
awesome-fonts se pairing chuno -> license check -> app/fonts me
register -> EK TEST CARD render (dono family, ladder ke top aur
bottom size) -> output padho -> tab template me lagao. Icons:
awesome-icons se ek family -> license note -> template.

THE LAWS: license check kisi bhi font/icon se pehle (asset hai, wahi
niyam); printed output hi evidence - render proof ke bina koi font
verdict nahi; template publish se pehle ask_approval; font file
tenant ke bahar kisi ko nahi jati.

FALLBACK TEST: render me font aayi hi nahi (system fallback dikha) to
"fonts theek" bolna mana - app/fonts registration dobara karo, path
check karo, phir render. Kaam tab poora jab printed render sahi font
dikhaye.

NEVER: unlicensed font sold template me embed karna; 4 fonts ek card
me dalna; do icon families ek template me mix karna; license ke bina
font file embed karna; rendering check ke bina "fonts theek" bolna
(printed render proof hi sach hai); ladder todkar har element ko apni
marzi ka size dena.
