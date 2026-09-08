// A minimal, order-preserving JSON model.
//
// The package has no external dependencies, and `JSONSerialization` cannot
// express what the wire contract needs: request bodies must serialize their
// members in the order the surface tables declare them (so one request is one
// reproducible byte string, retried verbatim), and error bodies must be read
// without losing member order or number precision. This file is the Swift
// counterpart of the private scanner in `packages/rust/src/error.rs`.

import Foundation

/// One member of a JSON object, in declaration order.
public struct TemperaJSONMember: Sendable, Equatable {
    /// The member's key.
    public let key: String
    /// The member's value.
    public let value: TemperaJSON

    /// Create one member.
    public init(_ key: String, _ value: TemperaJSON) {
        self.key = key
        self.value = value
    }
}

/// A JSON value. Objects keep their members in order, so a body built from the
/// surface tables serializes the same way every time.
public enum TemperaJSON: Sendable, Equatable {
    /// JSON `null`.
    case null
    /// JSON `true` / `false`.
    case bool(Bool)
    /// A JSON number with no fractional or exponent part.
    case int(Int)
    /// A JSON number with a fractional or exponent part.
    case double(Double)
    /// A JSON string.
    case string(String)
    /// A JSON array.
    case array([TemperaJSON])
    /// A JSON object, in member order.
    case object([TemperaJSONMember])
}

// TemperaJSON deliberately does NOT conform to ExpressibleByNilLiteral: it
// would make a bare `nil` in any TemperaJSON context mean `.null`, which
// silently turns `optional ?? nil` and `condition ? value : nil` into a
// non-optional `.null`. Write `.null` where JSON null is meant.

extension TemperaJSON: ExpressibleByBooleanLiteral {
    public init(booleanLiteral value: Bool) { self = .bool(value) }
}

extension TemperaJSON: ExpressibleByIntegerLiteral {
    public init(integerLiteral value: Int) { self = .int(value) }
}

extension TemperaJSON: ExpressibleByFloatLiteral {
    public init(floatLiteral value: Double) { self = .double(value) }
}

extension TemperaJSON: ExpressibleByStringLiteral {
    public init(stringLiteral value: String) { self = .string(value) }
}

extension TemperaJSON: ExpressibleByArrayLiteral {
    public init(arrayLiteral elements: TemperaJSON...) { self = .array(elements) }
}

extension TemperaJSON: ExpressibleByDictionaryLiteral {
    public init(dictionaryLiteral elements: (String, TemperaJSON)...) {
        self = .object(elements.map { TemperaJSONMember($0.0, $0.1) })
    }
}

extension TemperaJSON {
    /// The value of one object member, or `nil` for a non-object or a missing key.
    public subscript(key: String) -> TemperaJSON? {
        guard case let .object(members) = self else { return nil }
        return members.first { $0.key == key }?.value
    }

    /// The string payload, when this is a string.
    public var stringValue: String? {
        guard case let .string(value) = self else { return nil }
        return value
    }

    /// The integer payload, when this is a number that is exactly an integer.
    public var intValue: Int? {
        switch self {
        case let .int(value): return value
        case let .double(value) where value.rounded() == value && value.isFinite: return Int(value)
        default: return nil
        }
    }

    /// The boolean payload, when this is a boolean.
    public var boolValue: Bool? {
        guard case let .bool(value) = self else { return nil }
        return value
    }

    /// The elements, when this is an array.
    public var arrayValue: [TemperaJSON]? {
        guard case let .array(values) = self else { return nil }
        return values
    }

    /// The members, when this is an object.
    public var objectValue: [TemperaJSONMember]? {
        guard case let .object(members) = self else { return nil }
        return members
    }

    /// Whether this is JSON `null`.
    public var isNull: Bool {
        if case .null = self { return true }
        return false
    }

    /// The plain-text form used for path substitution and query-string values.
    ///
    /// Strings are used as-is; numbers and booleans take their JSON spelling,
    /// which is what the TypeScript and Python clients send.
    public var plainText: String {
        switch self {
        case .null: return ""
        case let .bool(value): return value ? "true" : "false"
        case let .int(value): return String(value)
        case let .double(value): return TemperaJSON.numberText(value)
        case let .string(value): return value
        case .array, .object: return serialized()
        }
    }

