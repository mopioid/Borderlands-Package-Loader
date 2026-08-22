from __future__ import annotations

from mods_base import Game

from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar, Iterable, Iterator, Self, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from .bl2 import *
elif Game.get_current() == Game.AoDK:
    from .aodk import *
elif Game.get_current() == Game.BL2:
    from .bl2 import *
elif Game.get_current() == Game.TPS:
    from .tps import *


type PackageLoad = str | Sequence[str] | PackageLoadCharacter | PackageLoadLevel | PackageLoadAll
"""
Any type designated as a PackageLoad may be included in a mod's `package_loads`:
    A string; the name of a package to be passed directly to `unrealsdk.load_package()`.
    A Sequence of strings; names of packages that should be loaded alongside one another, in the
        order they are provided.
    An Sequence of package names; packages in this sequence will be loaded together as a group.
    An instance of `PackageLoadCharacter`; a package for a playable character.
    An instance of `PackageLoadLevel`; a PersistentMap that should be loaded alongside all of its
        SecondaryMaps in the same way as performed by the game.
    `PackageLoadLevel.All` and `PackageLoadCharacter.All`; expand to individual entries of
        `PackageLoadLevel` and `PackageLoadCharacter` respectively during `on_load_packages`.
"""


class PackageLoaderError(Exception):
    pass


class PackageLoadAll(Iterable[PackageLoad]):
    pass


class PackageLoadCharacter(StrEnum):
    Assassin = "gd_assassin_streaming_sf"
    Mercenary = "gd_mercenary_streaming_sf"
    Siren = "gd_siren_streaming_sf"
    Soldier = "gd_soldier_streaming_sf"
    Mechro = "gd_tulip_mechro_streaming_sf"
    Psycho = "gd_lilac_psycho_streaming_sf"

    Baroness = "crocus_baroness_streaming_sf"
    Doppel = "quince_doppel_streaming_sf"
    Enforcer = "gd_enforcer_streaming_sf"
    Gladiator = "gd_gladiator_streaming_sf"
    Lawbringer = "gd_lawbringer_streaming_sf"
    Prototype = "gd_prototype_streaming_sf"

    def __eq__(self, value: object) -> bool:
        return self.value == value.lower() if isinstance(value, str) else False

    @dataclass(kw_only=True, frozen=True)
    class All(PackageLoadAll):
        """
        A convenience object that expands to additional objects representing characters to be
        loaded.

        Args:
            blacklist: A Sequence of `PackageLoadCharacter` or character package names to skip.
        """

        blacklist: Sequence[str | PackageLoadCharacter] = field(default=(), compare=False)

        _normalized_blacklist: Sequence[str] = field(init=False, repr=False)

        def __post_init__(self) -> None:
            object.__setattr__(
                self,
                "_normalized_blacklist",
                tuple(character.lower() for character in self.blacklist),
            )

        def __iter__(self) -> Iterator[PackageLoad]:
            blacklist = tuple(character.lower() for character in self.blacklist)
            return (
                character
                for character in PackageLoadCharacter
                if character in characters and character not in blacklist
            )

        def __contains__(self, item: object) -> bool:
            return isinstance(item, str) and item.lower() in tuple(iter(self))


@dataclass(frozen=True, init=False, eq=False, slots=True)
class PackageLoadLevel:
    """
    An object representing packages to be loaded for a specific level. All packages for the level
    will be loaded as a group, in the order indicated in the game's LevelDependencyList objects.
    """

    name: str = field(repr=False, hash=False, compare=False)
    """The level's human-readable name, e.g. "Southpaw Steam & Power" """
    persistent_map: str = field(repr=True, hash=True, compare=True)
    """The level's persistent map, e.g. "SouthpawFactory_P" """
    packages: Sequence[str] = field(repr=False, hash=False, compare=False)
    """The level's secondary maps"""
    dlc: str | None = field(repr=False, hash=False, compare=False)
    """TODO"""

    _instances: ClassVar[dict[str, Self]] = dict()

    def __new__(cls, persistent_map: str) -> Self:
        return cls._instances[persistent_map.lower()]

    @dataclass(kw_only=True, frozen=True)
    class All(PackageLoadAll):
        """
        A convenience object that expands to additional objects representing levels to be loaded.

        Args:
            blacklist: A Sequence of `PackageLoadLevel` and/or persistent map names (e.g.
                "Sanctuary_P") to skip.
            persistent_only: If True, expands to strings of the persistent map names, thus only
                loading the persistent map package for each level. If False, expands to
                `PackageLoadLevel`s, thus loading the persistent map and all its secondary maps
                (see: `PackageLoadLevel`).
        """

        persistent_only: bool = False
        blacklist: Sequence[str | PackageLoadLevel] = field(default=(), compare=False)

        _normalized_blacklist: Sequence[str] = field(init=False, repr=False, compare=True)

        def __post_init__(self) -> None:
            object.__setattr__(
                self,
                "_normalized_blacklist",
                tuple(
                    level.lower() if isinstance(level, str) else level.persistent_map
                    for level in self.blacklist
                ),
            )

        def __iter__(self) -> Iterator[PackageLoad]:
            return (
                (
                    persistent_map
                    for persistent_map in PackageLoadLevel._instances
                    if persistent_map not in self._normalized_blacklist
                )
                if self.persistent_only
                else (
                    level
                    for level in PackageLoadLevel._instances.values()
                    if level.persistent_map not in self._normalized_blacklist
                )
            )

        def __contains__(self, item: object) -> bool:
            if isinstance(item, str):
                item = item.lower()
                if item in self._normalized_blacklist:
                    return False
                if self.persistent_only:
                    return item in PackageLoadLevel._instances
                return any(
                    item in level.packages
                    for level in PackageLoadLevel._instances.values()
                    if level.persistent_map not in self._normalized_blacklist
                )

            if isinstance(item, PackageLoadLevel):
                return (
                    False
                    if self.persistent_only
                    else item.persistent_map not in self._normalized_blacklist
                )

            return False


for dlc, name, persistent_map, *secondary_maps in levels:
    level = super(PackageLoadLevel, PackageLoadLevel).__new__(PackageLoadLevel)

    object.__setattr__(level, "persistent_map", persistent_map.lower())
    object.__setattr__(level, "name", name)
    object.__setattr__(
        level, "packages", (level.persistent_map, *(map.lower() for map in secondary_maps))
    )
    object.__setattr__(level, "dlc", dlc)

    PackageLoadLevel._instances[level.persistent_map] = level


package_blacklist = {
    "akaudio",
    "core",
    "engine",
    "gameframework",
    "gearboxframework",
    "gfxui",
    "ipdrv",
    "onlinesubsystemsteamworks",
    "onlinesubsystemepicstore",
    "startup",
    "startup_loc_int",
    "startup_loc_deu",
    "startup_loc_esn",
    "startup_loc_fra",
    "startup_loc_ita",
    "startup_loc_jpn",
    "startup_loc_kor",
    "startup_loc_rus",
    "willowgame",
}
