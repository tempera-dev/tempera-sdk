package dev.tempera.sdk.fixture

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.core.app.ActivityScenario
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AndroidSdkRuntimeTest {
    @Test fun authMcpAndBaseJsonClassesLoadOnDevice() {
        val server = MockWebServer()
        server.start()
        try {
            server.enqueue(MockResponse().setBody("{\"ok\":true}"))
            server.enqueue(MockResponse().setBody("{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"ok\":true}}"))
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    assertEquals("true:true", activity.executeLoopback(server.url("/").toString().removeSuffix("/")))
                }
            }
            assertEquals(2, server.requestCount)
        } finally {
            server.shutdown()
        }
    }
}