    static func numberText(_ value: Double) -> String {
        guard value.isFinite else { return "null" }
        if value.rounded() == value, abs(value) < 1e15 {
            return String(Int64(value))
        }
        return String(value)
    }

    /// Escape one string for inclusion in a JSON string literal, without the
    /// surrounding quotes. Non-ASCII characters are emitted verbatim as UTF-8,
    /// matching the compact `ensure_ascii=False` encoder in the Python package.
    public static func escape(_ value: String) -> String {
        var out = String()
        out.reserveCapacity(value.count)
        for character in value.unicodeScalars {
            switch character {
            case "\"": out += "\\\""
            case "\\": out += "\\\\"
            case "\n": out += "\\n"
            case "\r": out += "\\r"
            case "\t": out += "\\t"
            default:
                if character.value < 0x20 {
                    out += String(format: "\\u%04x", character.value)
                } else {
                    out.unicodeScalars.append(character)
                }
            }
        }
        return out
    }

    /// Serialize compactly, with no insignificant whitespace and members in
    /// declaration order.
    public func serialized() -> String {
        switch self {
        case .null:
            return "null"
        case let .bool(value):
            return value ? "true" : "false"
        case let .int(value):
            return String(value)
        case let .double(value):
            return TemperaJSON.numberText(value)
        case let .string(value):
            return "\"\(TemperaJSON.escape(value))\""
        case let .array(values):
            return "[" + values.map { $0.serialized() }.joined(separator: ",") + "]"
        case let .object(members):
            let inner = members
                .map { "\"\(TemperaJSON.escape($0.key))\":\($0.value.serialized())" }
                .joined(separator: ",")
            return "{\(inner)}"
        }
    }

    /// UTF-8 bytes of the compact serialization.
    public func serializedData() -> Data {
        Data(serialized().utf8)
    }

    /// Parse a complete JSON document, or `nil` on any syntax error or trailing
    /// garbage -- which callers treat as "unparseable body".
    public static func parse(_ input: String) -> TemperaJSON? {
        var scanner = TemperaJSONScanner(Array(input.unicodeScalars))
        scanner.skipWhitespace()
        guard let value = scanner.parseValue() else { return nil }
        scanner.skipWhitespace()
        return scanner.isAtEnd ? value : nil
    }

    /// Parse UTF-8 bytes; `nil` when they are not valid UTF-8 or not valid JSON.
    public static func parse(_ data: Data) -> TemperaJSON? {
        guard let text = String(data: data, encoding: .utf8) else { return nil }
        return parse(text)
    }
}

/// A recursive-descent JSON scanner over Unicode scalars.
struct TemperaJSONScanner {
    private let scalars: [Unicode.Scalar]
    private var position = 0

    init(_ scalars: [Unicode.Scalar]) {
        self.scalars = scalars
    }

    var isAtEnd: Bool { position >= scalars.count }

    private func peek() -> Unicode.Scalar? {
        position < scalars.count ? scalars[position] : nil
    }

    private mutating func bump() -> Unicode.Scalar? {
        guard let scalar = peek() else { return nil }
        position += 1
        return scalar
    }

    mutating func skipWhitespace() {
        while let scalar = peek(), scalar == " " || scalar == "\t" || scalar == "\n" || scalar == "\r" {
            position += 1
        }
    }

    private mutating func eat(_ token: String) -> Bool {
        let expected = Array(token.unicodeScalars)
        guard position + expected.count <= scalars.count else { return false }
        for (offset, scalar) in expected.enumerated() where scalars[position + offset] != scalar {
            return false
        }
        position += expected.count
        return true
    }

    mutating func parseValue() -> TemperaJSON? {
        guard let scalar = peek() else { return nil }
        switch scalar {
        case "{": return parseObject()
        case "[": return parseArray()
        case "\"": return parseString().map { TemperaJSON.string($0) }
        case "t": return eat("true") ? .bool(true) : nil
        case "f": return eat("false") ? .bool(false) : nil
        case "n": return eat("null") ? .null : nil
        default:
            if scalar == "-" || (scalar.value >= 0x30 && scalar.value <= 0x39) { return parseNumber() }
            return nil
        }
    }

