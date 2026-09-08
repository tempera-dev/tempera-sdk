// A minimal, order-preserving JSON model.
//
// The package has no external dependencies -- the JDK ships no JSON API -- and
// the wire contract needs more than a generic one anyway: request bodies must
// serialize their members in the order the surface tables declare them (so one
// request is one reproducible byte string, retried verbatim), and error bodies
// must be read without losing member order or number precision. This file is
// the Kotlin counterpart of the private scanner in
// `packages/rust/src/error.rs`.

package dev.tempera.sdk

/** One member of a JSON object, in declaration order. */
public data class TemperaJsonMember(
    public val key: String,
    public val value: TemperaJson,
)

/**
 * A JSON value. Objects keep their members in order, so a body built from the
 * surface tables serializes the same way every time.
 */
public sealed class TemperaJson {
    /** JSON `null`. */
    public object Null : TemperaJson()

    /** JSON `true` / `false`. */
    public data class Bool(public val value: Boolean) : TemperaJson()

    /** A JSON number with no fractional or exponent part. */
    public data class Int64(public val value: Long) : TemperaJson()

    /** A JSON number with a fractional or exponent part. */
    public data class Decimal(public val value: Double) : TemperaJson()

    /** A JSON string. */
    public data class Text(public val value: String) : TemperaJson()

    /** A JSON array. */
    public data class Arr(public val values: List<TemperaJson>) : TemperaJson()

    /** A JSON object, in member order. */
    public data class Obj(public val members: List<TemperaJsonMember>) : TemperaJson()

    /** The value of one object member, or `null` for a non-object or a missing key. */
    public operator fun get(key: String): TemperaJson? =
        if (this is Obj) members.firstOrNull { it.key == key }?.value else null

    /** The string payload, when this is a string. */
    public fun asString(): String? = if (this is Text) value else null

    /** The integer payload, when this is a number that is exactly an integer. */
    public fun asLong(): Long? =
        when (this) {
            is Int64 -> value
            is Decimal ->
                if (value.isFinite() && value == Math.floor(value)) value.toLong() else null
            else -> null
        }

    /** The integer payload as an `Int`. */
    public fun asInt(): Int? = asLong()?.toInt()

    /** The boolean payload, when this is a boolean. */
    public fun asBoolean(): Boolean? = if (this is Bool) value else null

    /** The elements, when this is an array. */
    public fun asArray(): List<TemperaJson>? = if (this is Arr) values else null

    /** The members, when this is an object. */
    public fun asObject(): List<TemperaJsonMember>? = if (this is Obj) members else null

    /** Whether this is JSON `null`. */
    public fun isNull(): Boolean = this === Null

    /**
     * The plain-text form used for path substitution and query-string values.
     *
     * Strings are used as-is; numbers and booleans take their JSON spelling,
     * which is what the TypeScript and Python clients send.
     */
    public fun plainText(): String =
        when (this) {
            is Null -> ""
            is Bool -> if (value) "true" else "false"
            is Int64 -> value.toString()
            is Decimal -> numberText(value)
            is Text -> value
            is Arr, is Obj -> serialized()
        }

    /** Serialize compactly, with no insignificant whitespace, in member order. */
    public fun serialized(): String {
        val out = StringBuilder()
        writeTo(out)
        return out.toString()
    }

    /** UTF-8 bytes of the compact serialization. */
    public fun serializedBytes(): ByteArray = serialized().toByteArray(Charsets.UTF_8)

    private fun writeTo(out: StringBuilder) {
        when (this) {
            is Null -> out.append("null")
            is Bool -> out.append(if (value) "true" else "false")
            is Int64 -> out.append(value.toString())
            is Decimal -> out.append(numberText(value))
            is Text -> {
                out.append('"')
                escapeInto(value, out)
                out.append('"')
            }
            is Arr -> {
                out.append('[')
                for ((index, element) in values.withIndex()) {
                    if (index > 0) out.append(',')
                    element.writeTo(out)
                }
                out.append(']')
            }
            is Obj -> {
                out.append('{')
                for ((index, member) in members.withIndex()) {
                    if (index > 0) out.append(',')
                    out.append('"')
                    escapeInto(member.key, out)
                    out.append("\":")
                    member.value.writeTo(out)
                }
                out.append('}')
            }
        }
    }

