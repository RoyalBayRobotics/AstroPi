# Stripped and packed version of piexif with only dump function
import copy
import numbers
import struct

class InvalidImageDataError(ValueError):
    pass

def split_into_segments(data):
    """Slices JPEG meta data into a list from JPEG binary data.
    """
    if data[0:2] != b"\xff\xd8":
        raise InvalidImageDataError("Given data isn't JPEG.")

    head = 2
    segments = [b"\xff\xd8"]
    while 1:
        if data[head: head + 2] == b"\xff\xda":
            segments.append(data[head:])
            break
        else:
            length = struct.unpack(">H", data[head + 2: head + 4])[0]
            endPoint = head + length + 2
            seg = data[head: endPoint]
            segments.append(seg)
            head = endPoint

        if (head >= len(data)):
            raise InvalidImageDataError("Wrong JPEG data.")
    return segments

def read_exif_from_file(filename):
    """Slices JPEG meta data into a list from JPEG binary data.
    """
    f = open(filename, "rb")
    data = f.read(6)

    if data[0:2] != b"\xff\xd8":
        raise InvalidImageDataError("Given data isn't JPEG.")

    head = data[2:6]
    HEAD_LENGTH = 4
    exif = None
    while len(head) == HEAD_LENGTH:
        length = struct.unpack(">H", head[2: 4])[0]

        if head[:2] == b"\xff\xe1":
            segment_data = f.read(length - 2)
            if segment_data[:4] != b'Exif':
                head = f.read(HEAD_LENGTH)
                continue
            exif = head + segment_data
            break
        elif head[0:1] == b"\xff":
            f.read(length - 2)
            head = f.read(HEAD_LENGTH)
        else:
            break

    f.close()
    return exif

def get_exif_seg(segments):
    """Returns Exif from JPEG meta data list
    """
    for seg in segments:
        if seg[0:2] == b"\xff\xe1" and seg[4:10] == b"Exif\x00\x00":
            return seg
    return None


