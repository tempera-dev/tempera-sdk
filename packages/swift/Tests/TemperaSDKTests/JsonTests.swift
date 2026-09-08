import Foundation
import XCTest

@testable import TemperaSDK

final class JsonTests: XCTestCase {
    func testObjectsKeepTheirMemberOrderThroughParseAndSerialize() {
        let source = #"{"b":1,"a":2,"c":{"z":[1,2,3],"y":null}}"#
        let parsed = TemperaJSON.parse(source)
        XCTAssertEqual(parsed?.serialized(), source)
        XCTAssertEqual(parsed?.objectValue?.map(\.key), ["b", "a", "c"])
    }

    func testSerializationIsCompactAndUtf8() {
        let value: TemperaJSON = ["name": "organization’s", "emoji": "🚀"]
        XCTAssertEqual(value.serialized(), #"{"name":"organization’s","emoji":"🚀"}"#)
        XCTAssertEqual(value.serializedData(), Data(value.serialized().utf8))
    }

    func testControlCharactersAndQuotesAreEscaped() {
        let value = TemperaJSON.string("quote \" slash \\ tab \t newline \n bell \u{7}")
        XCTAssertEqual(
            value.serialized(),
            "\"quote \\\" slash \\\\ tab \\t newline \\n bell \\u0007\""
        )
        XCTAssertEqual(TemperaJSON.parse(value.serialized()), value)
    }

    func testNumbersRoundTripWithoutBecomingFloats() {
        XCTAssertEqual(TemperaJSON.parse("[0,-1,2.5,1e3]"), [0, -1, 2.5, 1000.0])
        XCTAssertEqual(TemperaJSON.parse("42"), .int(42))
        XCTAssertEqual(TemperaJSON.int(42).serialized(), "42")
        XCTAssertEqual(TemperaJSON.double(2.5).serialized(), "2.5")
        XCTAssertEqual(TemperaJSON.double(3.0).serialized(), "3")
        XCTAssertEqual(TemperaJSON.double(.nan).serialized(), "null")
    }

    func testUnicodeEscapesAndSurrogatePairsDecode() {
        XCTAssertEqual(TemperaJSON.parse(#""emoji 😀 done""#), .string("emoji 😀 done"))
        XCTAssertEqual(TemperaJSON.parse(#""é""#), .string("é"))
        XCTAssertEqual(TemperaJSON.parse(#""slash \/ ok""#), .string("slash / ok"))
        // A lone high surrogate is not decodable.
        XCTAssertNil(TemperaJSON.parse(#""\uD83D""#))
    }

    func testMalformedDocumentsAreRejected() {
        // Leading zeros are accepted, exactly as the Rust scanner accepts them:
        // both read producer responses, never caller input.
        for bad in [
            "", "   ", "{", #"{"a":1} extra"#, #"{"a":"line"# + "\n" + #"break"}"#, "[1,]",
            "{'a':1}", "tru",
        ] {
            XCTAssertNil(TemperaJSON.parse(bad), bad)
        }
    }

    func testAccessorsReadTheExpectedShapes() {
        let value: TemperaJSON = ["s": "x", "i": 7, "b": true, "n": .null, "a": [1, 2]]
        XCTAssertEqual(value["s"]?.stringValue, "x")
        XCTAssertEqual(value["i"]?.intValue, 7)
        XCTAssertEqual(value["b"]?.boolValue, true)
        XCTAssertEqual(value["n"]?.isNull, true)
        XCTAssertEqual(value["a"]?.arrayValue?.count, 2)
        XCTAssertNil(value["missing"])
        XCTAssertNil(TemperaJSON.string("x")["key"])
    }

    func testPlainTextIsWhatPathsAndQueriesSend() {
        XCTAssertEqual(TemperaJSON.string("a b").plainText, "a b")
        XCTAssertEqual(TemperaJSON.int(25).plainText, "25")
        XCTAssertEqual(TemperaJSON.bool(true).plainText, "true")
        XCTAssertEqual(TemperaJSON.bool(false).plainText, "false")
        XCTAssertEqual(TemperaJSON.null.plainText, "")
    }

    func testParamsPreserveInsertionOrderAndReplaceInPlace() {
        var params: TemperaParams = ["b": 1, "a": 2]
        XCTAssertEqual(params.keys, ["b", "a"])
        params.set("b", 3)
        XCTAssertEqual(params.keys, ["b", "a"])
        XCTAssertEqual(params["b"], .int(3))
        params["c"] = "new"
        XCTAssertEqual(params.keys, ["b", "a", "c"])
        params["a"] = nil
        XCTAssertEqual(params.keys, ["b", "c"])
        XCTAssertTrue(params.contains("b"))
        XCTAssertFalse(params.contains("a"))
    }

    func testPercentEncodingMatchesTheUnreservedSet() {
        XCTAssertEqual(temperaPercentEncode("a-b_c.d~e"), "a-b_c.d~e")
        XCTAssertEqual(temperaPercentEncode("a b/c"), "a%20b%2Fc")
        XCTAssertEqual(temperaPercentEncode("é"), "%C3%A9")
        XCTAssertEqual(temperaPercentEncode("a:b"), "a%3Ab")
    }
}
