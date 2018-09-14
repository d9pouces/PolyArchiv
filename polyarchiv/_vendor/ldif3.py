# coding=utf-8
"""ldif3 - generate and parse LDIF data (see RFC 2849)."""

from __future__ import unicode_literals

import base64
import logging
import re
from collections import OrderedDict

try:  # pragma: nocover
    # noinspection PyCompatibility
    from urlparse import urlparse
    from urllib import urlopen
except ImportError:  # pragma: nocover
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.parse import urlparse

    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.request import urlopen

__version__ = "3.2.0"

__all__ = [
    # constants
    "LDIF_PATTERN",
    # classes
    "LDIFWriter",
    "LDIFParser",
]

log = logging.getLogger("ldif3")

ATTRTYPE_PATTERN = r"[\w;.-]+(;[\w_-]+)*"
ATTRVALUE_PATTERN = r'(([^,]|\\,)+|".*?")'
ATTR_PATTERN = ATTRTYPE_PATTERN + r"[ ]*=[ ]*" + ATTRVALUE_PATTERN
RDN_PATTERN = ATTR_PATTERN + r"([ ]*\+[ ]*" + ATTR_PATTERN + r")*[ ]*"
DN_PATTERN = RDN_PATTERN + r"([ ]*,[ ]*" + RDN_PATTERN + r")*[ ]*"
DN_REGEX = re.compile("^%s$" % DN_PATTERN)

LDIF_PATTERN = (
    "^((dn(:|::) %(DN_PATTERN)s)|(%(ATTRTYPE_PATTERN)" "s(:|::) .*)$)+" % vars()
)

MOD_OPS = ["add", "delete", "replace"]
CHANGE_TYPES = ["add", "delete", "modify", "modrdn"]


def is_dn(s):
    """Return True if s is a LDAP DN."""
    if s == "":
        return True
    rm = DN_REGEX.match(s)
    return rm is not None and rm.group(0) == s


def lower(l):
    """Return a list with the lowercased items of l."""
    return [i.lower() for i in l or []]


class LDIFParser(object):
    """Read LDIF entry or change records from file object.

    :type input_file: file-like object in binary mode
    :param input_file: file to read the LDIF input from

    :type ignored_attr_types: List[string]
    :param ignored_attr_types: List of attribute types that will be ignored

    :type process_url_schemes: List[bytearray]
    :param process_url_schemes: List of URL schemes to process with urllib.
        An empty list turns off all URL processing and the attribute is
        ignored completely.

    :type line_sep: bytearray
    :param line_sep: line separator

    :type encoding: string
    :param encoding: Encoding to use for converting values to unicode strings.
        If decoding failes, the raw bytestring will be used instead. You can
        also pass ``None`` which will skip decoding and always produce
        bytestrings. Note that this only applies to entry values. ``dn`` and
        entry keys will always be unicode strings.

    :type strict: boolean
    :param strict: If set to ``False``, recoverable parse errors will produce
        log warnings rather than exceptions.
    """

    # noinspection PyMethodMayBeStatic
    def _strip_line_sep(self, s):
        """Strip trailing line separators from s, but no other whitespaces."""
        if s[-2:] == b"\r\n":
            return s[:-2]
        elif s[-1:] == b"\n":
            return s[:-1]
        else:
            return s

    # noinspection PyDefaultArgument
    def __init__(
        self,
        input_file,
        ignored_attr_types=[],
        process_url_schemes=[],
        line_sep=b"\n",
        encoding="utf8",
        strict=True,
    ):
        self._input_file = input_file
        self._process_url_schemes = lower(process_url_schemes)
        self._ignored_attr_types = lower(ignored_attr_types)
        self._line_sep = line_sep
        self._encoding = encoding
        self._strict = strict

        self.line_counter = 0  #: number of lines that have been read
        self.byte_counter = 0  #: number of bytes that have been read
        self.records_read = 0  #: number of records that have been read

    def _iter_unfolded_lines(self):
        """Iter input unfoled lines. Skip comments."""
        line = self._input_file.readline()
        while line:
            self.line_counter += 1
            self.byte_counter += len(line)

            line = self._strip_line_sep(line)

            nextline = self._input_file.readline()
            while nextline and nextline[:1] == b" ":
                line += self._strip_line_sep(nextline)[1:]
                nextline = self._input_file.readline()

            if not line.startswith(b"#"):
                yield line
            line = nextline

    def _iter_blocks(self):
        """Iter input lines in blocks separated by blank lines."""
        lines = []
        for line in self._iter_unfolded_lines():
            if line:
                lines.append(line)
            else:
                self.records_read += 1
                yield lines
                lines = []
        if lines:
            self.records_read += 1
            yield lines

    def _parse_attr(self, line):
        """Parse a single attribute type/value pair."""
        colon_pos = line.index(b":")
        attr_type = line[0:colon_pos].decode("ascii")

        if line[colon_pos:].startswith(b"::"):
            attr_value = base64.decodestring(line[colon_pos + 2 :])
        elif line[colon_pos:].startswith(b":<"):
            url = line[colon_pos + 2 :].strip()
            attr_value = b""
            if self._process_url_schemes:
                u = urlparse(url)
                if u[0] in self._process_url_schemes:
                    attr_value = urlopen(url.decode("ascii")).read()
        else:
            attr_value = line[colon_pos + 1 :].strip()

        if attr_type == "dn":
            return attr_type, attr_value.decode("utf8")
        elif self._encoding is not None:
            try:
                return attr_type, attr_value.decode(self._encoding)
            except UnicodeError:
                pass
        return attr_type, attr_value

    def _error(self, msg):
        if self._strict:
            raise ValueError(msg)
        else:
            log.warning(msg)

    def _check_dn(self, dn, attr_value):
        """Check dn attribute for issues."""
        if dn is not None:
            self._error("Two lines starting with dn: in one record.")
        if not is_dn(attr_value):
            self._error(
                "No valid string-representation of "
                "distinguished name %s." % attr_value
            )

    def _check_changetype(self, dn, changetype, attr_value):
        """Check changetype attribute for issues."""
        if dn is None:
            self._error("Read changetype: before getting valid dn: line.")
        if changetype is not None:
            self._error("Two lines starting with changetype: in one record.")
        if attr_value not in CHANGE_TYPES:
            self._error("changetype value %s is invalid." % attr_value)

    def _parse_entry_record(self, lines):
        """Parse a single entry record from a list of lines."""
        dn = None
        entry = OrderedDict()

        for line in lines:
            attr_type, attr_value = self._parse_attr(line)

            if attr_type == "dn":
                self._check_dn(dn, attr_value)
                dn = attr_value
            elif attr_type == "version" and dn is None:
                pass  # version = 1
            else:
                if dn is None:
                    self._error(
                        "First line of record does not start "
                        'with "dn:": %s' % attr_type
                    )
                if (
                    attr_value is not None
                    and attr_type.lower() not in self._ignored_attr_types
                ):
                    if attr_type in entry:
                        entry[attr_type].append(attr_value)
                    else:
                        entry[attr_type] = [attr_value]

        return dn, entry

    def parse(self):
        """Iterate LDIF entry records.

        :rtype: Iterator[Tuple[string, Dict]]
        :return: (dn, entry)
        """
        for block in self._iter_blocks():
            yield self._parse_entry_record(block)