    public companion object {
        /**
         * Escape one string for a JSON string literal, without the surrounding
         * quotes. Non-ASCII characters are emitted verbatim as UTF-8, matching
         * the compact `ensure_ascii=False` encoder in the Python package.
         */
        public fun escape(value: String): String {
            val out = StringBuilder(value.length)
            escapeInto(value, out)
            return out.toString()
        }

        /**
         * Parse a complete JSON document, or `null` on any syntax error or
         * trailing garbage -- which callers treat as "unparseable body".
         */
        public fun parse(input: String): TemperaJson? {
            val scanner = TemperaJsonScanner(input)
            scanner.skipWhitespace()
            val value = scanner.parseValue() ?: return null
            scanner.skipWhitespace()
            return if (scanner.isAtEnd()) value else null
        }

        /** Parse UTF-8 bytes; `null` when they are not valid JSON. */
        public fun parse(input: ByteArray): TemperaJson? =
            if (input.isEmpty()) null else parse(String(input, Charsets.UTF_8))
    }
}

internal fun escapeInto(value: String, out: StringBuilder) {
    for (character in value) {
        when (character) {
            '"' -> out.append("\\\"")
            '\\' -> out.append("\\\\")
            '\n' -> out.append("\\n")
            '\r' -> out.append("\\r")
            '\t' -> out.append("\\t")
            else ->
                if (character.code < 0x20) {
                    out.append(String.format("\\u%04x", character.code))
                } else {
                    out.append(character)
                }
        }
    }
}

internal fun numberText(value: Double): String {
    if (!value.isFinite()) return "null"
    if (value == Math.floor(value) && Math.abs(value) < 1e15) {
        return value.toLong().toString()
    }
    return value.toString()
}

/**
 * Convert a Kotlin value into JSON: `null`, `Boolean`, any integral or
 * floating-point `Number`, `CharSequence`, `Map`, `Iterable`, `Array`, or an
 * already-built [TemperaJson]. Anything else takes its `toString()`.
 */
public fun temperaJsonOf(value: Any?): TemperaJson =
    when (value) {
        null -> TemperaJson.Null
        is TemperaJson -> value
        is Boolean -> TemperaJson.Bool(value)
        is Byte, is Short, is Int, is Long -> TemperaJson.Int64((value as Number).toLong())
        is Float, is Double -> TemperaJson.Decimal((value as Number).toDouble())
        is CharSequence -> TemperaJson.Text(value.toString())
        is Map<*, *> ->
            TemperaJson.Obj(
                value.entries.map { TemperaJsonMember(it.key.toString(), temperaJsonOf(it.value)) }
            )
        is Iterable<*> -> TemperaJson.Arr(value.map { temperaJsonOf(it) })
        is Array<*> -> TemperaJson.Arr(value.map { temperaJsonOf(it) })
        else -> TemperaJson.Text(value.toString())
    }

/** Build a JSON object from ordered pairs. */
public fun temperaJsonObject(vararg members: Pair<String, Any?>): TemperaJson =
    TemperaJson.Obj(members.map { TemperaJsonMember(it.first, temperaJsonOf(it.second)) })

/** A recursive-descent JSON scanner. */
internal class TemperaJsonScanner(private val source: String) {
    private var position = 0

    fun isAtEnd(): Boolean = position >= source.length

    private fun peek(): Char? = if (position < source.length) source[position] else null

    private fun bump(): Char? {
        val character = peek() ?: return null
        position += 1
        return character
    }

    fun skipWhitespace() {
        while (true) {
            val character = peek() ?: return
            if (character == ' ' || character == '\t' || character == '\n' || character == '\r') {
                position += 1
            } else {
                return
            }
        }
    }

    private fun eat(token: String): Boolean {
        if (source.startsWith(token, position)) {
            position += token.length
            return true
        }
        return false
    }

