# v0.72 Release builds shrink and rename classes (R8). Native / reflective code looks some up BY NAME:

# ONNX Runtime (Silero VAD in calls, "Hey Santosh" wake word): its JNI calls FindClass / GetMethodID on these.
# Stripped -> "JNI DETECTED ERROR: java_class == null in OrtSession.run" -> SIGABRT the moment a call starts.
-keep class ai.onnxruntime.** { *; }
-keepclassmembers class ai.onnxruntime.** { *; }
-dontwarn ai.onnxruntime.**

# flutter_local_notifications reads its saved schedule with Gson TypeToken (needs generic signatures).
# Stripped -> "Missing type parameter" in ScheduledNotificationBootReceiver after a reboot / app update.
-keepattributes Signature
-keepattributes *Annotation*
-keepattributes EnclosingMethod,InnerClasses
-keep class com.google.gson.reflect.TypeToken { *; }
-keep class * extends com.google.gson.reflect.TypeToken
-keep class com.dexterous.** { *; }
-dontwarn com.dexterous.**

# Hoola's own Kotlin (services / receivers named in the manifest are kept anyway; keep the rest readable in
# crash reports and safe for reflection)
-keep class com.newtika.santosh.** { *; }