def merge_segments(segments, exif=b""):
    """Merges Exif with APP0 and APP1 manipulations.
    """
    if segments[1][0:2] == b"\xff\xe0" and \
       segments[2][0:2] == b"\xff\xe1" and \
       segments[2][4:10] == b"Exif\x00\x00":
        if exif:
            segments[2] = exif
            segments.pop(1)
        elif exif is None:
            segments.pop(2)
        else:
            segments.pop(1)
    elif segments[1][0:2] == b"\xff\xe0":
        if exif:
            segments[1] = exif
    elif segments[1][0:2] == b"\xff\xe1" and \
         segments[1][4:10] == b"Exif\x00\x00":
        if exif:
            segments[1] = exif
        elif exif is None:
            segments.pop(1)
    else:
        if exif:
            segments.insert(1, exif)
    return b"".join(segments)


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
    'Image': {11: {'name': 'ProcessingSoftware', 'type': TYPES.Ascii},
               254: {'name': 'NewSubfileType', 'type': TYPES.Long},
               255: {'name': 'SubfileType', 'type': TYPES.Short},
               256: {'name': 'ImageWidth', 'type': TYPES.Long},
               257: {'name': 'ImageLength', 'type': TYPES.Long},
               258: {'name': 'BitsPerSample', 'type': TYPES.Short},
               259: {'name': 'Compression', 'type': TYPES.Short},
               262: {'name': 'PhotometricInterpretation', 'type': TYPES.Short},
               263: {'name': 'Threshholding', 'type': TYPES.Short},
               264: {'name': 'CellWidth', 'type': TYPES.Short},
               265: {'name': 'CellLength', 'type': TYPES.Short},
               266: {'name': 'FillOrder', 'type': TYPES.Short},
               269: {'name': 'DocumentName', 'type': TYPES.Ascii},
               270: {'name': 'ImageDescription', 'type': TYPES.Ascii},
               271: {'name': 'Make', 'type': TYPES.Ascii},
               272: {'name': 'Model', 'type': TYPES.Ascii},
               273: {'name': 'StripOffsets', 'type': TYPES.Long},
               274: {'name': 'Orientation', 'type': TYPES.Short},
               277: {'name': 'SamplesPerPixel', 'type': TYPES.Short},
               278: {'name': 'RowsPerStrip', 'type': TYPES.Long},
               279: {'name': 'StripByteCounts', 'type': TYPES.Long},
               282: {'name': 'XResolution', 'type': TYPES.Rational},
               283: {'name': 'YResolution', 'type': TYPES.Rational},
               284: {'name': 'PlanarConfiguration', 'type': TYPES.Short},
               290: {'name': 'GrayResponseUnit', 'type': TYPES.Short},
               291: {'name': 'GrayResponseCurve', 'type': TYPES.Short},
               292: {'name': 'T4Options', 'type': TYPES.Long},
               293: {'name': 'T6Options', 'type': TYPES.Long},
               296: {'name': 'ResolutionUnit', 'type': TYPES.Short},
               301: {'name': 'TransferFunction', 'type': TYPES.Short},
               305: {'name': 'Software', 'type': TYPES.Ascii},
               306: {'name': 'DateTime', 'type': TYPES.Ascii},
               315: {'name': 'Artist', 'type': TYPES.Ascii},
               316: {'name': 'HostComputer', 'type': TYPES.Ascii},
               317: {'name': 'Predictor', 'type': TYPES.Short},
               318: {'name': 'WhitePoint', 'type': TYPES.Rational},
               319: {'name': 'PrimaryChromaticities', 'type': TYPES.Rational},
               320: {'name': 'ColorMap', 'type': TYPES.Short},
               321: {'name': 'HalftoneHints', 'type': TYPES.Short},
               322: {'name': 'TileWidth', 'type': TYPES.Short},
               323: {'name': 'TileLength', 'type': TYPES.Short},
               324: {'name': 'TileOffsets', 'type': TYPES.Short},
               325: {'name': 'TileByteCounts', 'type': TYPES.Short},
               330: {'name': 'SubIFDs', 'type': TYPES.Long},
               332: {'name': 'InkSet', 'type': TYPES.Short},
               333: {'name': 'InkNames', 'type': TYPES.Ascii},
               334: {'name': 'NumberOfInks', 'type': TYPES.Short},
               336: {'name': 'DotRange', 'type': TYPES.Byte},
               337: {'name': 'TargetPrinter', 'type': TYPES.Ascii},
               338: {'name': 'ExtraSamples', 'type': TYPES.Short},
               339: {'name': 'SampleFormat', 'type': TYPES.Short},
               340: {'name': 'SMinSampleValue', 'type': TYPES.Short},
               341: {'name': 'SMaxSampleValue', 'type': TYPES.Short},
               342: {'name': 'TransferRange', 'type': TYPES.Short},
               343: {'name': 'ClipPath', 'type': TYPES.Byte},
               344: {'name': 'XClipPathUnits', 'type': TYPES.Long},
               345: {'name': 'YClipPathUnits', 'type': TYPES.Long},
               346: {'name': 'Indexed', 'type': TYPES.Short},
               347: {'name': 'JPEGTables', 'type': TYPES.Undefined},
               351: {'name': 'OPIProxy', 'type': TYPES.Short},
               512: {'name': 'JPEGProc', 'type': TYPES.Long},
               513: {'name': 'JPEGInterchangeFormat', 'type': TYPES.Long},
               514: {'name': 'JPEGInterchangeFormatLength', 'type': TYPES.Long},
               515: {'name': 'JPEGRestartInterval', 'type': TYPES.Short},
               517: {'name': 'JPEGLosslessPredictors', 'type': TYPES.Short},
               518: {'name': 'JPEGPointTransforms', 'type': TYPES.Short},
               519: {'name': 'JPEGQTables', 'type': TYPES.Long},
               520: {'name': 'JPEGDCTables', 'type': TYPES.Long},
               521: {'name': 'JPEGACTables', 'type': TYPES.Long},
               529: {'name': 'YCbCrCoefficients', 'type': TYPES.Rational},
               530: {'name': 'YCbCrSubSampling', 'type': TYPES.Short},
               531: {'name': 'YCbCrPositioning', 'type': TYPES.Short},
               532: {'name': 'ReferenceBlackWhite', 'type': TYPES.Rational},
               700: {'name': 'XMLPacket', 'type': TYPES.Byte},
               18246: {'name': 'Rating', 'type': TYPES.Short},
               18249: {'name': 'RatingPercent', 'type': TYPES.Short},
               32781: {'name': 'ImageID', 'type': TYPES.Ascii},
               33421: {'name': 'CFARepeatPatternDim', 'type': TYPES.Short},
               33422: {'name': 'CFAPattern', 'type': TYPES.Byte},
               33423: {'name': 'BatteryLevel', 'type': TYPES.Rational},
               33432: {'name': 'Copyright', 'type': TYPES.Ascii},
               33434: {'name': 'ExposureTime', 'type': TYPES.Rational},
               34377: {'name': 'ImageResources', 'type': TYPES.Byte},
               34665: {'name': 'ExifTag', 'type': TYPES.Long},
               34675: {'name': 'InterColorProfile', 'type': TYPES.Undefined},
               34853: {'name': 'GPSTag', 'type': TYPES.Long},
               34857: {'name': 'Interlace', 'type': TYPES.Short},
               34858: {'name': 'TimeZoneOffset', 'type': TYPES.Long},
               34859: {'name': 'SelfTimerMode', 'type': TYPES.Short},
               37387: {'name': 'FlashEnergy', 'type': TYPES.Rational},
               37388: {'name': 'SpatialFrequencyResponse', 'type': TYPES.Undefined},
               37389: {'name': 'Noise', 'type': TYPES.Undefined},
               37390: {'name': 'FocalPlaneXResolution', 'type': TYPES.Rational},
               37391: {'name': 'FocalPlaneYResolution', 'type': TYPES.Rational},
               37392: {'name': 'FocalPlaneResolutionUnit', 'type': TYPES.Short},
               37393: {'name': 'ImageNumber', 'type': TYPES.Long},
               37394: {'name': 'SecurityClassification', 'type': TYPES.Ascii},
               37395: {'name': 'ImageHistory', 'type': TYPES.Ascii},
               37397: {'name': 'ExposureIndex', 'type': TYPES.Rational},
               37398: {'name': 'TIFFEPStandardID', 'type': TYPES.Byte},
               37399: {'name': 'SensingMethod', 'type': TYPES.Short},
               40091: {'name': 'XPTitle', 'type': TYPES.Byte},
               40092: {'name': 'XPComment', 'type': TYPES.Byte},
               40093: {'name': 'XPAuthor', 'type': TYPES.Byte},
               40094: {'name': 'XPKeywords', 'type': TYPES.Byte},
               40095: {'name': 'XPSubject', 'type': TYPES.Byte},
               50341: {'name': 'PrintImageMatching', 'type': TYPES.Undefined},
               50706: {'name': 'DNGVersion', 'type': TYPES.Byte},
               50707: {'name': 'DNGBackwardVersion', 'type': TYPES.Byte},
               50708: {'name': 'UniqueCameraModel', 'type': TYPES.Ascii},
               50709: {'name': 'LocalizedCameraModel', 'type': TYPES.Byte},
               50710: {'name': 'CFAPlaneColor', 'type': TYPES.Byte},
               50711: {'name': 'CFALayout', 'type': TYPES.Short},
               50712: {'name': 'LinearizationTable', 'type': TYPES.Short},
               50713: {'name': 'BlackLevelRepeatDim', 'type': TYPES.Short},
               50714: {'name': 'BlackLevel', 'type': TYPES.Rational},
               50715: {'name': 'BlackLevelDeltaH', 'type': TYPES.SRational},
               50716: {'name': 'BlackLevelDeltaV', 'type': TYPES.SRational},
               50717: {'name': 'WhiteLevel', 'type': TYPES.Short},
               50718: {'name': 'DefaultScale', 'type': TYPES.Rational},
               50719: {'name': 'DefaultCropOrigin', 'type': TYPES.Short},
               50720: {'name': 'DefaultCropSize', 'type': TYPES.Short},
               50721: {'name': 'ColorMatrix1', 'type': TYPES.SRational},
               50722: {'name': 'ColorMatrix2', 'type': TYPES.SRational},
               50723: {'name': 'CameraCalibration1', 'type': TYPES.SRational},
               50724: {'name': 'CameraCalibration2', 'type': TYPES.SRational},
               50725: {'name': 'ReductionMatrix1', 'type': TYPES.SRational},
               50726: {'name': 'ReductionMatrix2', 'type': TYPES.SRational},
               50727: {'name': 'AnalogBalance', 'type': TYPES.Rational},
               50728: {'name': 'AsShotNeutral', 'type': TYPES.Short},
               50729: {'name': 'AsShotWhiteXY', 'type': TYPES.Rational},
               50730: {'name': 'BaselineExposure', 'type': TYPES.SRational},
               50731: {'name': 'BaselineNoise', 'type': TYPES.Rational},
               50732: {'name': 'BaselineSharpness', 'type': TYPES.Rational},
               50733: {'name': 'BayerGreenSplit', 'type': TYPES.Long},
               50734: {'name': 'LinearResponseLimit', 'type': TYPES.Rational},
               50735: {'name': 'CameraSerialNumber', 'type': TYPES.Ascii},
               50736: {'name': 'LensInfo', 'type': TYPES.Rational},
               50737: {'name': 'ChromaBlurRadius', 'type': TYPES.Rational},
               50738: {'name': 'AntiAliasStrength', 'type': TYPES.Rational},
               50739: {'name': 'ShadowScale', 'type': TYPES.SRational},
               50740: {'name': 'DNGPrivateData', 'type': TYPES.Byte},
               50741: {'name': 'MakerNoteSafety', 'type': TYPES.Short},
               50778: {'name': 'CalibrationIlluminant1', 'type': TYPES.Short},
               50779: {'name': 'CalibrationIlluminant2', 'type': TYPES.Short},
               50780: {'name': 'BestQualityScale', 'type': TYPES.Rational},
               50781: {'name': 'RawDataUniqueID', 'type': TYPES.Byte},
               50827: {'name': 'OriginalRawFileName', 'type': TYPES.Byte},
               50828: {'name': 'OriginalRawFileData', 'type': TYPES.Undefined},
               50829: {'name': 'ActiveArea', 'type': TYPES.Short},
               50830: {'name': 'MaskedAreas', 'type': TYPES.Short},
               50831: {'name': 'AsShotICCProfile', 'type': TYPES.Undefined},
               50832: {'name': 'AsShotPreProfileMatrix', 'type': TYPES.SRational},
               50833: {'name': 'CurrentICCProfile', 'type': TYPES.Undefined},
               50834: {'name': 'CurrentPreProfileMatrix', 'type': TYPES.SRational},
               50879: {'name': 'ColorimetricReference', 'type': TYPES.Short},
               50931: {'name': 'CameraCalibrationSignature', 'type': TYPES.Byte},
               50932: {'name': 'ProfileCalibrationSignature', 'type': TYPES.Byte},
               50934: {'name': 'AsShotProfileName', 'type': TYPES.Byte},
               50935: {'name': 'NoiseReductionApplied', 'type': TYPES.Rational},
               50936: {'name': 'ProfileName', 'type': TYPES.Byte},
               50937: {'name': 'ProfileHueSatMapDims', 'type': TYPES.Long},
               50938: {'name': 'ProfileHueSatMapData1', 'type': TYPES.Float},
               50939: {'name': 'ProfileHueSatMapData2', 'type': TYPES.Float},
               50940: {'name': 'ProfileToneCurve', 'type': TYPES.Float},
               50941: {'name': 'ProfileEmbedPolicy', 'type': TYPES.Long},
               50942: {'name': 'ProfileCopyright', 'type': TYPES.Byte},
               50964: {'name': 'ForwardMatrix1', 'type': TYPES.SRational},
               50965: {'name': 'ForwardMatrix2', 'type': TYPES.SRational},
               50966: {'name': 'PreviewApplicationName', 'type': TYPES.Byte},
               50967: {'name': 'PreviewApplicationVersion', 'type': TYPES.Byte},
               50968: {'name': 'PreviewSettingsName', 'type': TYPES.Byte},
               50969: {'name': 'PreviewSettingsDigest', 'type': TYPES.Byte},
               50970: {'name': 'PreviewColorSpace', 'type': TYPES.Long},
               50971: {'name': 'PreviewDateTime', 'type': TYPES.Ascii},
               50972: {'name': 'RawImageDigest', 'type': TYPES.Undefined},
               50973: {'name': 'OriginalRawFileDigest', 'type': TYPES.Undefined},
               50974: {'name': 'SubTileBlockSize', 'type': TYPES.Long},
               50975: {'name': 'RowInterleaveFactor', 'type': TYPES.Long},
               50981: {'name': 'ProfileLookTableDims', 'type': TYPES.Long},
               50982: {'name': 'ProfileLookTableData', 'type': TYPES.Float},
               51008: {'name': 'OpcodeList1', 'type': TYPES.Undefined},
               51009: {'name': 'OpcodeList2', 'type': TYPES.Undefined},
               51022: {'name': 'OpcodeList3', 'type': TYPES.Undefined},
               60606: {'name': 'ZZZTestSlong1', 'type': TYPES.SLong},
               60607: {'name': 'ZZZTestSlong2', 'type': TYPES.SLong},
               60608: {'name': 'ZZZTestSByte', 'type': TYPES.SByte},
               60609: {'name': 'ZZZTestSShort', 'type': TYPES.SShort},
               60610: {'name': 'ZZZTestDFloat', 'type': TYPES.DFloat},},
    'Exif': {33434: {'name': 'ExposureTime', 'type': TYPES.Rational},
             33437: {'name': 'FNumber', 'type': TYPES.Rational},
             34850: {'name': 'ExposureProgram', 'type': TYPES.Short},
             34852: {'name': 'SpectralSensitivity', 'type': TYPES.Ascii},
             34855: {'name': 'ISOSpeedRatings', 'type': TYPES.Short},
             34856: {'name': 'OECF', 'type': TYPES.Undefined},
             34864: {'name': 'SensitivityType', 'type': TYPES.Short},
             34865: {'name': 'StandardOutputSensitivity', 'type': TYPES.Long},
             34866: {'name': 'RecommendedExposureIndex', 'type': TYPES.Long},
             34867: {'name': 'ISOSpeed', 'type': TYPES.Long},
             34868: {'name': 'ISOSpeedLatitudeyyy', 'type': TYPES.Long},
             34869: {'name': 'ISOSpeedLatitudezzz', 'type': TYPES.Long},
             36864: {'name': 'ExifVersion', 'type': TYPES.Undefined},
             36867: {'name': 'DateTimeOriginal', 'type': TYPES.Ascii},
             36868: {'name': 'DateTimeDigitized', 'type': TYPES.Ascii},
             36880: {'name': 'OffsetTime', 'type': TYPES.Ascii},
             36881: {'name': 'OffsetTimeOriginal', 'type': TYPES.Ascii},
             36882: {'name': 'OffsetTimeDigitized', 'type': TYPES.Ascii},
             37121: {'name': 'ComponentsConfiguration', 'type': TYPES.Undefined},
             37122: {'name': 'CompressedBitsPerPixel', 'type': TYPES.Rational},
             37377: {'name': 'ShutterSpeedValue', 'type': TYPES.SRational},
             37378: {'name': 'ApertureValue', 'type': TYPES.Rational},
             37379: {'name': 'BrightnessValue', 'type': TYPES.SRational},
             37380: {'name': 'ExposureBiasValue', 'type': TYPES.SRational},
             37381: {'name': 'MaxApertureValue', 'type': TYPES.Rational},
             37382: {'name': 'SubjectDistance', 'type': TYPES.Rational},
             37383: {'name': 'MeteringMode', 'type': TYPES.Short},
             37384: {'name': 'LightSource', 'type': TYPES.Short},
             37385: {'name': 'Flash', 'type': TYPES.Short},
             37386: {'name': 'FocalLength', 'type': TYPES.Rational},
             37396: {'name': 'SubjectArea', 'type': TYPES.Short},
             37500: {'name': 'MakerNote', 'type': TYPES.Undefined},
             37510: {'name': 'UserComment', 'type': TYPES.Undefined},
             37520: {'name': 'SubSecTime', 'type': TYPES.Ascii},
             37521: {'name': 'SubSecTimeOriginal', 'type': TYPES.Ascii},
             37522: {'name': 'SubSecTimeDigitized', 'type': TYPES.Ascii},
             37888: {'name': 'Temperature', 'type': TYPES.SRational},
             37889: {'name': 'Humidity', 'type': TYPES.Rational},
             37890: {'name': 'Pressure', 'type': TYPES.Rational},
             37891: {'name': 'WaterDepth', 'type': TYPES.SRational},
             37892: {'name': 'Acceleration', 'type': TYPES.Rational},
             37893: {'name': 'CameraElevationAngle', 'type': TYPES.SRational},
             40960: {'name': 'FlashpixVersion', 'type': TYPES.Undefined},
             40961: {'name': 'ColorSpace', 'type': TYPES.Short},
             40962: {'name': 'PixelXDimension', 'type': TYPES.Long},
             40963: {'name': 'PixelYDimension', 'type': TYPES.Long},
             40964: {'name': 'RelatedSoundFile', 'type': TYPES.Ascii},
             40965: {'name': 'InteroperabilityTag', 'type': TYPES.Long},
             41483: {'name': 'FlashEnergy', 'type': TYPES.Rational},
             41484: {'name': 'SpatialFrequencyResponse', 'type': TYPES.Undefined},
             41486: {'name': 'FocalPlaneXResolution', 'type': TYPES.Rational},
             41487: {'name': 'FocalPlaneYResolution', 'type': TYPES.Rational},
             41488: {'name': 'FocalPlaneResolutionUnit', 'type': TYPES.Short},
             41492: {'name': 'SubjectLocation', 'type': TYPES.Short},
             41493: {'name': 'ExposureIndex', 'type': TYPES.Rational},
             41495: {'name': 'SensingMethod', 'type': TYPES.Short},
             41728: {'name': 'FileSource', 'type': TYPES.Undefined},
             41729: {'name': 'SceneType', 'type': TYPES.Undefined},
             41730: {'name': 'CFAPattern', 'type': TYPES.Undefined},
             41985: {'name': 'CustomRendered', 'type': TYPES.Short},
             41986: {'name': 'ExposureMode', 'type': TYPES.Short},
             41987: {'name': 'WhiteBalance', 'type': TYPES.Short},
             41988: {'name': 'DigitalZoomRatio', 'type': TYPES.Rational},
             41989: {'name': 'FocalLengthIn35mmFilm', 'type': TYPES.Short},
             41990: {'name': 'SceneCaptureType', 'type': TYPES.Short},
             41991: {'name': 'GainControl', 'type': TYPES.Short},
             41992: {'name': 'Contrast', 'type': TYPES.Short},
             41993: {'name': 'Saturation', 'type': TYPES.Short},
             41994: {'name': 'Sharpness', 'type': TYPES.Short},
             41995: {'name': 'DeviceSettingDescription', 'type': TYPES.Undefined},
             41996: {'name': 'SubjectDistanceRange', 'type': TYPES.Short},
             42016: {'name': 'ImageUniqueID', 'type': TYPES.Ascii},
             42032: {'name': 'CameraOwnerName', 'type': TYPES.Ascii},
             42033: {'name': 'BodySerialNumber', 'type': TYPES.Ascii},
             42034: {'name': 'LensSpecification', 'type': TYPES.Rational},
             42035: {'name': 'LensMake', 'type': TYPES.Ascii},
             42036: {'name': 'LensModel', 'type': TYPES.Ascii},
             42037: {'name': 'LensSerialNumber', 'type': TYPES.Ascii},
             42240: {'name': 'Gamma', 'type': TYPES.Rational}},
    'GPS': {0: {'name': 'GPSVersionID', 'type': TYPES.Byte},
                1: {'name': 'GPSLatitudeRef', 'type': TYPES.Ascii},
                2: {'name': 'GPSLatitude', 'type': TYPES.Rational},
                3: {'name': 'GPSLongitudeRef', 'type': TYPES.Ascii},
                4: {'name': 'GPSLongitude', 'type': TYPES.Rational},
                5: {'name': 'GPSAltitudeRef', 'type': TYPES.Byte},
                6: {'name': 'GPSAltitude', 'type': TYPES.Rational},
                7: {'name': 'GPSTimeStamp', 'type': TYPES.Rational},
                8: {'name': 'GPSSatellites', 'type': TYPES.Ascii},
                9: {'name': 'GPSStatus', 'type': TYPES.Ascii},
                10: {'name': 'GPSMeasureMode', 'type': TYPES.Ascii},
                11: {'name': 'GPSDOP', 'type': TYPES.Rational},
                12: {'name': 'GPSSpeedRef', 'type': TYPES.Ascii},
                13: {'name': 'GPSSpeed', 'type': TYPES.Rational},
                14: {'name': 'GPSTrackRef', 'type': TYPES.Ascii},
                15: {'name': 'GPSTrack', 'type': TYPES.Rational},
                16: {'name': 'GPSImgDirectionRef', 'type': TYPES.Ascii},
                17: {'name': 'GPSImgDirection', 'type': TYPES.Rational},
                18: {'name': 'GPSMapDatum', 'type': TYPES.Ascii},
                19: {'name': 'GPSDestLatitudeRef', 'type': TYPES.Ascii},
                20: {'name': 'GPSDestLatitude', 'type': TYPES.Rational},
                21: {'name': 'GPSDestLongitudeRef', 'type': TYPES.Ascii},
                22: {'name': 'GPSDestLongitude', 'type': TYPES.Rational},
                23: {'name': 'GPSDestBearingRef', 'type': TYPES.Ascii},
                24: {'name': 'GPSDestBearing', 'type': TYPES.Rational},
                25: {'name': 'GPSDestDistanceRef', 'type': TYPES.Ascii},
                26: {'name': 'GPSDestDistance', 'type': TYPES.Rational},
                27: {'name': 'GPSProcessingMethod', 'type': TYPES.Undefined},
                28: {'name': 'GPSAreaInformation', 'type': TYPES.Undefined},
                29: {'name': 'GPSDateStamp', 'type': TYPES.Ascii},
                30: {'name': 'GPSDifferential', 'type': TYPES.Short},
                31: {'name': 'GPSHPositioningError', 'type': TYPES.Rational}},
    'Interop': {1: {'name': 'InteroperabilityIndex', 'type': TYPES.Ascii}},
}