    fun parseValue(): TemperaJson? {
        val character = peek() ?: return null
        return when {
            character == '{' -> parseObject()
            character == '[' -> parseArray()
            character == '"' -> parseString()?.let { TemperaJson.Text(it) }
            character == 't' -> if (eat("true")) TemperaJson.Bool(true) else null
            character == 'f' -> if (eat("false")) TemperaJson.Bool(false) else null
            character == 'n' -> if (eat("null")) TemperaJson.Null else null
            character == '-' || (character in '0'..'9') -> parseNumber()
            else -> null
        }
    }

    private fun parseObject(): TemperaJson? {
        bump() // consume '{'
        val members = ArrayList<TemperaJsonMember>()
        skipWhitespace()
        if (peek() == '}') {
            bump()
            return TemperaJson.Obj(members)
        }
        while (true) {
            skipWhitespace()
            if (peek() != '"') return null
            val key = parseString() ?: return null
            skipWhitespace()
            if (bump() != ':') return null
            skipWhitespace()
            val value = parseValue() ?: return null
            members.add(TemperaJsonMember(key, value))
            skipWhitespace()
            when (bump()) {
                ',' -> continue
                '}' -> return TemperaJson.Obj(members)
                else -> return null
            }
        }
    }

    private fun parseArray(): TemperaJson? {
        bump() // consume '['
        val values = ArrayList<TemperaJson>()
        skipWhitespace()
        if (peek() == ']') {
            bump()
            return TemperaJson.Arr(values)
        }
        while (true) {
            skipWhitespace()
            val value = parseValue() ?: return null
            values.add(value)
            skipWhitespace()
            when (bump()) {
                ',' -> continue
                ']' -> return TemperaJson.Arr(values)
                else -> return null
            }
        }
    }

    private fun parseString(): String? {
        bump() // consume the opening quote
        val out = StringBuilder()
        while (true) {
            val character = bump() ?: return null
            if (character == '"') return out.toString()
            if (character.code < 0x20) return null // raw control character
            if (character != '\\') {
                out.append(character)
                continue
            }
            when (bump()) {
                '"' -> out.append('"')
                '\\' -> out.append('\\')
                '/' -> out.append('/')
                'b' -> out.append('\b')
                'f' -> out.append('\u000C')
                'n' -> out.append('\n')
                'r' -> out.append('\r')
                't' -> out.append('\t')
                'u' -> {
                    val unit = parseHex4() ?: return null
                    if (unit in 0xD800..0xDBFF) {
                        // High surrogate: a \uXXXX low surrogate must follow.
                        if (bump() != '\\' || bump() != 'u') return null
                        val low = parseHex4() ?: return null
                        if (low !in 0xDC00..0xDFFF) return null
                        out.append(Char(unit))
                        out.append(Char(low))
                    } else if (unit in 0xDC00..0xDFFF) {
                        return null // a lone low surrogate
                    } else {
                        out.append(Char(unit))
                    }
                }
                else -> return null
            }
        }
    }

    private fun parseHex4(): Int? {
        var value = 0
        for (index in 0 until 4) {
            val character = bump() ?: return null
            val digit = Character.digit(character, 16)
            if (digit < 0) return null
            value = (value shl 4) or digit
        }
        return value
    }

    private fun parseNumber(): TemperaJson? {
        val start = position
        var isInteger = true
        if (peek() == '-') position += 1
        if (!eatDigits()) return null
        if (peek() == '.') {
            isInteger = false
            position += 1
            if (!eatDigits()) return null
        }
        val exponent = peek()
        if (exponent == 'e' || exponent == 'E') {
            isInteger = false
            position += 1
            val sign = peek()
            if (sign == '+' || sign == '-') position += 1
            if (!eatDigits()) return null
        }
        val raw = source.substring(start, position)
        if (isInteger) {
            val parsed = raw.toLongOrNull()
            if (parsed != null) return TemperaJson.Int64(parsed)
        }
        val parsed = raw.toDoubleOrNull() ?: return null
        return TemperaJson.Decimal(parsed)
    }

    private fun eatDigits(): Boolean {
        val start = position
        while (true) {
            val character = peek() ?: break
            if (character in '0'..'9') position += 1 else break
        }
        return position > start
    }
}
