# This file is a stripped version of piexif

import copy
import numbers
import struct

class TYPES:
    Byte = 1
    Ascii = 2
    Short = 3
    Long = 4
    Rational = 5
    SByte = 6
    Undefined = 7
    SShort = 8
    SLong = 9
    SRational = 10
    Float = 11
    DFloat = 12


TAGS = {
    'Image': {
       34853: {'name': 'GPSTag', 'type': TYPES.Long},
    },
    'GPS': {
        1: {'name': 'GPSLatitudeRef', 'type': TYPES.Ascii},
        2: {'name': 'GPSLatitude', 'type': TYPES.Rational},
        3: {'name': 'GPSLongitudeRef', 'type': TYPES.Ascii},
        4: {'name': 'GPSLongitude', 'type': TYPES.Rational},
    },
}

class ImageIFD:
    """Exif tag number reference - 0th IFD"""
    GPSTag = 34853

class GPSIFD:
    """Exif tag number reference - GPS IFD"""
    GPSLatitudeRef = 1
    GPSLatitude = 2
    GPSLongitudeRef = 3
    GPSLongitude = 4

TIFF_HEADER_LENGTH = 8

def dump(exif_dict_original):
    exif_dict = copy.deepcopy(exif_dict_original)
    header = b"Exif\x00\x00\x4d\x4d\x00\x2a\x00\x00\x00\x08\x00\x01"
    first_ifd_pointer = b"\x00\x00\x00\x00"

    gps_ifd = exif_dict["GPS"]
    offset = 18

    gps_bytes = b"".join(_dict_to_bytes(gps_ifd, "GPS", offset))
    pointer = struct.pack(">I", TIFF_HEADER_LENGTH + offset)
    key = struct.pack(">H", ImageIFD.GPSTag)
    type = struct.pack(">H", TYPES.Long)
    length = struct.pack(">I", 1)
    gps_pointer = key + type + length + pointer

    return (header + gps_pointer + first_ifd_pointer + gps_bytes)

def _value_to_bytes(raw_value, value_type, offset):
    four_bytes_over = b""
    value_str = b""

    if value_type == TYPES.Ascii:
        new_value = raw_value.encode("latin1") + b"\x00"
        length = len(new_value)
        if length > 4:
            value_str = struct.pack(">I", offset)
            four_bytes_over = new_value
        else:
            value_str = new_value + b"\x00" * (4 - length)
    elif value_type == TYPES.Rational:
        if isinstance(raw_value[0], numbers.Integral):
            length = 1
            num, den = raw_value
            new_value = struct.pack(">L", num) + struct.pack(">L", den)
        elif isinstance(raw_value[0], tuple):
            length = len(raw_value)
            new_value = b""
            for n, val in enumerate(raw_value):
                num, den = val
                new_value += (struct.pack(">L", num) +
                                struct.pack(">L", den))
        value_str = struct.pack(">I", offset)
        four_bytes_over = new_value

    length_str = struct.pack(">I", length)
    return length_str, value_str, four_bytes_over

def _dict_to_bytes(ifd_dict, ifd, ifd_offset):
    tag_count = len(ifd_dict)
    entry_header = struct.pack(">H", tag_count)
    entries_length = 2 + tag_count * 12
    entries = b""
    values = b""

    for n, key in enumerate(sorted(ifd_dict)):
        raw_value = ifd_dict[key]
        key_str = struct.pack(">H", key)
        value_type = TAGS[ifd][key]["type"]
        type_str = struct.pack(">H", value_type)
        four_bytes_over = b""
        offset = TIFF_HEADER_LENGTH + entries_length + ifd_offset + len(values)

        length_str, value_str, four_bytes_over = _value_to_bytes(raw_value, value_type, offset)

        entries += key_str + type_str + length_str + value_str
        values += four_bytes_over
    return (entry_header + entries, values)
