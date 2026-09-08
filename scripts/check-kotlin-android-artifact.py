#!/usr/bin/env python3
"""Fail-closed structural inspection for the Android Kotlin SDK AAR.

This is intentionally not a full bytecode or Android API verifier. It checks
selected class entries and constant-pool references; R8 and API-26 device lanes
prove the remaining runtime facts.
"""
import argparse
import io
import struct
import sys
import zipfile

MAX_AAR = 50 * 1024 * 1024
MAX_ENTRIES = 10_000
MAX_CLASSES_JAR = 25 * 1024 * 1024
MAX_CLASS = 5 * 1024 * 1024
MAX_TOTAL_CLASS_BYTES = 20 * 1024 * 1024
REQUIRED = {
    "dev/tempera/sdk/TemperaClient.class",
    "dev/tempera/sdk/TemperaAuth.class",
    "dev/tempera/sdk/TemperaMcpClient.class",
    "dev/tempera/sdk/TemperaJson.class",
    "dev/tempera/sdk/AndroidDefaultTransportKt.class",
    "dev/tempera/sdk/OkHttpTemperaTransport.class",
}
FORBIDDEN_CLASSES = {
    "dev/tempera/sdk/JdkHttpTransport.class",
    "dev/tempera/sdk/JvmDefaultTransportKt.class",
}

def fail(message):
    raise ValueError(message)

def bounded_zip(data, label):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        fail(f"malformed {label}: {exc}")
    infos = archive.infolist()
    if len(infos) > MAX_ENTRIES:
        fail(f"too many {label} entries")
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        fail(f"duplicate {label} entries")
    return archive, infos

def bounded_read(archive, info, limit, label):
    if info.file_size > limit:
        fail(f"{label} exceeds size bound")
    with archive.open(info) as entry:
        value = entry.read(limit + 1)
    if len(value) > limit:
        fail(f"{label} exceeds size bound")
    return value

def read_exact(data, offset, size):
    if offset + size > len(data):
        fail("truncated class file")
    return data[offset:offset + size], offset + size

def parse_utf8_constants(data):
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        fail("missing CAFEBABE class header")
    count = struct.unpack(">H", data[8:10])[0]
    if count == 0:
        fail("invalid constant pool count")
    offset, index, utf8 = 10, 1, []
    fixed = {3: 4, 4: 4, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4, 12: 4, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
    while index < count:
        tag, offset = read_exact(data, offset, 1)
        tag = tag[0]
        if tag == 1:
            size, offset = read_exact(data, offset, 2)
            size = struct.unpack(">H", size)[0]
            payload, offset = read_exact(data, offset, size)
            utf8.append(payload.decode("utf-8", "surrogateescape"))
        elif tag in (5, 6):
            _, offset = read_exact(data, offset, 8)
            index += 1
        elif tag == 15:
            _, offset = read_exact(data, offset, 3)
        elif tag in fixed:
            _, offset = read_exact(data, offset, fixed[tag])
        else:
            fail(f"unknown constant pool tag {tag}")
        index += 1
    if index != count:
        fail("invalid long/double constant pool slot")
    return utf8

def inspect(path):
    if path.stat().st_size > MAX_AAR:
        fail("AAR exceeds size bound")
    with path.open("rb") as source:
        raw = source.read(MAX_AAR + 1)
    if len(raw) > MAX_AAR:
        fail("AAR exceeds size bound")
    aar, infos = bounded_zip(raw, "AAR")
    by_name = {item.filename: item for item in infos}
    if "classes.jar" not in by_name:
        fail("AAR is missing classes.jar")
    embedded_jars = [name for name in by_name if name.startswith("libs/") and name.endswith(".jar")]
    if embedded_jars:
        fail("embedded jars are not permitted: " + ", ".join(sorted(embedded_jars)))
    classes = bounded_read(aar, by_name["classes.jar"], MAX_CLASSES_JAR, "classes.jar")
    jar, infos = bounded_zip(classes, "classes.jar")
    classes_by_name = {item.filename: item for item in infos}
    missing = REQUIRED - classes_by_name.keys()
    if missing:
        fail("missing required classes: " + ", ".join(sorted(missing)))
    present_forbidden = FORBIDDEN_CLASSES & classes_by_name.keys()
    if present_forbidden:
        fail("forbidden JVM transport classes: " + ", ".join(sorted(present_forbidden)))
    class_bytes = 0
    for name, info in classes_by_name.items():
        if not name.endswith(".class"):
            continue
        class_bytes += info.file_size
        if class_bytes > MAX_TOTAL_CLASS_BYTES:
            fail("aggregate class bytes exceed size bound")
        constants = parse_utf8_constants(bounded_read(jar, info, MAX_CLASS, f"class {name}"))
        if any("java/net/http/" in value for value in constants):
            fail(f"JVM HTTP reference in {name}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aar", required=True, type=lambda value: __import__("pathlib").Path(value))
    parser.add_argument("--min-sdk", required=True, type=int)
    args = parser.parse_args()
    inspect(args.aar)
    print(f"constant-pool structural check passed for {args.aar} (API {args.min_sdk} runtime and bytecode verification remain CI-only)")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"artifact check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
