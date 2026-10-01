"""List one bound official SDK CHM directory as inert data; never decompress content.

Primary format implementation references (read as web text; not downloaded/executed):
https://raw.githubusercontent.com/kyz/libmspack/master/libmspack/mspack/chm.h
https://raw.githubusercontent.com/kyz/libmspack/master/libmspack/mspack/chmd.c
This is an independently written narrow parser based on field-layout observations.
These references are upstream implementation sources, not a Microsoft normative spec.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

BASE = Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution\schema_package_research_20260930_1228")
INPUT = BASE / "sdk_chm_data" / "VISSDK.CHM"
EXPECTED_BYTES = 6764354
EXPECTED_SHA = "19a74be23751db246fdf047d49a187187074113ad9095febd0cb640dba465a4a"
ATTEMPT = BASE / "chm_directory_attempt_v1"
MAX_NAME_BYTES = 4096
MAX_ENTRIES = 50000
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_ENCINT = (1 << 63) - 1
SOURCE_REFERENCES = [
    "https://raw.githubusercontent.com/kyz/libmspack/master/libmspack/mspack/chm.h",
    "https://raw.githubusercontent.com/kyz/libmspack/master/libmspack/mspack/chmd.c",
]
GUID_BYTES = bytes.fromhex(
    "10fd017caa7bd0119e0c00a0c922e6ec"
    "11fd017caa7bd0119e0c00a0c922e6ec"
)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write_new(path, value):
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    require(len(payload) <= MAX_REPORT_BYTES, "report byte limit")
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return {"path": str(path), "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()}


def read_exact(handle, offset, size, bound):
    require(type(offset) is int and type(size) is int, "integer read bounds")
    require(0 <= offset <= bound and 0 <= size <= bound - offset, "read outside EOF")
    handle.seek(offset)
    value = handle.read(size)
    require(len(value) == size, "short read")
    return value


def u32(data, offset):
    require(offset + 4 <= len(data), "u32 bounds")
    return struct.unpack_from("<I", data, offset)[0]


def u64(data, offset):
    require(offset + 8 <= len(data), "u64 bounds")
    return struct.unpack_from("<Q", data, offset)[0]


def encint(data, pos, end):
    """MSB-first seven-bit chunks with a continuation bit; maximum ten bytes."""
    value = 0
    for _ in range(10):
        require(pos < end, "encoded integer outside entry area")
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7f)
        require(value <= MAX_ENCINT, "encoded integer overflow")
        if not (byte & 0x80):
            return value, pos
    raise ValueError("unterminated encoded integer")


def parse_directory(handle, result):
    first = os.fstat(handle.fileno())
    require(first.st_size == EXPECTED_BYTES, "exact input size mismatch")
    digest = hashlib.sha256()
    remaining = EXPECTED_BYTES
    while remaining:
        block = handle.read(min(65536, remaining))
        require(bool(block), "EOF during input binding")
        digest.update(block)
        remaining -= len(block)
    require(not handle.read(1), "input exceeds expected EOF")
    actual_sha = digest.hexdigest()
    result["input_actual"] = {"path": str(INPUT), "bytes": first.st_size,
                              "sha256": actual_sha}
    require(actual_sha == EXPECTED_SHA, "exact input SHA mismatch")

    head = read_exact(handle, 0, 96, EXPECTED_BYTES)
    require(head[:4] == b"ITSF", "unknown ITSF signature")
    require(u32(head, 4) == 3 and u32(head, 8) == 96, "unsupported ITSF version/header")
    require(head[24:56] == GUID_BYTES, "unknown ITSF GUIDs")
    hs0_offset, hs0_length = u64(head, 56), u64(head, 64)
    directory_offset, directory_length = u64(head, 72), u64(head, 80)
    content_offset = u64(head, 88)
    result["itsf"] = {
        "version": u32(head, 4), "header_bytes": u32(head, 8),
        "unknown_12": u32(head, 12), "timestamp_raw": u32(head, 16),
        "language_id": u32(head, 20), "guid_bytes": head[24:56].hex(),
        "header_section0_offset": hs0_offset, "header_section0_bytes": hs0_length,
        "directory_offset": directory_offset, "directory_bytes": directory_length,
        "section0_content_offset": content_offset,
    }
    require(hs0_length == 24, "unsupported header section0 length")
    hs0 = read_exact(handle, hs0_offset, hs0_length, EXPECTED_BYTES)
    declared_length = u64(hs0, 8)
    result["itsf"]["declared_file_bytes"] = declared_length
    result["itsf"]["unparsed_trailing_bytes"] = EXPECTED_BYTES - declared_length
    require(96 <= declared_length <= EXPECTED_BYTES, "invalid declared file span")
    require(directory_length >= 84 and directory_offset >= 96, "directory span")
    require(directory_offset <= declared_length and
            directory_length <= declared_length - directory_offset, "directory outside declared EOF")
    require(directory_offset + directory_length <= content_offset <= declared_length,
            "section0 content offset bounds")

    itsp = read_exact(handle, directory_offset, 84, declared_length)
    require(itsp[:4] == b"ITSP" and u32(itsp, 4) == 1, "unknown ITSP signature/version")
    require(u32(itsp, 8) == 84, "unsupported ITSP header length")
    chunk_size, density, depth = u32(itsp, 16), u32(itsp, 20), u32(itsp, 24)
    index_root, first_pmgl, last_pmgl = u32(itsp, 28), u32(itsp, 32), u32(itsp, 36)
    chunk_count = u32(itsp, 44)
    result["itsp"] = {
        "version": u32(itsp, 4), "header_bytes": u32(itsp, 8),
        "chunk_bytes": chunk_size, "quickref_density": density, "index_depth": depth,
        "index_root": index_root, "first_pmgl": first_pmgl, "last_pmgl": last_pmgl,
        "chunk_count": chunk_count, "language_id": u32(itsp, 48),
        "remaining_header_hex": itsp[52:].hex(),
    }
    require(chunk_size == 4096, "unsupported directory chunk size")
    require(1 <= chunk_count <= EXPECTED_BYTES // chunk_size, "chunk count bound")
    require(1 <= depth <= 10, "unsupported directory index depth")
    require(index_root == 0xffffffff or index_root < chunk_count, "index root outside chunks")
    require(first_pmgl <= last_pmgl < chunk_count, "PMGL range outside chunks")
    require(directory_length == 84 + chunk_count * chunk_size, "unknown directory tail/layout")
    chunk_base = directory_offset + 84
    entries = result["members"]
    chunks = result["chunks"]
    pmgl_links = {}
    names = set()

    for chunk_index in range(chunk_count):
        absolute = chunk_base + chunk_index * chunk_size
        data = read_exact(handle, absolute, chunk_size, directory_offset + directory_length)
        signature = data[:4]
        require(signature in (b"PMGL", b"PMGI"), "unknown directory chunk signature")
        chunk_info = {"index": chunk_index, "offset": absolute,
                      "signature": signature.decode("ascii"), "bytes": chunk_size}
        chunks.append(chunk_info)
        if signature == b"PMGI":
            chunk_info["index_records_parsed"] = False
            continue
        free_area = u32(data, 4)
        previous, following = u32(data, 12), u32(data, 16)
        require(2 <= free_area <= chunk_size - 20, "PMGL quickref/free area bounds")
        end = chunk_size - free_area
        count = struct.unpack_from("<H", data, chunk_size - 2)[0]
        require(count <= MAX_ENTRIES - len(entries), "member count bound")
        chunk_info.update({"free_area_bytes": free_area, "entry_area_end": end,
                           "declared_entries": count, "previous": previous, "next": following})
        require(previous == 0xffffffff or previous < chunk_count, "PMGL previous bounds")
        require(following == 0xffffffff or following < chunk_count, "PMGL next bounds")
        pmgl_links[chunk_index] = (previous, following)
        pos = 20
        for entry_index in range(count):
            name_length, pos = encint(data, pos, end)
            require(0 < name_length <= MAX_NAME_BYTES and name_length <= end - pos,
                    "member name length/bounds")
            raw_name = data[pos:pos + name_length]
            pos += name_length
            name = raw_name.decode("utf-8", "strict")
            require("\x00" not in name and name not in names, "NUL or duplicate member name")
            section, pos = encint(data, pos, end)
            offset, pos = encint(data, pos, end)
            length, pos = encint(data, pos, end)
            require(section in (0, 1), "unsupported content section")
            if section == 0:
                require(offset <= declared_length - content_offset and
                        length <= declared_length - content_offset - offset,
                        "section0 member outside file")
            names.add(name)
            entries.append({
                "ordinal": len(entries), "chunk": chunk_index, "entry": entry_index,
                "name": name, "section": section, "section_offset": offset,
                "declared_length": length, "payload_read": False,
                "offset_scope": "uncompressed section-relative value; content not read",
            })
        require(pos == end, "unknown bytes in PMGL entry area")
        chunk_info["actual_entries"] = count
        chunk_info["actual_entry_end"] = pos

    require(first_pmgl in pmgl_links and last_pmgl in pmgl_links, "missing first/last PMGL")
    visited = set()
    current = first_pmgl
    previous = 0xffffffff
    while True:
        require(current in pmgl_links and current not in visited, "invalid/cyclic PMGL chain")
        visited.add(current)
        actual_previous, following = pmgl_links[current]
        require(actual_previous == previous, "inconsistent PMGL previous link")
        if current == last_pmgl:
            require(following == 0xffffffff, "last PMGL has a successor")
            break
        require(following != 0xffffffff, "PMGL chain ends before last")
        previous, current = current, following
    require(visited == set(pmgl_links), "PMGL chunks not covered by complete chain")
    if index_root != 0xffffffff:
        require(chunks[index_root]["signature"] == "PMGI", "index root is not PMGI")
    final = os.fstat(handle.fileno())
    require((first.st_size, first.st_mtime_ns) == (final.st_size, final.st_mtime_ns),
            "input metadata changed during read")
    result["directory_complete"] = True
    result["member_count"] = len(entries)
    result["pmgl_count"] = len(pmgl_links)
    result["pmgi_count"] = len(chunks) - len(pmgl_links)
    result["filename_candidates"] = [
        entry for entry in entries
        if entry["name"].lower().endswith(".xsd") or "schema" in entry["name"].lower()
    ]
    result["input_stability_scope"] = (
        "Exact initial SHA/size plus final fstat metadata; not a lock against arbitrary writers."
    )


def main():
    require(len(sys.argv) == 1, "This candidate accepts no input/output path overrides")
    require(not ATTEMPT.exists(), "Attempt directory already exists; do not replay")
    ATTEMPT.mkdir()
    write_new(ATTEMPT / "ENTRY.json", {
        "schema": "sdk-chm-directory-entry.v1", "utc": utc(), "pid": os.getpid(),
        "source": str(Path(__file__).resolve()),
        "expected_input": {"path": str(INPUT), "bytes": EXPECTED_BYTES, "sha256": EXPECTED_SHA},
        "scope": "Inert directory listing only; no member decompression/execution",
    })
    result = {
        "schema": "sdk-chm-inert-directory-candidate.v1", "started_utc": utc(),
        "source_references": SOURCE_REFERENCES,
        "source_authority": "Primary upstream implementation, not Microsoft normative schema",
        "members": [], "chunks": [], "directory_complete": False,
        "PMGI_index_contents_validated": False, "payload_read_or_decompressed": False,
        "LZX_decoder_used": False, "schema_validation": False,
        "installer_execution": False, "Office_COM": False, "scientific_execution": False,
    }
    try:
        with INPUT.open("rb") as handle:
            parse_directory(handle, result)
        result["completed_utc"] = utc()
        result["result"] = "directory_listing_candidate"
        descriptor = write_new(ATTEMPT / "SDK_CHM_DIRECTORY_CANDIDATE.json", result)
        print(json.dumps(descriptor))
        return 0
    except Exception as error:
        result["completed_utc"] = utc()
        result["result"] = "failed_partial_directory_candidate"
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        descriptor = write_new(ATTEMPT / "SDK_CHM_DIRECTORY_FAILURE.json", result)
        print(json.dumps(descriptor), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

