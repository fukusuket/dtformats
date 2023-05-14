# -*- coding: utf-8 -*-
"""Apple Unified Logging and _FormatIntegerAsHexadecimal8 Tracing files."""

import lz4.block

from dtformats import data_format
from dtformats import errors


class DSCRange(object):
  """Shared-Cache Strings (dsc) range.

  Attributes:
    path (str): path.
    range_offset (int): the offset of the range.
    range_sizes (int): the size of the range.
    uuid (uuid.UUID): the UUID.
    uuid_index (int): index of the UUID.
  """

  def __init__(self):
    """Initializes a Shared-Cache Strings (dsc) range."""
    super(DSCRange, self).__init__()
    self.path = None
    self.range_offset = None
    self.range_size = None
    self.uuid = None
    self.uuid_index = None


class DSCUUID(object):
  """Shared-Cache Strings (dsc) UUID.

  Attributes:
    path (str): path.
    sender_identifier (uuid.UUID): the sender identifier.
    text_offset (int): the offset of the text.
    text_sizes (int): the size of the text.
  """

  def __init__(self):
    """Initializes a Shared-Cache Strings (dsc) UUID."""
    super(DSCUUID, self).__init__()
    self.path = None
    self.sender_identifier = None
    self.text_offset = None
    self.text_size = None


