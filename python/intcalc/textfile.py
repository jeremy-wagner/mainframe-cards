"""Newline-delimited ASCII exports of the interest-batch files.

``app/data/ASCII`` stores one copybook record per line. Category, disclosure,
and account lines are the full copybook length. The card cross-reference
export drops the trailing spaces of ``FILLER PIC X(14)`` (CVACT03Y.cpy line 8),
so those lines are 36 bytes. A short line is read as space-padded out to the
copybook length. ``reserialize`` writes the original line width and the
original line ending back, so the file bytes do not change.

A line longer than the copybook, or a numeric field that is not numeric, is
rejected. The error does not include the line.
"""

from __future__ import annotations

from typing import List, Tuple, Type, TypeVar

from intcalc.records import FixedRecord, RecordFormatError

T = TypeVar("T", bound=FixedRecord)


def read_records(data: bytes, record_type: Type[T]) -> List[T]:
    """Parse every line of an ASCII export into copybook records."""

    records = []
    for payload, _ending in _split_lines(data):
        records.append(record_type.from_bytes(_pad(payload, record_type)))
    return records


def reserialize(data: bytes, record_type: Type[T]) -> bytes:
    """Parse ``data`` and emit the same bytes.

    The encoded copybook record must match the line once a short line has
    been space-padded. The bytes written are the original payload and ending.
    """

    if not isinstance(data, bytes):
        raise RecordFormatError("file must be bytes")

    out = bytearray()
    for payload, ending in _split_lines(data):
        padded = _pad(payload, record_type)
        encoded = record_type.from_bytes(padded).to_bytes()
        if encoded != padded:
            raise RecordFormatError(
                f"{record_type.RECORD_NAME} did not match the input bytes"
            )
        out += payload
        out += ending
    return bytes(out)


def _pad(payload: bytes, record_type: Type[FixedRecord]) -> bytes:
    length = record_type.RECORD_LENGTH
    if len(payload) > length:
        raise RecordFormatError(
            f"{record_type.RECORD_NAME} must be {length} bytes, got {len(payload)}"
        )
    if len(payload) < length:
        # Only a missing tail of spaces is restored. Anything else fails the
        # numeric check inside from_bytes, or the match inside reserialize.
        return payload + (b" " * (length - len(payload)))
    return payload


def _split_lines(data: bytes) -> List[Tuple[bytes, bytes]]:
    if not isinstance(data, bytes):
        raise RecordFormatError("file must be bytes")

    lines: List[Tuple[bytes, bytes]] = []
    index = 0
    size = len(data)
    while index < size:
        end = index
        while end < size and data[end] not in (10, 13):
            end += 1
        payload = data[index:end]
        if end >= size:
            ending = b""
            index = size
        elif data[end : end + 2] == b"\r\n":
            ending = b"\r\n"
            index = end + 2
        else:
            ending = data[end : end + 1]
            index = end + 1
        lines.append((payload, ending))
    return lines
