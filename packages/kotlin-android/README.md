# Tempera SDK for Android

`dev.tempera:tempera-sdk-kotlin-android:0.12.0` is the Android runtime variant
of the Tempera Kotlin SDK. It shares the public client, auth, MCP, and JSON
surface with the dependency-free JVM artifact, but supplies the Android-only
OkHttp transport. It supports Android API 26+ and compiles with API 36.

The artifact advertises the same Gradle runtime capability as
`dev.tempera:tempera-sdk-kotlin:0.12.0`. A consumer must select one runtime
variant; Gradle metadata must reject a request that attempts to package both.

The fixture app is part of this build. It exercises the SDK on API 26 and API
36 in Debug and minified Release, including class loading for the base JSON,
auth, and MCP client types. It is a local qualification fixture and does not
contact an external service or publish to Maven Central.
