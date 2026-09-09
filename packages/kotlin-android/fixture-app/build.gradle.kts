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
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestCompileOnly("com.google.errorprone:error_prone_annotations:2.27.0")
    androidTestImplementation("androidx.test:core:1.6.1")
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

// Verify annotations resolve for test compilation without entering Android runtime artifacts.
tasks.register("verifyReleaseTestAnnotationClasspath") {
    doLast {
        fun modules(configuration: String) = configurations.getByName(configuration)
            .incoming.resolutionResult.allComponents.mapNotNull {
                it.id as? org.gradle.api.artifacts.component.ModuleComponentIdentifier
            }
        fun isAnnotation(module: org.gradle.api.artifacts.component.ModuleComponentIdentifier) =
            module.group == "com.google.errorprone" && module.module == "error_prone_annotations"
        fun isTracing(module: org.gradle.api.artifacts.component.ModuleComponentIdentifier) =
            module.group == "androidx.tracing" && module.module == "tracing"
        check(modules("releaseAndroidTestCompileClasspath").any(::isAnnotation)) { "Missing test compile annotation dependency" }
        check(modules("releaseAndroidTestRuntimeClasspath").none(::isAnnotation)) { "Compiler annotations leaked into test runtime dependencies" }
        check(modules("releaseRuntimeClasspath").none(::isTracing)) { "Tracing leaked into minified fixture app runtime" }
        check(modules("releaseAndroidTestRuntimeClasspath").any(::isTracing)) { "Test runner tracing dependency is missing from test runtime" }
        println("Error Prone annotations present only in Release AndroidTest compile classpath")
    }
}
