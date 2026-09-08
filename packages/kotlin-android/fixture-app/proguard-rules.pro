# Keep the minimal fixture entry point so minified runtime instrumentation can
# exercise the same SDK class-loading path as Debug.
-keep class dev.tempera.sdk.fixture.MainActivity { *; }
