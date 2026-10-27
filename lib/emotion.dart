/// Santosh's feelings: what he reads in your words, and how he shows it.
///
/// Fast and on-device: a weighted lexicon for Hinglish, Hindi (Devanagari), Marathi and English,
/// plus punctuation and intensity cues. Results feed [Mood] in the app state, which decays back
/// to calm, and keeps a short memory (if you were stressed, he stays gentle for a while).
library;

import 'package:flutter/material.dart';

enum Mood { idle, listening, happy, excited, care, think, wow, work, talking }

class MoodStyle {
  const MoodStyle(this.label, this.aura, this.pose, this.thought);
  final String label;
  final Color aura;
  final String pose; // asset
  final String thought; // thought bubble text
}

const _H = 'assets/images/santosh_happy.png';
const _W = 'assets/images/santosh_working.png';
const _T = 'assets/images/santosh_thinking.png';

const moodStyles = <Mood, MoodStyle>{
  Mood.idle: MoodStyle('Taiyaar', Color(0xFFFFB15C), _H, ''),
  Mood.listening: MoodStyle('Sun raha', Color(0xFF2DD4BF), _H, 'Haan, boliye…'),
  Mood.happy: MoodStyle('Khush', Color(0xFFFFB15C), _H, 'Mazaa aa gaya!'),
  Mood.excited: MoodStyle('Josh mein', Color(0xFFF472B6), _H, 'Kya baat hai!'),
  Mood.care: MoodStyle('Fikar', Color(0xFF60A5FA), _H, 'Main hoon na'),
  Mood.think: MoodStyle('Soch raha', Color(0xFFA78BFA), _T, 'Hmm…'),
  Mood.wow: MoodStyle('Hairaan', Color(0xFFFDE047), _H, 'Sach mein?!'),
  Mood.work: MoodStyle('Kaam par', Color(0xFF34D399), _W, 'Kar raha hoon…'),
  Mood.talking: MoodStyle('Bol raha', Color(0xFFFFB15C), _H, ''),
};

class _Cue {
  const _Cue(this.mood, this.weight, this.words);
  final Mood mood;
  final double weight;
  final List<String> words;
}

