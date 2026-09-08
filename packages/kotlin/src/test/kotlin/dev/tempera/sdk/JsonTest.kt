package dev.tempera.sdk

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class JsonTest {

    @Test
    fun objectsKeepTheirMemberOrderThroughParseAndSerialize() {
        val source = """{"b":1,"a":2,"c":{"z":[1,2,3],"y":null}}"""
        val parsed = TemperaJson.parse(source)
        assertEquals(source, parsed?.serialized())
        assertEquals(listOf("b", "a", "c"), parsed?.asObject()?.map { it.key })
    }

    @Test
    fun serializationIsCompactAndUtf8() {
        val value = temperaJsonObject("name" to "organization’s", "emoji" to "🚀")
        assertEquals("""{"name":"organization’s","emoji":"🚀"}""", value.serialized())
        assertTrue(value.serialized().toByteArray(Charsets.UTF_8).contentEquals(value.serializedBytes()))
    }

    @Test
    fun controlCharactersAndQuotesAreEscaped() {
        val value = TemperaJson.Text("quote \" slash \\ tab \t newline \n bell \u0007")
        assertEquals(
            "\"quote \\\" slash \\\\ tab \\t newline \\n bell \\u0007\"",
            value.serialized(),
        )
        assertEquals(value, TemperaJson.parse(value.serialized()))
    }

    @Test
    fun numbersRoundTripWithoutBecomingFloats() {
        assertEquals(
            TemperaJson.Arr(
                listOf(
                    TemperaJson.Int64(0),
                    TemperaJson.Int64(-1),
                    TemperaJson.Decimal(2.5),
                    TemperaJson.Decimal(1000.0),
                )
            ),
            TemperaJson.parse("[0,-1,2.5,1e3]"),
        )
        assertEquals(TemperaJson.Int64(42), TemperaJson.parse("42"))
        assertEquals("42", TemperaJson.Int64(42).serialized())
        assertEquals("2.5", TemperaJson.Decimal(2.5).serialized())
        assertEquals("3", TemperaJson.Decimal(3.0).serialized())
        assertEquals("null", TemperaJson.Decimal(Double.NaN).serialized())
    }

    @Test
    fun unicodeEscapesAndSurrogatePairsDecode() {
        // Escaped rather than raw strings: the JSON source must carry the two
        // literal characters `\` and `u`, not a Kotlin-decoded character.
        assertEquals(
            TemperaJson.Text("emoji 😀 done"),
            TemperaJson.parse("\"emoji \\uD83D\\uDE00 done\""),
        )
        assertEquals(TemperaJson.Text("é"), TemperaJson.parse("\"\\u00e9\""))
        assertEquals(TemperaJson.Text("slash / ok"), TemperaJson.parse("\"slash \\/ ok\""))
        // A lone high surrogate is not decodable.
        assertNull(TemperaJson.parse("\"\\uD83D\""))
    }

    @Test
    fun malformedDocumentsAreRejected() {
        // Leading zeros are accepted, exactly as the Rust scanner accepts them:
        // both read producer responses, never caller input.
        val bad =
            listOf(
                "",
                "   ",
                "{",
                """{"a":1} extra""",
                "{\"a\":\"line\nbreak\"}",
                "[1,]",
                "{'a':1}",
                "tru",
            )
        for (input in bad) {
            assertNull(TemperaJson.parse(input), input)
        }
    }

    @Test
    fun accessorsReadTheExpectedShapes() {
        val value =
            temperaJsonObject(
                "s" to "x",
                "i" to 7,
                "b" to true,
                "n" to null,
                "a" to listOf(1, 2),
            )
        assertEquals("x", value["s"]?.asString())
        assertEquals(7L, value["i"]!!.asLong()!!)
        assertEquals(7, value["i"]!!.asInt()!!)
        assertEquals(true, value["b"]!!.asBoolean()!!)
        assertTrue(value["n"]!!.isNull())
        assertEquals(2, value["a"]!!.asArray()!!.size)
        assertNull(value["missing"])
        assertNull(TemperaJson.Text("x")["key"])
    }

    @Test
    fun plainTextIsWhatPathsAndQueriesSend() {
        assertEquals("a b", TemperaJson.Text("a b").plainText())
        assertEquals("25", TemperaJson.Int64(25).plainText())
        assertEquals("true", TemperaJson.Bool(true).plainText())
        assertEquals("false", TemperaJson.Bool(false).plainText())
        assertEquals("", TemperaJson.Null.plainText())
    }

    @Test
    fun kotlinValuesConvertToJson() {
        assertEquals(TemperaJson.Null, temperaJsonOf(null))
        assertEquals(TemperaJson.Int64(5), temperaJsonOf(5))
        assertEquals(TemperaJson.Int64(5), temperaJsonOf(5L))
        assertEquals(TemperaJson.Decimal(2.5), temperaJsonOf(2.5))
        assertEquals(TemperaJson.Bool(true), temperaJsonOf(true))
        assertEquals(TemperaJson.Text("x"), temperaJsonOf("x"))
        assertEquals("""[1,2]""", temperaJsonOf(listOf(1, 2)).serialized())
        assertEquals("""{"a":1}""", temperaJsonOf(mapOf("a" to 1)).serialized())
        // An already-built value passes through untouched.
        val built = temperaJsonObject("a" to 1)
        assertEquals(built, temperaJsonOf(built))
    }

    @Test
    fun percentEncodingMatchesTheUnreservedSet() {
        assertEquals("a-b_c.d~e", temperaPercentEncode("a-b_c.d~e"))
        assertEquals("a%20b%2Fc", temperaPercentEncode("a b/c"))
        assertEquals("%C3%A9", temperaPercentEncode("é"))
        assertEquals("a%3Ab", temperaPercentEncode("a:b"))
    }
}
