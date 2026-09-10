// The generated Tempera SDK for Kotlin/JVM.
//
// It has no runtime dependencies on purpose: everything it needs is in JDK 17
// (`java.net.http` for HTTP, `java.security` for SHA-256 and the CSPRNG,
// `java.util.Base64` for base64url). Adding one would put a version
// constraint on every JVM application that adopts the SDK, so the JSON model
// and the HTTP client are written here instead.
//
// Build: ./gradlew build          (or `gradle build` with a local Gradle 8.5+)
// Test:  ./gradlew test

plugins {
    kotlin("jvm") version "2.0.21"
    `java-library`
}

group = "dev.tempera"

// Kept in step with packages/typescript/package.json, packages/python/pyproject.toml,
// packages/rust/Cargo.toml, and TemperaSdk.VERSION.
version = "0.13.0"

repositories {
    mavenCentral()
}

dependencies {
    // Test-only. The main source set must stay dependency-free.
    testImplementation(platform("org.junit:junit-bom:5.10.2"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

kotlin {
    jvmToolchain(17)
}

java {
    withSourcesJar()
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
    testLogging {
        events("passed", "skipped", "failed")
    }
}