TAGS["0th"] = TAGS["Image"]
TAGS["1st"] = TAGS["Image"]

class ImageIFD:
    """Exif tag number reference - 0th IFD"""
    ProcessingSoftware = 11
    NewSubfileType = 254
    SubfileType = 255
    ImageWidth = 256
    ImageLength = 257
    BitsPerSample = 258
    Compression = 259
    PhotometricInterpretation = 262
    Threshholding = 263
    CellWidth = 264
    CellLength = 265
    FillOrder = 266
    DocumentName = 269
    ImageDescription = 270
    Make = 271
    Model = 272
    StripOffsets = 273
    Orientation = 274
    SamplesPerPixel = 277
    RowsPerStrip = 278
    StripByteCounts = 279
    XResolution = 282
    YResolution = 283
    PlanarConfiguration = 284
    GrayResponseUnit = 290
    GrayResponseCurve = 291
    T4Options = 292
    T6Options = 293
    ResolutionUnit = 296
    TransferFunction = 301
    Software = 305
    DateTime = 306
    Artist = 315
    HostComputer = 316
    Predictor = 317
    WhitePoint = 318
    PrimaryChromaticities = 319
    ColorMap = 320
    HalftoneHints = 321
    TileWidth = 322
    TileLength = 323
    TileOffsets = 324
    TileByteCounts = 325
    SubIFDs = 330
    InkSet = 332
    InkNames = 333
    NumberOfInks = 334
    DotRange = 336
    TargetPrinter = 337
    ExtraSamples = 338
    SampleFormat = 339
    SMinSampleValue = 340
    SMaxSampleValue = 341
    TransferRange = 342
    ClipPath = 343
    XClipPathUnits = 344
    YClipPathUnits = 345
    Indexed = 346
    JPEGTables = 347
    OPIProxy = 351
    JPEGProc = 512
    JPEGInterchangeFormat = 513
    JPEGInterchangeFormatLength = 514
    JPEGRestartInterval = 515
    JPEGLosslessPredictors = 517
    JPEGPointTransforms = 518
    JPEGQTables = 519
    JPEGDCTables = 520
    JPEGACTables = 521
    YCbCrCoefficients = 529
    YCbCrSubSampling = 530
    YCbCrPositioning = 531
    ReferenceBlackWhite = 532
    XMLPacket = 700
    Rating = 18246
    RatingPercent = 18249
    ImageID = 32781
    CFARepeatPatternDim = 33421
    CFAPattern = 33422
    BatteryLevel = 33423
    Copyright = 33432
    ExposureTime = 33434
    ImageResources = 34377
    ExifTag = 34665
    InterColorProfile = 34675
    GPSTag = 34853
    Interlace = 34857
    TimeZoneOffset = 34858
    SelfTimerMode = 34859
    FlashEnergy = 37387
    SpatialFrequencyResponse = 37388
    Noise = 37389
    FocalPlaneXResolution = 37390
    FocalPlaneYResolution = 37391
    FocalPlaneResolutionUnit = 37392
    ImageNumber = 37393
    SecurityClassification = 37394
    ImageHistory = 37395
    ExposureIndex = 37397
    TIFFEPStandardID = 37398
    SensingMethod = 37399
    XPTitle = 40091
    XPComment = 40092
    XPAuthor = 40093
    XPKeywords = 40094
    XPSubject = 40095
    PrintImageMatching = 50341
    DNGVersion = 50706
    DNGBackwardVersion = 50707
    UniqueCameraModel = 50708
    LocalizedCameraModel = 50709
    CFAPlaneColor = 50710
    CFALayout = 50711
    LinearizationTable = 50712
    BlackLevelRepeatDim = 50713
    BlackLevel = 50714
    BlackLevelDeltaH = 50715
    BlackLevelDeltaV = 50716
    WhiteLevel = 50717
    DefaultScale = 50718
    DefaultCropOrigin = 50719
    DefaultCropSize = 50720
    ColorMatrix1 = 50721
    ColorMatrix2 = 50722
    CameraCalibration1 = 50723
    CameraCalibration2 = 50724
    ReductionMatrix1 = 50725
    ReductionMatrix2 = 50726
    AnalogBalance = 50727
    AsShotNeutral = 50728
    AsShotWhiteXY = 50729
    BaselineExposure = 50730
    BaselineNoise = 50731
    BaselineSharpness = 50732
    BayerGreenSplit = 50733
    LinearResponseLimit = 50734
    CameraSerialNumber = 50735
    LensInfo = 50736
    ChromaBlurRadius = 50737
    AntiAliasStrength = 50738
    ShadowScale = 50739
    DNGPrivateData = 50740
    MakerNoteSafety = 50741
    CalibrationIlluminant1 = 50778
    CalibrationIlluminant2 = 50779
    BestQualityScale = 50780
    RawDataUniqueID = 50781
    OriginalRawFileName = 50827
    OriginalRawFileData = 50828
    ActiveArea = 50829
    MaskedAreas = 50830
    AsShotICCProfile = 50831
    AsShotPreProfileMatrix = 50832
    CurrentICCProfile = 50833
    CurrentPreProfileMatrix = 50834
    ColorimetricReference = 50879
    CameraCalibrationSignature = 50931
    ProfileCalibrationSignature = 50932
    AsShotProfileName = 50934
    NoiseReductionApplied = 50935
    ProfileName = 50936
    ProfileHueSatMapDims = 50937
    ProfileHueSatMapData1 = 50938
    ProfileHueSatMapData2 = 50939
    ProfileToneCurve = 50940
    ProfileEmbedPolicy = 50941
    ProfileCopyright = 50942
    ForwardMatrix1 = 50964
    ForwardMatrix2 = 50965
    PreviewApplicationName = 50966
    PreviewApplicationVersion = 50967
    PreviewSettingsName = 50968
    PreviewSettingsDigest = 50969
    PreviewColorSpace = 50970
    PreviewDateTime = 50971
    RawImageDigest = 50972
    OriginalRawFileDigest = 50973
    SubTileBlockSize = 50974
    RowInterleaveFactor = 50975
    ProfileLookTableDims = 50981
    ProfileLookTableData = 50982
    OpcodeList1 = 51008
    OpcodeList2 = 51009
    OpcodeList3 = 51022
    NoiseProfile = 51041
    ZZZTestSlong1 = 60606
    ZZZTestSlong2 = 60607
    ZZZTestSByte = 60608
    ZZZTestSShort = 60609
    ZZZTestDFloat = 60610


