plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "dev.tempera.sdk.fixture"
    compileSdk = 36
    defaultConfig {
        applicationId = "dev.tempera.sdk.fixture"
        minSdk = 26
        targetSdk = 36
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    testBuildType = providers.gradleProperty("fixtureTestBuildType").getOrElse("debug")
    buildTypes {
        getByName("release") {
            isMinifyEnabled = true
            signingConfig = signingConfigs.getByName("debug")
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin { jvmToolchain(17) }

dependencies {
    implementation(project(":"))
    implementation("androidx.activity:activity-ktx:1.10.1")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:core:1.6.1")
    androidTestImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
}

val jvmRuntime by configurations.creating {
    isCanBeConsumed = false
    isCanBeResolved = true
}
val androidRuntime by configurations.creating {
    isCanBeConsumed = false
    isCanBeResolved = true
}
val runtimeVariantConflict by configurations.creating {
    isCanBeConsumed = false
    isCanBeResolved = true
}

dependencies {
    add(jvmRuntime.name, "dev.tempera:tempera-sdk-kotlin:0.12.0")
    add(androidRuntime.name, "dev.tempera:tempera-sdk-kotlin-android:0.12.0")
    add(runtimeVariantConflict.name, "dev.tempera:tempera-sdk-kotlin:0.12.0")
    add(runtimeVariantConflict.name, "dev.tempera:tempera-sdk-kotlin-android:0.12.0")
}

tasks.register("verifyRuntimeVariantConflict") {
    dependsOn(":publishFixturePublication")
    doLast {
        check(jvmRuntime.resolve().isNotEmpty()) { "published JVM artifact did not resolve" }
        check(androidRuntime.resolve().isNotEmpty()) { "published Android artifact did not resolve" }
        val failure = runCatching { runtimeVariantConflict.resolve() }.exceptionOrNull()
        val diagnostic = generateSequence(failure) { it.cause }.joinToString("\n") { it.message.orEmpty() }
        check(failure != null && diagnostic.contains("capability", ignoreCase = true) && diagnostic.contains("conflict", ignoreCase = true)) {
            "expected shared runtime capability conflict after both artifacts resolved independently: $diagnostic"
        }
    }
}
