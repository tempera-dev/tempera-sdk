package dev.tempera.sdk.fixture

import android.app.Activity
import android.os.Bundle
import android.widget.TextView
import dev.tempera.sdk.TemperaAuth
import dev.tempera.sdk.TemperaJson
import dev.tempera.sdk.TemperaMcpClient
import dev.tempera.sdk.TemperaClient
import dev.tempera.sdk.TemperaClientConfiguration
import dev.tempera.sdk.TemperaRetryPolicy
import dev.tempera.sdk.TemperaSurface
import dev.tempera.sdk.OkHttpTemperaTransport

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
}