class ExifIFD:
    """Exif tag number reference - Exif IFD"""
    ExposureTime = 33434
    FNumber = 33437
    ExposureProgram = 34850
    SpectralSensitivity = 34852
    ISOSpeedRatings = 34855
    OECF = 34856
    SensitivityType = 34864
    StandardOutputSensitivity = 34865
    RecommendedExposureIndex = 34866
    ISOSpeed = 34867
    ISOSpeedLatitudeyyy = 34868
    ISOSpeedLatitudezzz = 34869
    ExifVersion = 36864
    DateTimeOriginal = 36867
    DateTimeDigitized = 36868
    OffsetTime = 36880
    OffsetTimeOriginal = 36881
    OffsetTimeDigitized = 36882
    ComponentsConfiguration = 37121
    CompressedBitsPerPixel = 37122
    ShutterSpeedValue = 37377
    ApertureValue = 37378
    BrightnessValue = 37379
    ExposureBiasValue = 37380
    MaxApertureValue = 37381
    SubjectDistance = 37382
    MeteringMode = 37383
    LightSource = 37384
    Flash = 37385
    FocalLength = 37386
    Temperature = 37888
    Humidity = 37889
    Pressure = 37890
    WaterDepth = 37891
    Acceleration = 37892
    CameraElevationAngle = 37893
    SubjectArea = 37396
    MakerNote = 37500
    UserComment = 37510
    SubSecTime = 37520
    SubSecTimeOriginal = 37521
    SubSecTimeDigitized = 37522
    FlashpixVersion = 40960
    ColorSpace = 40961
    PixelXDimension = 40962
    PixelYDimension = 40963
    RelatedSoundFile = 40964
    InteroperabilityTag = 40965
    FlashEnergy = 41483
    SpatialFrequencyResponse = 41484
    FocalPlaneXResolution = 41486
    FocalPlaneYResolution = 41487
    FocalPlaneResolutionUnit = 41488
    SubjectLocation = 41492
    ExposureIndex = 41493
    SensingMethod = 41495
    FileSource = 41728
    SceneType = 41729
    CFAPattern = 41730
    CustomRendered = 41985
    ExposureMode = 41986
    WhiteBalance = 41987
    DigitalZoomRatio = 41988
    FocalLengthIn35mmFilm = 41989
    SceneCaptureType = 41990
    GainControl = 41991
    Contrast = 41992
    Saturation = 41993
    Sharpness = 41994
    DeviceSettingDescription = 41995
    SubjectDistanceRange = 41996
    ImageUniqueID = 42016
    CameraOwnerName = 42032
    BodySerialNumber = 42033
    LensSpecification = 42034
    LensMake = 42035
    LensModel = 42036
    LensSerialNumber = 42037
    Gamma = 42240