// Lower-case substrings. Roman Hinglish/Marathi + Devanagari + English.
const _cues = <_Cue>[
  _Cue(Mood.care, 3, [
    'tension', 'pareshan', 'pareshaan', 'dukhi', 'udaas', 'udas', 'sad', 'stress', 'thak gaya', 'thak gayi', 'thaka', 'bimar', 'bemar',
    'sick', 'dard', 'pain', 'problem', 'dikkat', 'mushkil', 'ro raha', 'ro rahi', 'akela', 'lonely', 'dar lag', 'darr', 'worried',
    'chinta', 'fikar', 'ghabra', 'bura lag', 'hurt', 'nahi ho raha', 'fail', 'loss', 'nuksan', 'hospital', 'accident', 'jhagda',
    'gussa', 'naraz', 'angry', 'frustrat', 'bekar', 'kantala', 'tras', 'dukh', 'tired',
    'परेशान', 'दुखी', 'उदास', 'चिंता', 'तनाव', 'थक', 'बीमार', 'दर्द', 'मुश्किल', 'अकेला', 'गुस्सा', 'त्रास', 'दुःख', 'काळजी',
  ]),
  _Cue(Mood.excited, 3, [
    'promotion', 'selection', 'select ho', 'job lag', 'naukri lag', 'shaadi', 'engagement', 'baby', 'beta hua', 'beti hui', 'jeet',
    'won', 'win', 'first rank', 'topper', 'pass ho gaya', 'pass ho gayi', 'new car', 'nayi gaadi', 'naya ghar', 'birthday hai',
    'party', 'celebrate', 'yay', 'woohoo', 'awesome', 'amazing', 'zabardast', 'kamaal', 'bahut badhiya', 'mast', 'bhari',
    'जीत', 'शादी', 'प्रमोशन', 'बधाई', 'जबरदस्त', 'कमाल', 'मस्त', 'भारी',
  ]),
  _Cue(Mood.happy, 2, [
    'thank', 'thanks', 'shukriya', 'dhanyavad', 'dhanyawad', 'great', 'good', 'nice', 'badhiya', 'accha laga', 'achha laga', 'khush',
    'happy', 'perfect', 'sahi hai', 'ho gaya', 'done', 'love', 'pyaar', 'wah', 'waah', 'arre wah', 'shabash', 'chhan', 'chan',
    'छान', 'धन्यवाद', 'शुक्रिया', 'बढ़िया', 'खुश', 'वाह', 'अच्छा लगा',
  ]),
  _Cue(Mood.wow, 3, [
    'kya?', 'sach me', 'sach mein', 'seriously', 'really?', 'what?', 'itna', 'itne', 'kaise ho gaya', 'unbelievable', 'shocking',
    'omg', 'oh my', 'baap re', 'arre baap', 'hairan', 'surprise', 'kharra', 'kharokhar', 'काय', 'सच में', 'अरे बाप', 'इतना',
  ]),
  _Cue(Mood.think, 1.5, [
    'kaise', 'kyon', 'kyu', 'kab', 'kitna', 'kitne', 'kaun', 'kahan', 'konsa', 'kaunsa', 'kasa', 'kadhi', 'kuthe', 'kiti',
    'how', 'why', 'when', 'where', 'which', 'what', 'explain', 'samjhao', 'batao', 'sochna', 'idea', 'suggest', 'compare', 'best',
    'कैसे', 'क्यों', 'कब', 'कितना', 'कहाँ', 'कौन', 'कसे', 'केव्हा', 'कुठे', 'किती', 'बताओ',
  ]),
  _Cue(Mood.work, 2, [
    'bhar do', 'bharo', 'pay', 'order', 'mangwa', 'mangva', 'book', 'bhejo', 'bhej do', 'send', 'set kar', 'laga do', 'yaad dila',
    'remind', 'alarm', 'mail', 'email', 'draft', 'banao', 'bana do', 'campaign', 'cab', 'uber', 'ola', 'bill', 'recharge',
    'bhara', 'kara', 'pathav', 'भर दो', 'भेजो', 'मंगवाओ', 'बुक', 'याद दिला', 'बनाओ', 'पाठव', 'करा',
  ]),
];

class Feeling {
  const Feeling(this.mood, this.intensity);
  final Mood mood;
  final double intensity; // 0..1
}

/// What does this text feel like? null = nothing clear (stay as you are).
Feeling? feel(String text) {
  final t = ' ${text.toLowerCase()} ';
  if (t.trim().isEmpty) return null;
  final score = <Mood, double>{};
  for (final c in _cues) {
    for (final w in c.words) {
      if (t.contains(w)) score[c.mood] = (score[c.mood] ?? 0) + c.weight;
    }
  }
  final bangs = '!'.allMatches(text).length;
  final asks = '?'.allMatches(text).length;
  if (bangs >= 2) {
    score[Mood.excited] = (score[Mood.excited] ?? 0) + 1;
    score[Mood.wow] = (score[Mood.wow] ?? 0) + .8;
  }
  if (text.contains('?!') || text.contains('!?')) score[Mood.wow] = (score[Mood.wow] ?? 0) + 2;
  if (asks > 0) score[Mood.think] = (score[Mood.think] ?? 0) + .8;
  final caps = RegExp(r'[A-Z]').allMatches(text).length;
  final letters = RegExp(r'[A-Za-z]').allMatches(text).length;
  if (letters > 8 && caps / letters > .6) score[Mood.excited] = (score[Mood.excited] ?? 0) + .6; // SHOUTING = energy
  // care outranks happy when both appear ("thank you, but bahut tension hai")
  if ((score[Mood.care] ?? 0) > 0) score[Mood.happy] = (score[Mood.happy] ?? 0) * .4;
  if (score.isEmpty) return null;
  final best = score.entries.reduce((a, b) => a.value >= b.value ? a : b);
  if (best.value < 1.4) return null;
  return Feeling(best.key, (best.value / 6).clamp(.3, 1.0));
}
