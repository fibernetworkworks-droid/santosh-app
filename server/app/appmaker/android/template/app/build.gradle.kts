// Made by Hoola App Sahayak. The server owns this file: generated screens never change it.
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
}

android {
    namespace = "hoola.app"
    compileSdk = 37

    defaultConfig {
        applicationId = "@@APP_ID@@"
        minSdk = 26
        targetSdk = 36
        versionCode = @@VERSION_CODE@@
        versionName = "@@VERSION_NAME@@"
    }

    signingConfigs {
        create("preview") {
            val ks = file("../keys/preview.p12")
            if (ks.exists()) {
                storeFile = ks
                storeType = "PKCS12"
                storePassword = System.getenv("HOOLA_PREVIEW_KEY_PASS") ?: "@@KEY_PASS@@"
                keyAlias = "preview"
                keyPassword = System.getenv("HOOLA_PREVIEW_KEY_PASS") ?: "@@KEY_PASS@@"
            }
        }
    }

    buildTypes {
        debug {
            if (file("../keys/preview.p12").exists()) signingConfig = signingConfigs.getByName("preview")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            if (file("../keys/preview.p12").exists()) signingConfig = signingConfigs.getByName("preview")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    lint {
        abortOnError = false
        checkReleaseBuilds = false
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.graphics)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.compose.foundation)
    implementation(libs.compose.material3)
    implementation(libs.coroutines.android)
    debugImplementation(libs.compose.ui.tooling)
}