class GPSIFD:
    """Exif tag number reference - GPS IFD"""
    GPSVersionID = 0
    GPSLatitudeRef = 1
    GPSLatitude = 2
    GPSLongitudeRef = 3
    GPSLongitude = 4
    GPSAltitudeRef = 5
    GPSAltitude = 6
    GPSTimeStamp = 7
    GPSSatellites = 8
    GPSStatus = 9
    GPSMeasureMode = 10
    GPSDOP = 11
    GPSSpeedRef = 12
    GPSSpeed = 13
    GPSTrackRef = 14
    GPSTrack = 15
    GPSImgDirectionRef = 16
    GPSImgDirection = 17
    GPSMapDatum = 18
    GPSDestLatitudeRef = 19
    GPSDestLatitude = 20
    GPSDestLongitudeRef = 21
    GPSDestLongitude = 22
    GPSDestBearingRef = 23
    GPSDestBearing = 24
    GPSDestDistanceRef = 25
    GPSDestDistance = 26
    GPSProcessingMethod = 27
    GPSAreaInformation = 28
    GPSDateStamp = 29
    GPSDifferential = 30
    GPSHPositioningError = 31


class InteropIFD:
    """Exif tag number reference - Interoperability IFD"""
    InteroperabilityIndex = 1

TIFF_HEADER_LENGTH = 8


