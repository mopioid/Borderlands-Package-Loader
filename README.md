# Borderlands Package Loader
A library for Borderlands 2, The Pre-Sequel, and Attack on Dragon Keep that allows multiple mods to
load large numbers of packages in an efficient, stable, and user-friendly way.

<p align="center"><img src="https://i.imgur.com/0XqXD3q.jpeg" width=720></p>

With Package Loader, your mod specifies the packages (or groups of packages) that it needs, and
before any gameplay begins, it will load those packages with the following benefits:
- Memory management is handled to maximize stability even with extreme volumes of packages.
- Every mod using Package Loader shares loads to save load time.
- The user is presented with a progress indicator, rather than the game hanging.

To get started, your mod must first specify the packages it requires:
```py
import package_loader
from package_loader import PackageLoad, PackageLoadLevel, PackageLoadCharacter
import mods_base, unrealsdk
from typing import Iterable

package_loads: list[PackageLoad] = [
    PackageLoadCharacter.Soldier,
    PackageLoadCharacter.Mechro,
    PackageLoadLevel.All(blacklist=["Grass_P", "HypInterlude_P", "RobotSlaughter_P"]),
    "GD_BTech_Streaming_SF",
    "GD_Runner_Streaming_SF",
]
```
`package_loads` may be specified in either the top-level of your mod's module, or in its custom Mod
class.

To receive notice when loading is taking place, you define the function `on_load_packages`, also
either in the mod's module or its class:
```py
all_pawns: set[unrealsdk.unreal.UObject] = set()
all_vehicles: set[unrealsdk.unreal.UObject] = set()

def on_load_packages(loads: Iterable[PackageLoad]):
    for _ in loads:
        for pawn in unrealsdk.find_all("AIPawnBalanceDefinition"):
            pawn.ObjectFlags |= mods_base.ObjectFlags.KEEP_ALIVE
            all_pawns.add(pawn)
        for vehicle in unrealsdk.find_all("VehicleBalanceDefinition"):
            vehicle.ObjectFlags |= mods_base.ObjectFlags.KEEP_ALIVE
            all_vehicles.add(vehicle)
        yield
```
Note that `package_loads` must completely iterate over the `Iterable` object passed to it, and also
it must yield at the end of each iteration to await the next load.

Finally, your mod registers itself with Package Loader:

```py
mod = mods_base.build_mod(name="Ménage à Terre")
package_loader.register_mod(mod)
```

Loading will take place in the main menu when the player attempts to start the game (clicking
Continue, New Game, or Matchmaking).