    private mutating func parseObject() -> TemperaJSON? {
        _ = bump()  // consume '{'
        var members: [TemperaJSONMember] = []
        skipWhitespace()
        if peek() == "}" {
            _ = bump()
            return .object(members)
        }
        while true {
            skipWhitespace()
            guard peek() == "\"", let key = parseString() else { return nil }
            skipWhitespace()
            guard bump() == ":" else { return nil }
            skipWhitespace()
            guard let value = parseValue() else { return nil }
            members.append(TemperaJSONMember(key, value))
            skipWhitespace()
            switch bump() {
            case ",": continue
            case "}": return .object(members)
            default: return nil
            }
        }
    }

    private mutating func parseArray() -> TemperaJSON? {
        _ = bump()  // consume '['
        var values: [TemperaJSON] = []
        skipWhitespace()
        if peek() == "]" {
            _ = bump()
            return .array(values)
        }
        while true {
            skipWhitespace()
            guard let value = parseValue() else { return nil }
            values.append(value)
            skipWhitespace()
            switch bump() {
            case ",": continue
            case "]": return .array(values)
            default: return nil
            }
        }
    }

    private mutating func parseString() -> String? {
        _ = bump()  // consume the opening quote
        var out = String.UnicodeScalarView()
        while true {
            guard let scalar = bump() else { return nil }
            if scalar == "\"" { return String(out) }
            if scalar.value < 0x20 { return nil }  // raw control character
            guard scalar == "\\" else {
                out.append(scalar)
                continue
            }
            guard let escape = bump() else { return nil }
            switch escape {
            case "\"": out.append("\"")
            case "\\": out.append("\\")
            case "/": out.append("/")
            case "b": out.append(Unicode.Scalar(UInt8(0x08)))
            case "f": out.append(Unicode.Scalar(UInt8(0x0C)))
            case "n": out.append("\n")
            case "r": out.append("\r")
            case "t": out.append("\t")
            case "u":
                guard let unit = parseHex4() else { return nil }
                if unit >= 0xD800, unit < 0xDC00 {
                    // High surrogate: a \uXXXX low surrogate must follow.
                    guard bump() == "\\", bump() == "u", let low = parseHex4(),
                        low >= 0xDC00, low < 0xE000
                    else { return nil }
                    let combined =
                        0x10000 + ((UInt32(unit) - 0xD800) << 10) + (UInt32(low) - 0xDC00)
                    guard let scalar = Unicode.Scalar(combined) else { return nil }
                    out.append(scalar)
                } else {
                    guard let scalar = Unicode.Scalar(UInt32(unit)) else { return nil }
                    out.append(scalar)
                }
            default:
                return nil
            }
        }
    }

    private mutating func parseHex4() -> UInt16? {
        var value: UInt16 = 0
        for _ in 0..<4 {
            guard let scalar = bump(), let digit = hexDigit(scalar) else { return nil }
            value = (value << 4) | UInt16(digit)
        }
        return value
    }

    private func hexDigit(_ scalar: Unicode.Scalar) -> UInt8? {
        switch scalar {
        case "0"..."9": return UInt8(scalar.value - 0x30)
        case "a"..."f": return UInt8(scalar.value - 0x61 + 10)
        case "A"..."F": return UInt8(scalar.value - 0x41 + 10)
        default: return nil
        }
    }

    private mutating func parseNumber() -> TemperaJSON? {
        let start = position
        var isInteger = true
        if peek() == "-" { position += 1 }
        guard eatDigits() else { return nil }
        if peek() == "." {
            isInteger = false
            position += 1
            guard eatDigits() else { return nil }
        }
        if let scalar = peek(), scalar == "e" || scalar == "E" {
            isInteger = false
            position += 1
            if let sign = peek(), sign == "+" || sign == "-" { position += 1 }
            guard eatDigits() else { return nil }
        }
        let raw = String(String.UnicodeScalarView(scalars[start..<position]))
        if isInteger, let value = Int(raw) { return .int(value) }
        guard let value = Double(raw) else { return nil }
        return .double(value)
    }

    private mutating func eatDigits() -> Bool {
        let start = position
        while let scalar = peek(), scalar.value >= 0x30, scalar.value <= 0x39 {
            position += 1
        }
        return position > start
    }
}