def dump(exif_dict_original):
    """
    py:function:: piexif.load(data)

    Return exif as bytes.

    :param dict exif: Exif data({"0th":dict, "Exif":dict, "GPS":dict, "Interop":dict, "1st":dict, "thumbnail":bytes})
    :return: Exif
    :rtype: bytes
    """
    exif_dict = copy.deepcopy(exif_dict_original)
    header = b"Exif\x00\x00\x4d\x4d\x00\x2a\x00\x00\x00\x08"
    exif_is = False
    gps_is = False
    interop_is = False
    first_is = False

    if "0th" in exif_dict:
        zeroth_ifd = exif_dict["0th"]
    else:
        zeroth_ifd = {}

    if (("Exif" in exif_dict) and len(exif_dict["Exif"]) or
          ("Interop" in exif_dict) and len(exif_dict["Interop"]) ):
        zeroth_ifd[ImageIFD.ExifTag] = 1
        exif_is = True
        exif_ifd = exif_dict["Exif"]
        if ("Interop" in exif_dict) and len(exif_dict["Interop"]):
            exif_ifd[ExifIFD. InteroperabilityTag] = 1
            interop_is = True
            interop_ifd = exif_dict["Interop"]
        elif ExifIFD. InteroperabilityTag in exif_ifd:
            exif_ifd.pop(ExifIFD.InteroperabilityTag)
    elif ImageIFD.ExifTag in zeroth_ifd:
        zeroth_ifd.pop(ImageIFD.ExifTag)

    if ("GPS" in exif_dict) and len(exif_dict["GPS"]):
        zeroth_ifd[ImageIFD.GPSTag] = 1
        gps_is = True
        gps_ifd = exif_dict["GPS"]
    elif ImageIFD.GPSTag in zeroth_ifd:
        zeroth_ifd.pop(ImageIFD.GPSTag)

    if (("1st" in exif_dict) and
            ("thumbnail" in exif_dict) and
            (exif_dict["thumbnail"] is not None)):
        first_is = True
        exif_dict["1st"][ImageIFD.JPEGInterchangeFormat] = 1
        exif_dict["1st"][ImageIFD.JPEGInterchangeFormatLength] = 1
        first_ifd = exif_dict["1st"]

    zeroth_set = _dict_to_bytes(zeroth_ifd, "0th", 0)
    zeroth_length = (len(zeroth_set[0]) + exif_is * 12 + gps_is * 12 + 4 +
                     len(zeroth_set[1]))

    if exif_is:
        exif_set = _dict_to_bytes(exif_ifd, "Exif", zeroth_length)
        exif_length = len(exif_set[0]) + interop_is * 12 + len(exif_set[1])
    else:
        exif_bytes = b""
        exif_length = 0
    if gps_is:
        gps_set = _dict_to_bytes(gps_ifd, "GPS", zeroth_length + exif_length)
        gps_bytes = b"".join(gps_set)
        gps_length = len(gps_bytes)
    else:
        gps_bytes = b""
        gps_length = 0
    if interop_is:
        offset = zeroth_length + exif_length + gps_length
        interop_set = _dict_to_bytes(interop_ifd, "Interop", offset)
        interop_bytes = b"".join(interop_set)
        interop_length = len(interop_bytes)
    else:
        interop_bytes = b""
        interop_length = 0
    if first_is:
        offset = zeroth_length + exif_length + gps_length + interop_length
        first_set = _dict_to_bytes(first_ifd, "1st", offset)
        thumbnail = _get_thumbnail(exif_dict["thumbnail"])
        thumbnail_max_size = 64000
        if len(thumbnail) > thumbnail_max_size:
            raise ValueError("Given thumbnail is too large. max 64kB")
    else:
        first_bytes = b""
    if exif_is:
        pointer_value = TIFF_HEADER_LENGTH + zeroth_length
        pointer_str = struct.pack(">I", pointer_value)
        key = ImageIFD.ExifTag
        key_str = struct.pack(">H", key)
        type_str = struct.pack(">H", TYPES.Long)
        length_str = struct.pack(">I", 1)
        exif_pointer = key_str + type_str + length_str + pointer_str
    else:
        exif_pointer = b""
    if gps_is:
        pointer_value = TIFF_HEADER_LENGTH + zeroth_length + exif_length
        pointer_str = struct.pack(">I", pointer_value)
        key = ImageIFD.GPSTag
        key_str = struct.pack(">H", key)
        type_str = struct.pack(">H", TYPES.Long)
        length_str = struct.pack(">I", 1)
        gps_pointer = key_str + type_str + length_str + pointer_str
    else:
        gps_pointer = b""
    if interop_is:
        pointer_value = (TIFF_HEADER_LENGTH +
                         zeroth_length + exif_length + gps_length)
        pointer_str = struct.pack(">I", pointer_value)
        key = ExifIFD.InteroperabilityTag
        key_str = struct.pack(">H", key)
        type_str = struct.pack(">H", TYPES.Long)
        length_str = struct.pack(">I", 1)
        interop_pointer = key_str + type_str + length_str + pointer_str
    else:
        interop_pointer = b""
    if first_is:
        pointer_value = (TIFF_HEADER_LENGTH + zeroth_length +
                         exif_length + gps_length + interop_length)
        first_ifd_pointer = struct.pack(">L", pointer_value)
        thumbnail_pointer = (pointer_value + len(first_set[0]) + 24 +
                             4 + len(first_set[1]))
        thumbnail_p_bytes = (b"\x02\x01\x00\x04\x00\x00\x00\x01" +
                             struct.pack(">L", thumbnail_pointer))
        thumbnail_length_bytes = (b"\x02\x02\x00\x04\x00\x00\x00\x01" +
                                  struct.pack(">L", len(thumbnail)))
        first_bytes = (first_set[0] + thumbnail_p_bytes +
                       thumbnail_length_bytes + b"\x00\x00\x00\x00" +
                       first_set[1] + thumbnail)
    else:
        first_ifd_pointer = b"\x00\x00\x00\x00"

    zeroth_bytes = (zeroth_set[0] + exif_pointer + gps_pointer +
                    first_ifd_pointer + zeroth_set[1])
    if exif_is:
        exif_bytes = exif_set[0] + interop_pointer + exif_set[1]

    return (header + zeroth_bytes + exif_bytes + gps_bytes +
            interop_bytes + first_bytes)


