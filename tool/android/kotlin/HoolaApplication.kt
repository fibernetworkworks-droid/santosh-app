package com.newtika.santosh

import android.app.Application

/** v0.70 Runs first in every Hoola process (screen, services, alarms, push): the crash recorder is on from the start. */
class HoolaApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        try { CrashGuard.install(this) } catch (_: Throwable) {}
    }
}
