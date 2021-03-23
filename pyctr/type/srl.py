from threading import Lock
from typing import TYPE_CHECKING, NamedTuple
from types import MappingProxyType
from .base import TypeReaderBase
from ..common import _ReaderOpenFileBase

from ..fileio import SubsectionIO
from pyctr.util import readbe, readle
from os import PathLike

if TYPE_CHECKING:
    from typing import BinaryIO, Dict, Union, Mapping, Optional, Tuple

region_names = (
    "Japanese",
    "English",
    "French",
    "German",
    "Italian",
    "Spanish",
    "Simplified Chinese",
    "Korean",
    "Dutch",
    "Portuguese",
    "Russian",
    "Traditional Chinese",
)

# the order of the SMDH names to check. the difference here is that English is put before Japanese.
_region_order_check = (
    "English",
    "Japanese",
    "French",
    "German",
    "Italian",
    "Spanish",
    "Simplified Chinese",
    "Korean",
    "Dutch",
    "Portuguese",
    "Russian",
    "Traditional Chinese",
)

_region_lock_names = ("JPN", "USA", "EUR", "EUR", "CHN", "KOR", "TWN", "FREE")


SRLICON_SIZE = 0x2400


def _normalize_path(p: str):
    """Fix a given path to work with ExeFS filenames."""
    if p.startswith("/"):
        p = p[1:]
    # while it is technically possible for an ExeFS entry to contain ".bin",
    #   this would not happen in practice.
    # even so, normalization can be disabled by passing normalize=False to
    #   ExeFSReader.open
    if p.lower().endswith(".bin"):
        p = p[:4]
    return p


class _SRLFSOpenFile(_ReaderOpenFileBase):
    """Class for open ExeFS file entries."""

    def __init__(self, reader: "SRLReader", path: str):
        super().__init__(reader, path)
        self._info = reader.entries[self._path]


class SRLReader(TypeReaderBase):
    """
    Reads the contents of NCCH containers.
    """

    def __init__(
        self,
        fp: "Union[PathLike, str, bytes, BinaryIO]",
        *,
        closefd: bool = True,
        _load_icon: bool = True,
    ):

        super().__init__(fp, closefd=closefd)

        # Threading lock to prevent two operations on one class instance from interfering with eachother.
        self._lock = Lock()

        header = self._file.read(0x180)
        unitcode = readbe(header[0x12:0x13])

        self.apptitle = header[0x0:0x12]
        self.regionlocks = ""
        self.shortDesc = ""
        self.longDesc = ""
        if unitcode & 0x01:
            extheader = self._file.read(0xE80)
            region_lockout = readle(extheader[0x34:0x35])
            if region_lockout == "0x0":
                self.regionlocks = "Normal"
            elif region_lockout == "0x80":
                self.regionlocks = "China"
            elif region_lockout == "0x40":
                self.regionlocks = "Korea"
            else:
                self.regionlocks = str(region_lockout)

        self._icon_offset = readle(header[0x068 : 0x68 + 4])
        self._load_icon()

    def _load_icon(self):
        try:
            with SubsectionIO(self._file, self._icon_offset, SRLICON_SIZE) as f:
                self.icon = SRLIcon.load(f)
        except (Exception):  # (ExeFSFileNotFoundError, InvalidSMDHError):
            pass

    def __len__(self) -> int:
        """Return the amount of entries in the ExeFS."""
        return len(self.entries)

    def open(self, path: str, *, normalize: bool = True):
        """
        Open an entry in the ExeFS for reading.

        :param path: Name of the entry. Can start with / or end in .bin.
        :param normalize: Remove / and .bin from the path.
        :return: A file-like object that reads from the entry.
        """
        if normalize:
            # remove beginning "/" and ending ".bin"
            path = _normalize_path(path)

        entry = self.entries[path]
        if entry.offset == -1:
            # this would be the decompressed .code, if the original .code was compressed
            print("Test")
            return _SRLFSOpenFile(self, path)
        else:
            return SubsectionIO(self._file, self._icon_offset, entry.size)


class AppTitle(NamedTuple):
    short_desc: str
    long_desc: str
    publisher: str


class SRLIcon:
    """
    Class for 3DS SMDH. Icon data is currently not supported.

    https://www.3dbrew.org/wiki/SMDH
    """

    # TODO: support other settings

    def __init__(
        self,
        names: "Dict[str, AppTitle]",
        region_lock_allowed="",
        small_icon=None,
        palette_icon=None,
    ):
        self.names: Mapping[str, AppTitle] = MappingProxyType(
            {n: names.get(n, None) for n in region_names}
        )
        self.regionlocks = region_lock_allowed
        self.small_icon = small_icon
        self.palette_icon = palette_icon

    def __repr__(self):
        return f"<{type(self).__name__} title: {self.get_app_title().short_desc}>"

    def get_app_title(
        self, language: "Union[str, Tuple[str, ...]]" = _region_order_check
    ) -> "Optional[AppTitle]":
        if isinstance(language, str):
            language = (language,)

        for lang in language:
            apptitle = self.names[lang]
            if apptitle:
                return apptitle

        # if, for some reason, it fails to return...
        return AppTitle("unknown", "unknown", "unknown")

    @classmethod
    def load(cls, fp: "BinaryIO") -> "SRLIcon":
        """Load an SMDH from a file-like object."""
        srlicon = fp.read(SRLICON_SIZE)

        app_structs = srlicon[0x240:0x0A40]
        names: Dict[str, AppTitle] = {}
        # due to region_names only being 12 elements, this will only process 12. the other 4 are unused.
        for app_title, region in zip(
            (app_structs[x : x + 0x100] for x in range(0, 0x800, 0x100)), region_names
        ):
            title_string = (
                app_title[0x0:0x100].decode("utf-16le").strip("\0").splitlines()
            )
            if len(title_string) == 3:
                names[region] = AppTitle(
                    title_string[0],
                    title_string[0] + " " + title_string[1],
                    title_string[2],
                )
            elif len(title_string) == 2:
                names[region] = AppTitle(
                    title_string[0], title_string[0], title_string[1]
                )
            else:
                names[region] = AppTitle("", "", "")
        regionlist = []
        region_lockout = readle(srlicon[0x2018 : 0x2018 + 4])
        if region_lockout == 0x7FFFFFFF:
            regions = "ALL"
        else:
            for i in range(7):
                bit = region_lockout & (1 << i)
                if bit != 0:
                    regionlist.append(_region_lock_names[i])
            regionlist = set(regionlist)
            regions = ",".join(regionlist)
        regions = ""
        small_icon = srlicon[0x20 : 0x20 + 0x200]
        palette_icon = srlicon[0x220 : 0x220 + 0x20]
        return cls(names, regions, small_icon, palette_icon)

    @classmethod
    def from_file(cls, fn: "Union[PathLike, str, bytes]") -> "SRLIcon":
        with open(fn, "rb") as f:
            return cls.load(f)