def _get_thumbnail(jpeg):
    segments = split_into_segments(jpeg)
    while (b"\xff\xe0" <= segments[1][0:2] <= b"\xff\xef"):
        segments.pop(1)
    thumbnail = b"".join(segments)
    return thumbnail


def _pack_byte(*args):
    return struct.pack("B" * len(args), *args)

def _pack_signed_byte(*args):
    return struct.pack("b" * len(args), *args)

def _pack_short(*args):
    return struct.pack(">" + "H" * len(args), *args)

def _pack_signed_short(*args):
    return struct.pack(">" + "h" * len(args), *args)

def _pack_long(*args):
    return struct.pack(">" + "L" * len(args), *args)

def _pack_slong(*args):
    return struct.pack(">" + "l" * len(args), *args)

def _pack_float(*args):
    return struct.pack(">" + "f" * len(args), *args)

def _pack_double(*args):
    return struct.pack(">" + "d" * len(args), *args)


def _value_to_bytes(raw_value, value_type, offset):
    four_bytes_over = b""
    value_str = b""

    if value_type == TYPES.Byte:
        length = len(raw_value)
        if length <= 4:
            value_str = (_pack_byte(*raw_value) +
                            b"\x00" * (4 - length))
        else:
            value_str = struct.pack(">I", offset)
            four_bytes_over = _pack_byte(*raw_value)
    elif value_type == TYPES.Short:
        length = len(raw_value)
        if length <= 2:
            value_str = (_pack_short(*raw_value) +
                            b"\x00\x00" * (2 - length))
        else:
            value_str = struct.pack(">I", offset)
            four_bytes_over = _pack_short(*raw_value)
    elif value_type == TYPES.Long:
        length = len(raw_value)
        if length <= 1:
            value_str = _pack_long(*raw_value)
        else:
            value_str = struct.pack(">I", offset)
            four_bytes_over = _pack_long(*raw_value)
    elif value_type == TYPES.SLong:
        length = len(raw_value)
        if length <= 1:
            value_str = _pack_slong(*raw_value)
        else:
            value_str = struct.pack(">I", offset)
            four_bytes_over = _pack_slong(*raw_value)
    elif value_type == TYPES.Ascii:
        try:
            new_value = raw_value.encode("latin1") + b"\x00"
        except:
            try:
                new_value = raw_value + b"\x00"
            except TypeError:
                raise ValueError("Got invalid type to convert.")
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
    elif value_type == TYPES.SRational:
        if isinstance(raw_value[0], numbers.Integral):
            length = 1
            num, den = raw_value
            new_value = struct.pack(">l", num) + struct.pack(">l", den)
        elif isinstance(raw_value[0], tuple):
            length = len(raw_value)
            new_value = b""
            for n, val in enumerate(raw_value):
                num, den = val
                new_value += (struct.pack(">l", num) +
                                struct.pack(">l", den))
        value_str = struct.pack(">I", offset)
        four_bytes_over = new_value
    elif value_type == TYPES.Undefined:
        length = len(raw_value)
        if length > 4:
            value_str = struct.pack(">I", offset)
            try:
                four_bytes_over = b"" + raw_value
            except TypeError:
                raise ValueError("Got invalid type to convert.")
        else:
            try:
                value_str = raw_value + b"\x00" * (4 - length)
            except TypeError:
                raise ValueError("Got invalid type to convert.")
    elif value_type == TYPES.SByte: # Signed Byte
        length = len(raw_value)
        if length <= 4:
            value_str = (_pack_signed_byte(*raw_value) +
                            b"\x00" * (4 - length))
        else:
            value_str = struct.pack(">I", offset)
            four_bytes_over = _pack_signed_byte(*raw_value)
    elif value_type == TYPES.SShort: # Signed Short
        length = len(raw_value)
        if length <= 2:
            value_str = (_pack_signed_short(*raw_value) +
                            b"\x00\x00" * (2 - length))
        else:
            value_str = struct.pack(">I", offset)
            four_bytes_over = _pack_signed_short(*raw_value)
    elif value_type == TYPES.Float:
        length = len(raw_value)
        if length <= 1:
            value_str = _pack_float(*raw_value)
        else:
            value_str = struct.pack(">I", offset)
            four_bytes_over = _pack_float(*raw_value)
    elif value_type == TYPES.DFloat: # Double
        length = len(raw_value)
        value_str = struct.pack(">I", offset)
        four_bytes_over = _pack_double(*raw_value)

    length_str = struct.pack(">I", length)
    return length_str, value_str, four_bytes_over

