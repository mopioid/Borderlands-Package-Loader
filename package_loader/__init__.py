import inspect

import mods_base

from ._loading import mod_list, mod_modules, set_dev_mode
from ._data import PackageLoad, PackageLoadCharacter, PackageLoadLevel, PackageLoaderError

__all__ = (
    "register_mod",
    "deregister_mod",
    "mod_list",
    "set_dev_mode",
    "PackageLoad",
    "PackageLoadCharacter",
    "PackageLoadLevel",
    "PackageLoaderError",
)


mods_base.build_mod(cls=mods_base.Library)


def register_mod(mod: mods_base.Mod) -> None:
    if mod not in mod_list:
        if not (module := inspect.getmodule(inspect.stack()[1].frame)):
            raise PackageLoaderError(f"Could not determine module for mod {mod.name}")
        mod_list.append(mod)
        mod_modules[id(mod)] = module


def deregister_mod(mod: mods_base.Mod) -> None:
    if mod in mod_list:
        mod_list.remove(mod)
        del mod_modules[id(mod)]


"""
To use Package Loader, you must implement two components in your mod. Both can be either in the
top-level of your mod's __init__.py, or as attributes of its `Mod` subclass.

`package_loads` is a Sequence of `PackageLoad` objects, and defines the packages your mod
requires to be loaded. A `PackageLoad` can be any of the following:
    A string; the name of a package to be passed directly to `unrealsdk.load_package()`.
    A Sequence of strings; names of packages that should be loaded alongside one another, in the
        order they are provided.
    An instance of `PackageLoadCharacter`; a package for a playable character.
    An instance of `PackageLoadLevel`; a PersistentMap that should be loaded alongside all of its
        SecondaryMaps in the same way as performed by the game.
    An iterable that itself produces `PackageLoad` objects. Objects in this iterable will be loaded
        together as a group. This can be a custom Sequence of package names for example. The special
        cases `PackageLoadLevel.All` and `PackageLoadCharacter.All` will not be loaded as a group,
        and instead expand to individual entries into iteration during `on_load_packages`.
Example:
```
package_loads: list[PackageLoad] = [
    "Luckys_P",
    [
        "Sanctuary_P",
        "Sanctuary_Dynamic",
        "Sanctuary_Combat",
    ],
    PackageLoadCharacter.Soldier,
    PackageLoadLevel("CraterLake_P"),
    PackageLoadLevel.All(blacklist=["Luckys_P", "Sanctuary_P", "CraterLake_P"]),
]
```

`on_load_packages` is the function you would like called when packages are loaded. It must accept
one argument; at runtime, that will be an Iterator object which produces entries from
`package_loads` as they are loaded. This iterator is unique in that you *must* issue a `yield`
statement at the end of each iteration, in order to pause until the next loaded package.
Example:
```
def on_load_packages(package_loads: Iterable[PackageLoad]):
    pawns: list[UObject] = list()
    for package_load in package_loads:
        if package_load == PackageLoadLevel("CraterLake_P"):
            rat = find_object("WillowAIPawn", "GD_LootMidget_Rat.Character.Pawn_LootMidget_Rat")
            rat.ObjectFlags |= ObjectFlags.KEEP_ALIVE
            pawns.append(rat)
        elif package_load == "HyperionCity_P":
            jenkins = find_object("WillowAIPawn", "GD_JimmyJenkins.Character.Pawn_JimmyJenkins")
            jenkins.ObjectFlags |= ObjectFlags.KEEP_ALIVE
            pawns.append(jenkins)
        yield
    print("Found pawns", pawns)
```
`on_load_packages` will be invoked once per launch of the game, the first time the player loads into
an active session from the main menu.
The order in which entires in `package_loads` are loaded is not guaranteed.
Each iteration of the PackageLoad Iterable is guaranteed to have all of the objects from the
given package(s) loaded. It is not guaranteed that objects from previous or future packages will
not also be loaded.
"""