class DSCFile(data_format.BinaryDataFile):
  """Shared-Cache Strings (dsc) file.

  Attributes:
    ranges (list[DSCRange]): the ranges.
    uuids (list[DSCUUID]): the UUIDs.
  """

  # Using a class constant significantly speeds up the time required to load
  # the dtFabric definition file.
  _FABRIC = data_format.BinaryDataFile.ReadDefinitionFile('aul_dsc.yaml')

  _DEBUG_INFO_FILE_HEADER = [
      ('signature', 'Signature', '_FormatStreamAsSignature'),
      ('major_format_version', 'Major format version',
       '_FormatIntegerAsDecimal'),
      ('minor_format_version', 'Minor format version',
       '_FormatIntegerAsDecimal'),
      ('number_of_ranges', 'Number of ranges', '_FormatIntegerAsDecimal'),
      ('number_of_uuids', 'Number of UUIDs', '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_RANGE_DESCRIPTOR = [
      ('data_offset', 'Data offset', '_FormatIntegerAsHexadecimal8'),
      ('range_offset', 'Range offset', '_FormatIntegerAsHexadecimal8'),
      ('range_size', 'Range size', '_FormatIntegerAsDecimal'),
      ('unknown_offset', 'Unknown offset', '_FormatIntegerAsHexadecimal8'),
      ('uuid_descriptor_index', 'UUID descriptor index',
       '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_UUID_DESCRIPTOR = [
      ('text_offset', 'Text offset', '_FormatIntegerAsHexadecimal8'),
      ('text_size', 'Text size', '_FormatIntegerAsDecimal'),
      ('sender_identifier', 'Sender identifier', '_FormatUUIDAsString'),
      ('path_offset', 'Path offset', '_FormatIntegerAsHexadecimal8')]

  def __init__(self, debug=False, output_writer=None):
    """Initializes a shared-cache strings (dsc) file.

    Args:
      debug (Optional[bool]): True if debug information should be written.
      output_writer (Optional[OutputWriter]): output writer.
    """
    super(DSCFile, self).__init__(debug=debug, output_writer=output_writer)
    self.ranges = []
    self.uuids = []

  def _FormatStreamAsSignature(self, stream):
    """Formats a stream as a signature.

    Args:
      stream (bytes): stream.

    Returns:
      str: stream formatted as a signature.
    """
    return stream.decode('ascii')

  def _ReadFileHeader(self, file_object):
    """Reads a file header.

    Args:
      file_object (file): file-like object.

    Returns:
      dsc_file_header: a file header.

    Raises:
      ParseError: if the file header cannot be read.
    """
    data_type_map = self._GetDataTypeMap('dsc_file_header')

    file_header, _ = self._ReadStructureFromFileObject(
        file_object, 0, data_type_map, 'file header')

    if self._debug:
      self._DebugPrintStructureObject(
          file_header, self._DEBUG_INFO_FILE_HEADER)

    if file_header.signature != b'hcsd':
      raise errors.ParseError('Unsupported signature.')

    format_version = (
        file_header.major_format_version, file_header.minor_format_version)
    if format_version not in [(1, 0), (2, 0)]:
      format_version_string = '.'.join([
          f'{file_header.major_format_version:d}',
          f'{file_header.minor_format_version:d}'])
      raise errors.ParseError(
          f'Unsupported format version: {format_version_string:s}')

    return file_header

  def _ReadRangeDescriptors(
      self, file_object, file_offset, version, number_of_ranges):
    """Reads the range descriptors.

    Args:
      file_object (file): file-like object.
      file_offset (int): offset of the start of range descriptors data relative
          to the start of the file.
      version (int): major version of the file.
      number_of_ranges (int): the number of range descriptions to retrieve.

    Yields:
      DSCRange: a range.

    Raises:
      ParseError: if the file cannot be read.
    """
    if version not in (1, 2):
      raise errors.ParseError(f'Unsupported format version: {version:d}.')

    if version == 1:
      data_type_map_name = 'dsc_range_descriptor_v1'
      description = 'range descriptor v1'
    else:
      data_type_map_name = 'dsc_range_descriptor_v2'
      description = 'range descriptor v2'

    data_type_map = self._GetDataTypeMap(data_type_map_name)

    for _ in range(number_of_ranges):
      range_descriptor, record_size = self._ReadStructureFromFileObject(
          file_object, file_offset, data_type_map, description)

      file_offset += record_size

      if self._debug:
        self._DebugPrintStructureObject(
            range_descriptor, self._DEBUG_INFO_RANGE_DESCRIPTOR)

      dsc_range = DSCRange()
      dsc_range.range_offset = range_descriptor.range_offset
      dsc_range.range_size = range_descriptor.range_size
      dsc_range.uuid_index = range_descriptor.uuid_descriptor_index
      yield dsc_range

  def _ReadUUIDDescriptors(
      self, file_object, file_offset, version, number_of_uuids):
    """Reads the UUID descriptors.

    Args:
      file_object (file): file-like object.
      file_offset (int): offset of the start of UUID descriptors data relative
          to the start of the file.
      version (int): major version of the file
      number_of_uuids (int): the number of UUID descriptions to retrieve.

    Yields:
      DSCUUId: an UUID.

    Raises:
      ParseError: if the file cannot be read.
    """
    if version not in (1, 2):
      raise errors.ParseError(f'Unsupported format version: {version:d}.')

    if version == 1:
      data_type_map_name = 'dsc_uuid_descriptor_v1'
      description = 'UUID descriptor v1'
    else:
      data_type_map_name = 'dsc_uuid_descriptor_v2'
      description = 'UUID descriptor v2'

    data_type_map = self._GetDataTypeMap(data_type_map_name)

    for _ in range(number_of_uuids):
      uuid_descriptor, record_size = self._ReadStructureFromFileObject(
          file_object, file_offset, data_type_map, description)

      file_offset += record_size

      if self._debug:
        self._DebugPrintStructureObject(
            uuid_descriptor, self._DEBUG_INFO_UUID_DESCRIPTOR)

      dsc_uuid = DSCUUID()
      dsc_uuid.sender_identifier = uuid_descriptor.sender_identifier
      dsc_uuid.text_offset = uuid_descriptor.text_offset
      dsc_uuid.text_size = uuid_descriptor.text_size

      dsc_uuid.path = self._ReadUUIDPath(
          file_object, uuid_descriptor.path_offset)

      yield dsc_uuid

  def _ReadUUIDPath(self, file_object, file_offset):
    """Reads an UUID path.

    Args:
      file_object (file): file-like object.
      file_offset (int): offset of the UUID path data relative to the start of
          the file.

    Returns:
      str: UUID path.

    Raises:
      ParseError: if the file cannot be read.
    """
    data_type_map = self._GetDataTypeMap('cstring')

    uuid_path, _ = self._ReadStructureFromFileObject(
        file_object, file_offset, data_type_map, 'UUID path')

    if self._debug:
      self._DebugPrintValue('UUID path', uuid_path)

    return uuid_path

  def ReadFileObject(self, file_object):
    """Reads a shared-cache strings (dsc) file-like object.

    Args:
      file_object (file): file-like object.

    Raises:
      ParseError: if the file cannot be read.
    """
    file_header = self._ReadFileHeader(file_object)

    file_offset = file_object.tell()

    self.ranges = list(self._ReadRangeDescriptors(
        file_object, file_offset, file_header.major_format_version,
        file_header.number_of_ranges))

    file_offset = file_object.tell()

    self.uuids = list(self._ReadUUIDDescriptors(
        file_object, file_offset, file_header.major_format_version,
        file_header.number_of_uuids))

    for dsc_range in self.ranges:
      dsc_uuid = self.uuids[dsc_range.uuid_index]

      dsc_range.path = dsc_uuid.path
      dsc_range.uuid = dsc_uuid.sender_identifier


class TimesyncDatabaseFile(data_format.BinaryDataFile):
  """Timesync database file."""

  # Using a class constant significantly speeds up the time required to load
  # the dtFabric definition file.
  _FABRIC = data_format.BinaryDataFile.ReadDefinitionFile('aul_timesync.yaml')

  _BOOT_RECORD_SIGNATURE = b'\xb0\xbb'
  _SYNC_RECORD_SIGNATURE = b'Ts'

  _DEBUG_INFO_BOOT_RECORD = [
      ('signature', 'Signature', '_FormatStreamAsSignature'),
      ('record_size', 'Record size', '_FormatIntegerAsDecimal'),
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal'),
      ('boot_identifier', 'Boot identifier', '_FormatUUIDAsString'),
      ('timebase_numerator', 'Timebase numerator',
       '_FormatIntegerAsHexadecimal'),
      ('timebase_denominator', 'Timebase denominator',
       '_FormatIntegerAsHexadecimal'),
      ('timestamp', 'Timestamp', '_FormatIntegerAsPosixTimeInNanoseconds'),
      ('time_zone_offset', 'Time zone offset', '_FormatIntegerAsDecimal'),
      ('daylight_saving_flag', 'Daylight saving flag',
       '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_SYNC_RECORD = [
      ('signature', 'Signature', '_FormatStreamAsSignature'),
      ('record_size', 'Record size', '_FormatIntegerAsDecimal'),
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal'),
      ('kernel_time', 'Kernel Time', '_FormatIntegerAsDecimal'),
      ('timestamp', 'Timestamp', '_FormatIntegerAsPosixTimeInNanoseconds'),
      ('time_zone_offset', 'Time zone offset', '_FormatIntegerAsDecimal'),
      ('daylight_saving_flag', 'Daylight saving flag',
       '_FormatIntegerAsDecimal')]

  def __init__(self, debug=False, output_writer=None):
    """Initializes a timesync database file.

    Args:
      debug (Optional[bool]): True if debug information should be written.
      output_writer (Optional[OutputWriter]): output writer.
    """
    super(TimesyncDatabaseFile, self).__init__(
        debug=debug, output_writer=output_writer)
    self._boot_record_data_type_map = self._GetDataTypeMap(
        'timesync_boot_record')
    self._sync_record_data_type_map = self._GetDataTypeMap(
        'timesync_sync_record')

  def _ReadRecord(self, file_object, file_offset):
    """Reads a boot or sync record.

    Args:
      file_object (file): file-like object.
      file_offset (int): offset of the start of the record relative to the start
          of the file.

    Returns:
      tuple[object, int]: boot or sync record and number of bytes read.

    Raises:
      ParseError: if the file cannot be read.
    """
    signature = self._ReadData(file_object, file_offset, 2, 'signature')

    if signature == self._BOOT_RECORD_SIGNATURE:
      data_type_map = self._boot_record_data_type_map
      description = 'boot record'
      debug_info = self._DEBUG_INFO_BOOT_RECORD

    elif signature == self._SYNC_RECORD_SIGNATURE:
      data_type_map = self._sync_record_data_type_map
      description = 'sync record'
      debug_info = self._DEBUG_INFO_SYNC_RECORD

    else:
      signature = repr(signature)
      raise errors.ParseError(f'Unsupported signature: {signature:s}.')

    record, bytes_read = self._ReadStructureFromFileObject(
        file_object, file_offset, data_type_map, description)

    if self._debug:
      self._DebugPrintStructureObject(record, debug_info)

    return record, bytes_read

  def ReadFileObject(self, file_object):
    """Reads a timesync file-like object.

    Args:
      file_object (file): file-like object.

    Raises:
      ParseError: if the file cannot be read.
    """
    file_offset = 0

    while file_offset < self._file_size:
      record, _ = self._ReadRecord(file_object, file_offset)
      file_offset += record.record_size


class TraceV3File(data_format.BinaryDataFile):
  """Apple Unified Logging and Activity Tracing (tracev3) file."""

  # Using a class constant significantly speeds up the time required to load
  # the dtFabric definition file.
  _FABRIC = data_format.BinaryDataFile.ReadDefinitionFile('aul_tracev3.yaml')

  _CHUNK_TAG_HEADER = 0x00001000
  _CHUNK_TAG_FIREHOSE = 0x00006001
  _CHUNK_TAG_OVERSIZE = 0x00006002
  _CHUNK_TAG_STATEDUMP = 0x00006003
  _CHUNK_TAG_SIMPLEDUMP = 0x00006004
  _CHUNK_TAG_CATALOG = 0x0000600b
  _CHUNK_TAG_CHUNK_SET = 0x0000600d

  _CHUNK_TAG_DESCRIPTIONS = {
      0x00001000: 'Header',
      0x00006001: 'Firehose',
      0x00006002: 'Oversize',
      0x00006003: 'StateDump',
      0x00006004: 'SimpleDump',
      0x0000600b: 'Catalog',
      0x0000600d: 'ChunkSet'}

  _DEBUG_INFO_CATALOG = [
      ('sub_system_strings_offset', 'Sub system strings offset',
       '_FormatIntegerAsHexadecimal8'),
      ('process_information_entries_offset',
       'Process information entries offset', '_FormatIntegerAsHexadecimal8'),
      ('number_of_process_information_entries',
       'Number of process information entries', '_FormatIntegerAsDecimal'),
      ('sub_chunks_offset', 'Sub chunks offset',
       '_FormatIntegerAsHexadecimal8'),
      ('number_of_sub_chunks', 'Number of sub chunks',
       '_FormatIntegerAsDecimal'),
      ('unknown1', 'Unknown1', '_FormatDataInHexadecimal'),
      ('earliest_firehose_timestamp', 'Earliest firehose timestamp',
       '_FormatIntegerAsDecimal'),
      ('uuids', 'UUIDs', '_FormatArrayOfUUIDS'),
      ('sub_system_strings', 'Sub system strings', '_FormatArrayOfStrings')]

  _DEBUG_INFO_CATALOG_PROCESS_INFORMATION_ENTRY = [
      ('entry_index', 'Entry index', '_FormatIntegerAsDecimal'),
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal4'),
      ('main_uuid_index', 'Main UUID index', '_FormatIntegerAsDecimal'),
      ('dsc_uuid_index', 'DSC UUID index', '_FormatIntegerAsDecimal'),
      ('proc_id_upper', 'proc_id (upper 64-bit)', '_FormatIntegerAsDecimal'),
      ('proc_id_lower', 'proc_id (lower 32-bit)', '_FormatIntegerAsDecimal'),
      ('process_identifier', 'process identifier (pid)',
       '_FormatIntegerAsDecimal'),
      ('effective_user_identifier', 'Effective user identifier (euid)',
       '_FormatIntegerAsDecimal'),
      ('unknown2', 'Unknown2', '_FormatIntegerAsHexadecimal4'),
      ('number_of_uuid_entries', 'Number of UUID information entries',
       '_FormatIntegerAsDecimal'),
      ('unknown3', 'Unknown3', '_FormatIntegerAsHexadecimal4'),
      ('uuid_entries', 'UUID entries', '_FormatArrayOfCatalogUUIDEntries'),
      ('number_of_sub_system_entries', 'Number of sub system entries',
       '_FormatIntegerAsDecimal'),
      ('unknown4', 'Unknown4', '_FormatIntegerAsHexadecimal4'),
      ('sub_system_entries', 'Sub system entries',
       '_FormatArrayOfCatalogSubSystemEntries'),
      ('alignment_padding', 'Alignment padding', '_FormatDataInHexadecimal')]

  _DEBUG_INFO_CHUNK_HEADER = [
      ('chunk_tag', 'Chunk tag', '_FormatChunkTag'),
      ('chunk_sub_tag', 'Chunk sub tag', '_FormatIntegerAsHexadecimal8'),
      ('chunk_data_size', 'Chunk data size', '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_FIREHOSE_HEADER = [
      ('proc_id_upper', 'proc_id (upper 64-bit)', '_FormatIntegerAsDecimal'),
      ('proc_id_lower', 'proc_id (lower 32-bit)', '_FormatIntegerAsDecimal'),
      ('ttl', 'Time to live (TTL)', '_FormatIntegerAsDecimal'),
      ('collapsed', 'Collapsed', '_FormatIntegerAsDecimal'),
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal4'),
      ('public_data_size', 'Public data size', '_FormatIntegerAsDecimal'),
      ('private_data_virtual_offset', 'Private data virtual offset',
       '_FormatIntegerAsHexadecimal4'),
      ('unknown2', 'Unknown2', '_FormatIntegerAsHexadecimal4'),
      ('unknown3', 'Unknown3', '_FormatIntegerAsHexadecimal4'),
      ('base_continuous_time', 'Base continuous time',
       '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_FIREHOSE_TRACEPOINT = [
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal2'),
      ('unknown2', 'Unknown2', '_FormatIntegerAsHexadecimal2'),
      ('unknown3', 'Unknown3', '_FormatIntegerAsHexadecimal4'),
      ('format_string_location', 'Format string location',
       '_FormatIntegerAsHexadecimal8'),
      ('thread_identifier', 'Thread identifier', '_FormatIntegerAsDecimal'),
      ('continuous_time_lower', 'Continous time (lower 32-bit)',
       '_FormatIntegerAsDecimal'),
      ('continuous_time_upper', 'Continous time (upper 16-bit)',
       '_FormatIntegerAsDecimal'),
      ('data_size', 'Data size', '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_HEADER = [
      ('timebase_numerator', 'Timebase numerator', '_FormatIntegerAsDecimal'),
      ('timebase_denominator', 'Timebase denominator',
       '_FormatIntegerAsDecimal'),
      ('continuous_time', 'Continuous time', '_FormatIntegerAsDecimal'),
      ('unknown_time', 'Unknown time', 'FormatIntegerAsPosixTime'),
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal4'),
      ('unknown2', 'Unknown2', '_FormatIntegerAsHexadecimal4'),
      ('time_zone_offset', 'Time zone offset', '_FormatIntegerAsDecimal'),
      ('daylight_savings_flag', 'Daylight Savings Flag',
       '_FormatIntegerAsDecimal'),
      ('unknown_flags', 'Unknown flags', '_FormatIntegerAsHexadecimal4')]

  _DEBUG_INFO_HEADER_CONTINOUS_TIME_SUB_CHUNK = [
      ('sub_chunk_tag', 'Sub chunk tag', '_FormatIntegerAsHexadecimal4'),
      ('sub_chunk_data_size', 'Sub chunk data size', '_FormatIntegerAsDecimal'),
      ('continuous_time', 'Continuous time', '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_HEADER_SYSTEM_INFORMATION_SUB_CHUNK = [
      ('sub_chunk_tag', 'Sub chunk tag', '_FormatIntegerAsHexadecimal4'),
      ('sub_chunk_data_size', 'Sub chunk data size', '_FormatIntegerAsDecimal'),
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal4'),
      ('unknown2', 'Unknown2', '_FormatIntegerAsHexadecimal4'),
      ('build_version', 'Build version', '_FormatString'),
      ('hardware_model', 'Hardware model', '_FormatString')]

  _DEBUG_INFO_HEADER_GENERATION_SUB_CHUNK = [
      ('sub_chunk_tag', 'Sub chunk tag', '_FormatIntegerAsHexadecimal4'),
      ('sub_chunk_data_size', 'Sub chunk data size', '_FormatIntegerAsDecimal'),
      ('boot_identifier', 'Boot identifier', '_FormatUUIDAsString'),
      ('logd_process_identifier', 'logd process identifier (pid)',
       '_FormatIntegerAsDecimal'),
      ('logd_exit_status', 'logd exit status', '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_HEADER_TIME_ZONE_SUB_CHUNK = [
      ('sub_chunk_tag', 'Sub chunk tag', '_FormatIntegerAsHexadecimal4'),
      ('sub_chunk_data_size', 'Sub chunk data size', '_FormatIntegerAsDecimal'),
      ('path', 'Path', '_FormatString')]

  _DEBUG_INFO_LZ4_BLOCK_HEADER = [
      ('signature', 'Signature', '_FormatStreamAsSignature'),
      ('uncompressed_data_size', 'Uncompressed data size',
       '_FormatIntegerAsDecimal'),
      ('compressed_data_size', 'Compressed data size',
       '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_OVERSIZE_CHUNK = [
      ('proc_id_upper', 'proc_id (upper 64-bit)', '_FormatIntegerAsDecimal'),
      ('proc_id_lower', 'proc_id (lower 32-bit)', '_FormatIntegerAsDecimal'),
      ('ttl', 'Time to live (TTL)', '_FormatIntegerAsDecimal'),
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal2'),
      ('unknown2', 'Unknown2', '_FormatIntegerAsHexadecimal4'),
      ('continuous_time', 'Continuous time', '_FormatIntegerAsDecimal'),
      ('data_reference_index', 'Data reference index',
       '_FormatIntegerAsDecimal'),
      ('data_size', 'Data Size', '_FormatIntegerAsDecimal')]

  _DEBUG_INFO_SIMPLEDUMP_CHUNK = [
      ('proc_id_upper', 'proc_id (upper 64-bit)', '_FormatIntegerAsDecimal'),
      ('proc_id_lower', 'proc_id (lower 32-bit)', '_FormatIntegerAsDecimal'),
      ('ttl', 'Time to live (TTL)', '_FormatIntegerAsDecimal'),
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal2'),
      ('unknown2', 'Unknown2', '_FormatIntegerAsHexadecimal4'),
      ('continuous_time', 'Continuous time', '_FormatIntegerAsDecimal'),
      ('thread_identifier', 'Thread identifier', '_FormatIntegerAsDecimal'),
      ('unknown3', 'Unknown3', '_FormatIntegerAsHexadecimal8'),
      ('unknown4', 'Unknown4', '_FormatIntegerAsHexadecimal4'),
      ('unknown5', 'Unknown5', '_FormatIntegerAsHexadecimal4'),
      ('sender_identifier', 'Sender identifier', '_FormatUUIDAsString'),
      ('dsc_identifier', 'DSC identifier', '_FormatUUIDAsString'),
      ('unknown6', 'Unknown6', '_FormatIntegerAsHexadecimal8'),
      ('sub_system_string_size', 'Sub system string size',
       '_FormatIntegerAsDecimal'),
      ('message_string_size', 'Message string size', '_FormatIntegerAsDecimal'),
      ('sub_system_string', 'Sub system string', '_FormatString'),
      ('message_string', 'Message string', '_FormatString')]

  _DEBUG_INFO_STATEDUMP_CHUNK = [
      ('proc_id_upper', 'proc_id (upper 64-bit)', '_FormatIntegerAsDecimal'),
      ('proc_id_lower', 'proc_id (lower 32-bit)', '_FormatIntegerAsDecimal'),
      ('ttl', 'Time to live (TTL)', '_FormatIntegerAsDecimal'),
      ('unknown1', 'Unknown1', '_FormatIntegerAsHexadecimal2'),
      ('unknown2', 'Unknown2', '_FormatIntegerAsHexadecimal4'),
      ('continuous_time', 'Continuous time', '_FormatIntegerAsDecimal'),
      ('activity_identifier', 'Activity identifier',
       '_FormatIntegerAsHexadecimal8'),
      ('unknown3', 'Unknown3', '_FormatUUIDAsString'),
      ('data_type', 'Data type', '_FormatIntegerAsDecimal'),
      ('data_size', 'Data size', '_FormatIntegerAsDecimal'),
      ('unknown4', 'Unknown4', '_FormatDataInHexadecimal'),
      ('unknown5', 'Unknown5', '_FormatDataInHexadecimal'),
      ('name', 'Name', '_FormatString'),
      ('data', 'Data', '_FormatDataInHexadecimal')]

  def __init__(self, debug=False, output_writer=None):
    """Initializes a tracev3 file.

    Args:
      debug (Optional[bool]): True if debug information should be written.
      output_writer (Optional[OutputWriter]): output writer.
    """
    super(TraceV3File, self).__init__(debug=debug, output_writer=output_writer)

  def _FormatChunkTag(self, integer):
    """Formats a chunk tag.

    Args:
      integer (int): integer.

    Returns:
      str: integer formatted as chunk tag.
    """
    description = self._CHUNK_TAG_DESCRIPTIONS.get(integer, None)
    if description:
      return f'0x{integer:08x} ({description:s})'

    return f'0x{integer:08x}'

  def _FormatArrayOfStrings(self, array_of_strings):
    """Formats an array of strings.

    Args:
      array_of_strings (list[str]): array of strings.

    Returns:
      str: formatted array of strings.
    """
    value = '\n'.join([
        f'\t[{string_index:03d}] {string:s}'
        for string_index, string in enumerate(array_of_strings)])
    return f'{value:s}\n'

  def _FormatArrayOfCatalogSubSystemEntries(self, array_of_entries):
    """Formats an array of catalog sub system entries.

    Args:
      array_of_entries (list[tracev3_catalog_uuid_entry]): array of catalog sub
          system entries.

    Returns:
      str: formatted array of catalog sub system entries.
    """
    value = '\n'.join([
        (f'\tidentifier: {entry.identifier:d}, '
         f'sub_system_offset: {entry.sub_system_offset:d}, '
         f'category_offset: {entry.category_offset:d}')
        for entry in array_of_entries])
    return f'{value:s}\n'

  def _FormatArrayOfCatalogUUIDEntries(self, array_of_entries):
    """Formats an array of catalog UUID entries.

    Args:
      array_of_entries (list[tracev3_catalog_uuid_entry]): array of catalog
          UUID entries.

    Returns:
      str: formatted array of catalog UUID entries.
    """
    value = '\n'.join([
        (f'\tsize: {entry.size:d}, unknown1: 0x{entry.unknown1:x}, '
         f'offset: {entry.offset:d}, reference: {entry.reference:d}')
        for entry in array_of_entries])
    return f'{value:s}\n'

  def _FormatArrayOfUUIDS(self, array_of_uuids):
    """Formats an array of UUIDs.

    Args:
      array_of_uuids (list[uuid]): array of UUIDs.

    Returns:
      str: formatted array of UUIDs.
    """
    value = '\n'.join([
        f'\t[{uuid_index:03d}] {uuid!s}'
        for uuid_index, uuid in enumerate(array_of_uuids)])
    return f'{value:s}\n'

  def _FormatStreamAsSignature(self, stream):
    """Formats a stream as a signature.

    Args:
      stream (bytes): stream.

    Returns:
      str: stream formatted as a signature.
    """
    return stream.decode('ascii')

  def _ReadCatalog(self, file_object, file_offset, chunk_header):
    """Reads a catalog.

    Args:
      file_object (file): file-like object.
      file_offset (int): offset of the catalog data relative to the start
          of the file.
      chunk_header (tracev3_chunk_header): the chunk header of the catalog.

    Raises:
      ParseError: if the chunk header cannot be read.
    """
    if self._debug:
      chunk_data = file_object.read(chunk_header.chunk_data_size)
      self._DebugPrintData('Catalog chunk data', chunk_data)

    data_type_map = self._GetDataTypeMap('tracev3_catalog')

    catalog, bytes_read = self._ReadStructureFromFileObject(
        file_object, file_offset, data_type_map, 'Catalog')

    file_offset += bytes_read

    if self._debug:
      self._DebugPrintStructureObject(catalog, self._DEBUG_INFO_CATALOG)

    data_type_map = self._GetDataTypeMap(
        'tracev3_catalog_process_information_entry')

    for entry_index in range(catalog.number_of_process_information_entries):
      process_information_entry, bytes_read = self._ReadStructureFromFileObject(
          file_object, file_offset, data_type_map,
          f'Catalog process information entry: {entry_index:d}')

      file_offset += bytes_read

      if self._debug:
        self._DebugPrintStructureObject(
            process_information_entry,
            self._DEBUG_INFO_CATALOG_PROCESS_INFORMATION_ENTRY)

  def _ReadChunkHeader(self, file_object, file_offset):
    """Reads a chunk header.

    Args:
      file_object (file): file-like object.
      file_offset (int): offset of the chunk header relative to the start
          of the file.

    Returns:
      tracev3_chunk_header: a chunk header.

    Raises:
      ParseError: if the chunk header cannot be read.
    """
    data_type_map = self._GetDataTypeMap('tracev3_chunk_header')

    chunk_header, _ = self._ReadStructureFromFileObject(
        file_object, file_offset, data_type_map, 'chunk header')

    if self._debug:
      self._DebugPrintStructureObject(
          chunk_header, self._DEBUG_INFO_CHUNK_HEADER)

    return chunk_header

  def _ReadChunkSet(self, file_object, file_offset, chunk_header):
    """Reads a chunk set.

    Args:
      file_object (file): file-like object.
      file_offset (int): offset of the chunk set data relative to the start
          of the file.
      chunk_header (tracev3_chunk_header): the chunk header of the chunk set.

    Raises:
      ParseError: if the chunk header cannot be read.
    """
    chunk_data = file_object.read(chunk_header.chunk_data_size)

    data_type_map = self._GetDataTypeMap('tracev3_lz4_block_header')

    lz4_block_header, _ = self._ReadStructureFromFileObject(
        file_object, file_offset, data_type_map, 'LZ4 block header')

    if self._debug:
      self._DebugPrintStructureObject(
          lz4_block_header, self._DEBUG_INFO_LZ4_BLOCK_HEADER)

    end_of_compressed_data_offset = 12 + lz4_block_header.compressed_data_size

    if lz4_block_header.signature == b'bv41':
      uncompressed_data = lz4.block.decompress(
          chunk_data[12:end_of_compressed_data_offset],
          uncompressed_size=lz4_block_header.uncompressed_data_size)

    elif lz4_block_header.signature == b'bv4-':
      uncompressed_data = chunk_data[12:end_of_compressed_data_offset]

    else:
      raise errors.ParseError('Unsupported start of compressed data marker')

    end_of_compressed_data_identifier = chunk_data[
        end_of_compressed_data_offset:end_of_compressed_data_offset + 4]

    if end_of_compressed_data_identifier != b'bv4$':
      raise errors.ParseError('Unsupported end of compressed data marker')

    data_type_map = self._GetDataTypeMap('tracev3_chunk_header')

    data_offset = 0
    while data_offset < lz4_block_header.uncompressed_data_size:
      if self._debug:
        self._DebugPrintData('Chunk header data', uncompressed_data[
            data_offset:data_offset + 16])

      chunkset_chunk_header = self._ReadStructureFromByteStream(
          uncompressed_data[data_offset:], data_offset, data_type_map,
          'chunk header')
      data_offset += 16

      if self._debug:
        self._DebugPrintStructureObject(
            chunkset_chunk_header, self._DEBUG_INFO_CHUNK_HEADER)

      data_end_offset = data_offset + chunkset_chunk_header.chunk_data_size
      chunkset_chunk_data = uncompressed_data[data_offset:data_end_offset]
      if self._debug:
        self._DebugPrintData('Chunk data', chunkset_chunk_data)

      if chunkset_chunk_header.chunk_tag == self._CHUNK_TAG_FIREHOSE:
        self._ReadFirehoseChunkData(
            chunkset_chunk_data, chunkset_chunk_header.chunk_data_size,
            data_offset)

      elif chunkset_chunk_header.chunk_tag == self._CHUNK_TAG_OVERSIZE:
        self._ReadOversizeChunkData(
            chunkset_chunk_data, chunkset_chunk_header.chunk_data_size,
            data_offset)

      elif chunkset_chunk_header.chunk_tag == self._CHUNK_TAG_STATEDUMP:
        self._ReadStateDumpChunkData(
            chunkset_chunk_data, chunkset_chunk_header.chunk_data_size,
            data_offset)

      elif chunkset_chunk_header.chunk_tag == self._CHUNK_TAG_SIMPLEDUMP:
        self._ReadSimpleDumpChunkData(
            chunkset_chunk_data, chunkset_chunk_header.chunk_data_size,
            data_offset)

      data_offset = data_end_offset

      _, alignment = divmod(data_offset, 8)
      if alignment > 0:
        alignment = 8 - alignment

      data_offset += alignment

  def _ReadFirehoseChunkData(self, chunk_data, chunk_data_size, data_offset):
    """Reads firehose chunk data.

    Args:
      chunk_data (bytes): firehose chunk data.
      chunk_data_size (int): size of the firehose chunk data.
      data_offset (int): offset of the firehose chunk relative to the start
          of the chunk set.

    Returns:
      Tracev3FirehoseData: Firehose data

    Raises:
      ParseError: if the firehose chunk cannot be read.
    """
    data_type_map = self._GetDataTypeMap('tracev3_firehose_header')

    firehose_header = self._ReadStructureFromByteStream(
        chunk_data, data_offset, data_type_map, 'firehose header')

    if self._debug:
      self._DebugPrintStructureObject(
          firehose_header, self._DEBUG_INFO_FIREHOSE_HEADER)

    firehose_object = Tracev3FirehoseData()
    firehose_object.CopyFromFirehoseHeader(firehose_header)

    chunk_data_offset = 32
    while chunk_data_offset < chunk_data_size:
      firehose_tracepoint = self._ReadFirehoseTracepointData(
          chunk_data[chunk_data_offset:], data_offset + chunk_data_offset)

      test_data_offset = chunk_data_offset + 24
      test_data_end_offset = test_data_offset + firehose_tracepoint.data_size
      self._DebugPrintData(
          'Data', chunk_data[test_data_offset:test_data_end_offset])

      chunk_data_offset += 24 + firehose_tracepoint.data_size

      _, alignment = divmod(chunk_data_offset, 8)
      if alignment > 0:
        alignment = 8 - alignment

      chunk_data_offset += alignment

      firehose_object.firehose_tracepoints.append(firehose_tracepoint)

    return firehose_object

  def _ReadFirehoseTracepointData(self, tracepoint_data, data_offset):
    """Reads firehose tracepoint data.

    Args:
      tracepoint_data (bytes): firehose tracepoint data.
      data_offset (int): offset of the firehose tracepoint relative to
          the start of the chunk set.

    Returns:
      Tracev3FirehoseTracepoint: a firehose tracepoint.

    Raises:
      ParseError: if the firehose tracepoint cannot be read.
    """
    data_type_map = self._GetDataTypeMap('tracev3_firehose_tracepoint')

    firehose_tracepoint = self._ReadStructureFromByteStream(
        tracepoint_data, data_offset, data_type_map, 'firehose tracepoint')

    if self._debug:
      self._DebugPrintStructureObject(
          firehose_tracepoint, self._DEBUG_INFO_FIREHOSE_TRACEPOINT)

    tracepoint_object = Tracev3FirehoseTracepoint()
    tracepoint_object.CopyFromFirehostTracepoint(firehose_tracepoint)

    # TODO populate the data and parse it based on the type of tracepoint

    return tracepoint_object

  def _ReadHeaderChunk(self, file_object, file_offset):
    """Reads a header chunk.

    Args:
       file_object (file): file-like object.
       file_offset (int): offset of the chunk relative to the start of the file.

    Returns:
      header_chunk: a header chunk.

    Raises:
      ParseError: if the header chunk cannot be read.
    """
    data_type_map = self._GetDataTypeMap('tracev3_header_chunk')

    header_chunk, _ = self._ReadStructureFromFileObject(
        file_object, file_offset, data_type_map, 'header chunk')

    if self._debug:
      self._DebugPrintStructureObject(
          header_chunk, self._DEBUG_INFO_HEADER)
      self._DebugPrintStructureObject(
          header_chunk.continuous,
          self._DEBUG_INFO_HEADER_CONTINOUS_TIME_SUB_CHUNK)
      self._DebugPrintStructureObject(
          header_chunk.system_information,
          self._DEBUG_INFO_HEADER_SYSTEM_INFORMATION_SUB_CHUNK)
      self._DebugPrintStructureObject(
          header_chunk.generation, self._DEBUG_INFO_HEADER_GENERATION_SUB_CHUNK)
      self._DebugPrintStructureObject(
          header_chunk.time_zone, self._DEBUG_INFO_HEADER_TIME_ZONE_SUB_CHUNK)

    return header_chunk

  def _ReadOversizeChunkData(self, chunk_data, chunk_data_size, data_offset):
    """Reads Oversize chunk data.

    Args:
      chunk_data (bytes): Oversize chunk data.
      chunk_data_size (int): size of the Oversize chunk data.
      data_offset (int): offset of the Oversize chunk relative to the start
          of the chunk set.

    Returns:
      oversize_chunk: an Oversize chunk.

    Raises:
      ParseError: if the chunk cannot be read.
    """
    data_type_map = self._GetDataTypeMap('tracev3_oversize_chunk')

    oversize_chunk = self._ReadStructureFromByteStream(
        chunk_data, data_offset, data_type_map, 'Oversize chunk')

    if self._debug:
      self._DebugPrintStructureObject(
          oversize_chunk, self._DEBUG_INFO_OVERSIZE_CHUNK)

    # TODO: check for trailing data.
    _ = chunk_data_size

    return oversize_chunk

  def _ReadSimpleDumpChunkData(self, chunk_data, chunk_data_size, data_offset):
    """Reads SimpleDump chunk data.

    Args:
      chunk_data (bytes): SimpleDump chunk data.
      chunk_data_size (int): size of the SimpleDump chunk data.
      data_offset (int): offset of the SimpleDump chunk relative to the start
          of the chunk set.

    Returns:
      simpledump_chunk: a SimpleDump chunk.

    Raises:
      ParseError: if the chunk cannot be read.
    """
    data_type_map = self._GetDataTypeMap('tracev3_simpledump_chunk')

    simpledump_chunk = self._ReadStructureFromByteStream(
        chunk_data, data_offset, data_type_map, 'SimpleDump chunk')

    if self._debug:
      self._DebugPrintStructureObject(
          simpledump_chunk, self._DEBUG_INFO_SIMPLEDUMP_CHUNK)

    # TODO: check for trailing data.
    _ = chunk_data_size

    return simpledump_chunk

  def _ReadStateDumpChunkData(self, chunk_data, chunk_data_size, data_offset):
    """Reads StateDump chunk data.

    Args:
      chunk_data (bytes): StateDump chunk data.
      chunk_data_size (int): size of the StateDump chunk data.
      data_offset (int): offset of the StateDump chunk relative to the start
          of the chunk set.

    Returns:
      statedump_chunk: a StateDump chunk.

    Raises:
      ParseError: if the chunk cannot be read.
    """
    data_type_map = self._GetDataTypeMap('tracev3_statedump_chunk')

    statedump_chunk = self._ReadStructureFromByteStream(
        chunk_data, data_offset, data_type_map, 'StateDump chunk')

    if self._debug:
      self._DebugPrintStructureObject(
          statedump_chunk, self._DEBUG_INFO_STATEDUMP_CHUNK)

    # TODO: check for trailing data.
    _ = chunk_data_size

    return statedump_chunk

  def ReadFileObject(self, file_object):
    """Reads a tracev3 file-like object.

    Args:
      file_object (file): file-like object.

    Raises:
      ParseError: if the file cannot be read.
    """
    file_offset = 0

    while file_offset < self._file_size:
      chunk_header = self._ReadChunkHeader(file_object, file_offset)
      file_offset += 16

      if chunk_header.chunk_tag == self._CHUNK_TAG_HEADER:
        self._ReadHeaderChunk(file_object, file_offset)

      elif chunk_header.chunk_tag == self._CHUNK_TAG_CATALOG:
        self._ReadCatalog(file_object, file_offset, chunk_header)

      elif chunk_header.chunk_tag == self._CHUNK_TAG_CHUNK_SET:
        self._ReadChunkSet(file_object, file_offset, chunk_header)

      file_offset += chunk_header.chunk_data_size

      _, alignment = divmod(file_offset, 8)
      if alignment > 0:
        alignment = 8 - alignment

      file_offset += alignment


class Tracev3FirehoseData(object):
  """TraceV3 firehose data.

  Attributes:
    base_continuous_time (int): base continuous time for events in the firehose
        chunk
    firehose_tracepoints (list[Tracev3FirehoseTracepoint]): firehose
        tracepoints.
    private_data_virtual_offset (int): private data virtual offset.
    proc_id_lower (int): second number in "proc_id #@#".
    proc_id_upper (int): first number in "proc_id #@#".
    public_data_size (int): size of the Firehose data block.
  """

  def __init__(self):
    """Initializes a Firehose data block."""
    super(Tracev3FirehoseData, self).__init__()
    self.base_continuous_time = None
    self.firehose_tracepoints = []
    self.private_data_virtual_offset = None
    self.proc_id_lower = None
    self.proc_id_upper = None
    self.public_data_size = None

  def CopyFromFirehoseHeader(self, header):
    """Copies attributes a firehose header.

    Args:
      header (firehose_header): a firehose header.
    """
    self.base_continuous_time = header.base_continuous_time
    self.private_data_virtual_offset = header.private_data_virtual_offset
    self.proc_id_lower = header.proc_id_lower
    self.proc_id_upper = header.proc_id_upper
    self.public_data_size = header.public_data_size


class Tracev3FirehoseTracepoint(object):
  """TraceV3 firehose tracepoint.

  Attributes:
    continuous_time (int): continuous time.
    data (bytes): content of the tracepoint.
    data_size (int): size of the data segment.
    format_string_location (int): offset to the formated string location.
    thread_identifier (int): thread identifier.
  """

  def __init__(self):
    """Initialize a Firehose tracepoint."""
    super(Tracev3FirehoseTracepoint, self).__init__()
    self.continuous_time = None
    self.data = None
    self.data_size = None
    self.format_string_location = None
    self.thread_identifier = None

  def CopyFromFirehostTracepoint(self, tracepoint):
    """Copies attributes a firehose tracepoint.

    Args:
      tracepoint (firehose_tracepoint): firehose tracepoint.
    """
    self.continuous_time = tracepoint.continuous_time_lower + (
        tracepoint.continuous_time_upper << 32 )
    self.data_size = tracepoint.data_size
    self.format_string_location = tracepoint.format_string_location
    self.thread_identifier = tracepoint.thread_identifier


class UUIDTextFile(data_format.BinaryDataFile):
  """Apple Unified Logging and Activity Tracing (uuidtext) file."""

  # Using a class constant significantly speeds up the time required to load
  # the dtFabric definition file.
  _FABRIC = data_format.BinaryDataFile.ReadDefinitionFile('aul_uuidtext.yaml')

  _DEBUG_INFO_FILE_FOOTER = [
      ('library_path', 'Library path', '_FormatString')]

  _DEBUG_INFO_FILE_HEADER = [
      ('signature', 'Signature', '_FormatIntegerAsHexadecimal8'),
      ('major_format_version', 'Major format version',
       '_FormatIntegerAsDecimal'),
      ('minor_format_version', 'Minor format version',
       '_FormatIntegerAsDecimal'),
      ('number_of_entries', 'Number of entries', '_FormatIntegerAsDecimal'),
      ('entry_descriptors', 'Entry descriptors',
       '_FormatArrayOfEntryDescriptors')]

  def __init__(self, debug=False, output_writer=None):
    """Initializes an uuidtext file.

    Args:
      debug (Optional[bool]): True if debug information should be written.
      output_writer (Optional[OutputWriter]): output writer.
    """
    super(UUIDTextFile, self).__init__(
        debug=debug, output_writer=output_writer)

  def _FormatArrayOfEntryDescriptors(self, array_of_entry_descriptors):
    """Formats an array of entry descriptors.

    Args:
      array_of_entry_descriptors (list[uuidtext_entry_descriptor]): array of
          entry descriptors.

    Returns:
      str: formatted array of entry descriptors.
    """
    value = '\n'.join([
        (f'\t[{entry_index:03d}] offset: 0x{entry_descriptor.offset:08x}, '
         f'data size: {entry_descriptor.data_size:d}')
        for entry_index, entry_descriptor in enumerate(
            array_of_entry_descriptors)])
    return f'{value:s}\n'

  def _ReadFileFooter(self, file_object, file_offset):
    """Reads a file footer.

    Args:
      file_object (file): file-like object.
      file_offset (int): offset of the file footer relative to the start
          of the file.

    Raises:
      ParseError: if the file footer cannot be read.
    """
    data_type_map = self._GetDataTypeMap('uuidtext_file_footer')

    file_footer, _ = self._ReadStructureFromFileObject(
        file_object, file_offset, data_type_map, 'file footer')

    if self._debug:
      self._DebugPrintStructureObject(
          file_footer, self._DEBUG_INFO_FILE_FOOTER)

  def _ReadFileHeader(self, file_object):
    """Reads a file header.

    Args:
      file_object (file): file-like object.

    Returns:
      uuidtext_file_header: a file header.

    Raises:
      ParseError: if the file header cannot be read.
    """
    data_type_map = self._GetDataTypeMap('uuidtext_file_header')

    file_header, _ = self._ReadStructureFromFileObject(
        file_object, 0, data_type_map, 'file header')

    if self._debug:
      self._DebugPrintStructureObject(
          file_header, self._DEBUG_INFO_FILE_HEADER)

    if file_header.signature != 0x66778899:
      raise errors.ParseError(
          f'Unsupported signature: 0x{file_header.signature:04x}.')

    format_version = (
        file_header.major_format_version, file_header.minor_format_version)
    if format_version != (2, 1):
      format_version_string = '.'.join([
          f'{file_header.major_format_version:d}',
          f'{file_header.minor_format_version:d}'])
      raise errors.ParseError(
          f'Unsupported format version: {format_version_string:s}')

    return file_header

  def ReadFileObject(self, file_object):
    """Reads an uuidtext file-like object.

    Args:
      file_object (file): file-like object.

    Raises:
      ParseError: if the file cannot be read.
    """
    file_header = self._ReadFileHeader(file_object)

    file_offset = file_object.tell()
    for entry_descriptor in file_header.entry_descriptors:
      file_offset += entry_descriptor.data_size

    self._ReadFileFooter(file_object, file_offset)
