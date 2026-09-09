package dev.tempera.sdk

/** Android implementation of the shared default-transport factory. */
internal fun defaultTemperaTransport(): TemperaTransport = OkHttpTemperaTransport()
