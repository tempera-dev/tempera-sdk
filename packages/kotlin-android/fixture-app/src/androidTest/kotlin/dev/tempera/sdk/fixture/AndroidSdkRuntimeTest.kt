package dev.tempera.sdk.fixture

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.core.app.ActivityScenario
import android.os.Looper
import java.util.concurrent.atomic.AtomicReference
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
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
            // URL resolution and the blocking SDK boundary belong on the
            // instrumentation worker, never ActivityScenario's UI callback.
            assertNotEquals(Looper.getMainLooper(), Looper.myLooper())
            val baseUrl = server.url("/").toString().removeSuffix("/")
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                val activity = AtomicReference<MainActivity>()
                scenario.onActivity { activity.set(it) }
                assertEquals("true:true", requireNotNull(activity.get()).executeLoopback(baseUrl))
            }
            assertEquals(2, server.requestCount)
        } finally {
            server.shutdown()
        }
    }
}
