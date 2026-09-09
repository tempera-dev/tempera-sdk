package dev.tempera.sdk

/** JVM implementation of the shared default-transport factory. */
internal fun defaultTemperaTransport(): TemperaTransport = JdkHttpTransport()
