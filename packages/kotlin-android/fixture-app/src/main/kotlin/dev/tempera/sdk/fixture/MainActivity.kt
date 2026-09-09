package dev.tempera.sdk.fixture

import android.app.Activity
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.os.Build
import android.os.Bundle
import android.os.Process
import android.util.Log
import android.widget.TextView
import dev.tempera.sdk.TemperaAuth
import dev.tempera.sdk.TemperaJson
import dev.tempera.sdk.TemperaMcpClient
import dev.tempera.sdk.TemperaClient
import dev.tempera.sdk.TemperaClientConfiguration
import dev.tempera.sdk.TemperaRetryPolicy
import dev.tempera.sdk.TemperaSurface
import dev.tempera.sdk.OkHttpTemperaTransport
import java.io.FileInputStream
import java.net.URI
import java.security.MessageDigest
import org.json.JSONObject

fun sdkClassLoadingSummary(): String {
    val auth = TemperaAuth("https://issuer.example.test", apiKey = "tp_fixture")
    val mcp = TemperaMcpClient(url = auth.mcpUrl, bearer = "fixture-token")
    val json = requireNotNull(TemperaJson.parse("{\"fixture\":true}"))
    return "${TemperaSurface.mcpPath}:${mcp.url}:${json.isNull()}"
}

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(TextView(this).apply { text = sdkClassLoadingSummary() })
        handleReleaseQualificationIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleReleaseQualificationIntent(intent)
    }

    fun executeLoopback(baseUrl: String): String {
        val transport = OkHttpTemperaTransport()
        val configuration = TemperaClientConfiguration(retry = TemperaRetryPolicy(maxAttempts = 1))
        val client = TemperaClient(
            baseUrls = mapOf("controlPlane" to baseUrl),
            transport = transport,
            configuration = configuration,
        )
        val base = client.request("controlPlane", "/base", bearer = "fixture")
        val ping = TemperaMcpClient(
            url = "$baseUrl/mcp",
            bearer = "fixture",
            transport = transport,
            configuration = configuration,
        ).ping()
        return "${base["ok"]?.asBoolean()}:${ping["ok"]?.asBoolean()}"
    }

    private fun handleReleaseQualificationIntent(intent: Intent) {
        if (intent.action != RELEASE_QUALIFICATION_ACTION) return
        val request =
            runCatching {
                ReleaseQualificationRequest(
                    nonce = requireNotNull(intent.getStringExtra(EXTRA_NONCE)),
                    baseUrl = requireNotNull(intent.getStringExtra(EXTRA_BASE_URL)),
                    expectedApi = requireNotNull(intent.getStringExtra(EXTRA_EXPECTED_API)),
                ).also { it.validate() }
            }.getOrElse {
                Log.e(RELEASE_QUALIFICATION_LOG_TAG, "{\"status\":\"error\",\"error\":\"invalid_request\"}")
                return
            }
        Thread(
            Runnable {
                val apkSha256 = runCatching(::installedApkSha256).getOrElse {
                    reportReleaseQualification(request, "error", null, null)
                    return@Runnable
                }
                val result =
                    runCatching { executeLoopback(request.baseUrl) }.getOrElse {
                        reportReleaseQualification(request, "error", apkSha256, null)
                        return@Runnable
                    }
                reportReleaseQualification(request, "ok", apkSha256, result)
            },
            "tempera-sdk-release-qualification",
        ).start()
    }

    private fun installedApkSha256(): String {
        val digest = MessageDigest.getInstance("SHA-256")
        var total = 0L
        FileInputStream(applicationInfo.sourceDir).use { input ->
            val buffer = ByteArray(HASH_BUFFER_BYTES)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                total += read
                check(total <= MAX_APK_BYTES) { "fixture APK exceeds release qualification hash bound" }
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString(separator = "") { byte -> "%02x".format(byte.toInt() and 0xff) }
    }

    private fun reportReleaseQualification(
        request: ReleaseQualificationRequest,
        status: String,
        apkSha256: String?,
        result: String?,
    ) {
        val payload =
            JSONObject()
                .put("nonce", request.nonce)
                .put("api", Build.VERSION.SDK_INT)
                .put("pid", Process.myPid())
                .put("package", packageName)
                .put("debuggable", applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0)
                .put("apk_sha256", apkSha256)
                .put("status", status)
                .put("result", result)
        Log.i(RELEASE_QUALIFICATION_LOG_TAG, payload.toString())
    }

    private data class ReleaseQualificationRequest(
        val nonce: String,
        val baseUrl: String,
        val expectedApi: String,
    ) {
        fun validate() {
            check(NONCE_PATTERN.matches(nonce)) { "release qualification nonce was invalid" }
            check(expectedApi.toIntOrNull() == Build.VERSION.SDK_INT) { "release qualification API was invalid" }
            val uri = URI(baseUrl)
            check(uri.scheme == "http" && uri.host == "127.0.0.1" && uri.port in 1..65535) {
                "release qualification URL origin was invalid"
            }
            check(uri.rawPath.isNullOrEmpty() && uri.rawQuery == null && uri.rawUserInfo == null && uri.rawFragment == null) {
                "release qualification URL must not contain a path, query, user info, or fragment"
            }
        }
    }

    private companion object {
        const val RELEASE_QUALIFICATION_ACTION = "dev.tempera.sdk.fixture.action.QUALIFY_RELEASE"
        const val RELEASE_QUALIFICATION_LOG_TAG = "TemperaSdkRelease"
        const val EXTRA_NONCE = "tempera.release.nonce"
        const val EXTRA_BASE_URL = "tempera.release.base_url"
        const val EXTRA_EXPECTED_API = "tempera.release.expected_api"
        const val HASH_BUFFER_BYTES = 16 * 1024
        const val MAX_APK_BYTES = 64L * 1024L * 1024L
        val NONCE_PATTERN = Regex("[0-9a-f]{32}")
    }
}