def _dict_to_bytes(ifd_dict, ifd, ifd_offset):
    tag_count = len(ifd_dict)
    entry_header = struct.pack(">H", tag_count)
    if ifd in ("0th", "1st"):
        entries_length = 2 + tag_count * 12 + 4
    else:
        entries_length = 2 + tag_count * 12
    entries = b""
    values = b""

    for n, key in enumerate(sorted(ifd_dict)):
        if (ifd == "0th") and (key in (ImageIFD.ExifTag, ImageIFD.GPSTag)):
            continue
        elif (ifd == "Exif") and (key == ExifIFD.InteroperabilityTag):
            continue
        elif (ifd == "1st") and (key in (ImageIFD.JPEGInterchangeFormat, ImageIFD.JPEGInterchangeFormatLength)):
            continue

        raw_value = ifd_dict[key]
        key_str = struct.pack(">H", key)
        value_type = TAGS[ifd][key]["type"]
        type_str = struct.pack(">H", value_type)
        four_bytes_over = b""

        if isinstance(raw_value, numbers.Integral) or isinstance(raw_value, float):
            raw_value = (raw_value,)
        offset = TIFF_HEADER_LENGTH + entries_length + ifd_offset + len(values)

        try:
            length_str, value_str, four_bytes_over = _value_to_bytes(raw_value,
                                                                     value_type,
                                                                     offset)
        except ValueError:
            raise ValueError(
                '"dump" got wrong type of exif value.\n' +
                '{} in {} IFD. Got as {}.'.format(key, ifd, type(ifd_dict[key]))
            )

        entries += key_str + type_str + length_str + value_str
        values += four_bytes_over
    return (entry_header + entries, values)
