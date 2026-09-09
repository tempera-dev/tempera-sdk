package dev.tempera.sdk

import java.net.http.HttpClient
import org.junit.jupiter.api.Assertions.assertDoesNotThrow
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class DefaultTransportTest {
    @Test
    fun jvmFactoryKeepsTheJdkTransportDefault() {
        assertTrue(defaultTemperaTransport() is JdkHttpTransport)
    }

    @Test
    fun existingJvmTransportAndClientConstructorsRemainUsable() {
        assertDoesNotThrow {
            JdkHttpTransport(HttpClient.newBuilder().build())
            TemperaAuth("https://issuer.example.test", apiKey = "tp_test")
            TemperaClient()
            TemperaMcpClient("https://issuer.example.test/mcp", bearer = "tp_test")
        }
    }
}
