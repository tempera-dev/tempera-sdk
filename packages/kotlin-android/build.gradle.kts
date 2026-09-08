plugins {
    id("com.android.library") version "8.9.2"
    id("org.jetbrains.kotlin.android") version "2.1.20"
    `maven-publish`
}

group = "dev.tempera"
version = "0.12.0"

android {
    namespace = "dev.tempera.sdk"
    compileSdk = 36
    defaultConfig {
        minSdk = 26
        consumerProguardFiles("consumer-rules.pro")
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    publishing {
        singleVariant("release") {
            withSourcesJar()
        }
    }
}

kotlin {
    jvmToolchain(17)
}

kotlin.sourceSets.getByName("main").kotlin.apply {
    srcDir("../kotlin/src/main/kotlin")
    exclude("dev/tempera/sdk/JdkHttpTransport.kt")
    exclude("dev/tempera/sdk/JvmDefaultTransport.kt")
}

dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
    testImplementation("com.squareup.okhttp3:okhttp-tls:4.12.0")
}

configurations.configureEach {
    if (isCanBeConsumed) {
        // Keep ordinary coordinate resolution alongside the mutual exclusion.
        outgoing.capability("dev.tempera:tempera-sdk-kotlin-android:$version")
        outgoing.capability("dev.tempera:tempera-sdk-runtime:$version")
    }
}

publishing {
    publications {
        register<MavenPublication>("release") {
            afterEvaluate { from(components["release"]) }
            artifactId = "tempera-sdk-kotlin-android"
        }
    }
    repositories {
        maven {
            name = "fixture"
            url = uri(providers.gradleProperty("fixtureRepository").getOrElse(layout.buildDirectory.dir("fixture-repository").get().asFile.absolutePath))
        }
    }
}

tasks.register("publishFixturePublication") {
    dependsOn("publishReleasePublicationToFixtureRepository")
}
