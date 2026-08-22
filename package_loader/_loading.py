from . import _memory
from ._data import PackageLoad, PackageLoaderError
from ._groups import (
    LoadHandler,
    PackageGroup,
    expand_loads,
    group_loads,
)
from . import _ui

from mods_base import Mod, hook
from unrealsdk import load_package
from unrealsdk.unreal import UObject, WrappedStruct, BoundFunction
from unrealsdk.logging import error, info, misc, warning  # pyright: ignore[reportUnusedImport]

import traceback
from types import ModuleType
from typing import Any, Generator, Iterator, Sequence

LOADS_ATTR = "package_loads"
HANDLER_ATTR = "on_load_packages"

mod_list: list[Mod] = list()
mod_modules: dict[int, ModuleType] = dict()

dev_mode: bool = False


def set_dev_mode(enable: bool) -> None:
    """
    When package loading occurs in dev mode, a full garbage collection is ensured after each entry
    in `package_loads`. This is meant to be useful for using unrealsdk.find_all() to research which
    objects are loaded from which packages or groups of packages.
    """
    global dev_mode
    dev_mode = enable


def get_mod_attr(mod: Mod, field: str) -> Any:
    if not (value := getattr(mod, field, None)):
        value = getattr(mod_modules[id(mod)], field, None)
    return value


def print_exception(exception: Exception) -> None:
    if trace := exception.__traceback__:
        trace = trace.tb_next
    traceback.print_exception(type(exception), exception, trace)


class PackageLoadIterator(Iterator[PackageLoad]):
    _next: PackageLoad | None = None
    _allow_next: bool = False

    def __next__(self) -> PackageLoad:
        if self._next is None:
            raise StopIteration
        if not self._allow_next:
            raise PackageLoaderError(
                f"{HANDLER_ATTR} must yield on each iteration of a loaded package"
            )
        self._allow_next = False
        return self._next


load_iterator = PackageLoadIterator()

handler_mods: dict[LoadHandler, Mod]
package_groups: list[PackageGroup]

total_package_count: int = 0
loaded_package_count: int = 0


def probe_mods() -> None:
    global handler_mods, package_groups, total_package_count

    handler_mods = dict()
    handler_loads: dict[LoadHandler, Sequence[PackageLoad]] = dict()

    for mod in mod_list:
        if not mod.is_enabled:
            continue

        try:
            package_loads: Sequence[PackageLoad] = get_mod_attr(
                mod, "package_loads"
            )  # pyright: ignore[reportAssignmentType]
            if not isinstance(
                package_loads, Sequence
            ):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise PackageLoaderError(f"{LOADS_ATTR} must be a Sequence of `PackageLoad`s")

            on_load_packages = get_mod_attr(mod, HANDLER_ATTR)
            handler: LoadHandler = on_load_packages(
                load_iterator
            )  # pyright: ignore[reportOptionalCall]
            if not isinstance(handler, Generator):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise PackageLoaderError(
                    f"{HANDLER_ATTR} must yield on each iteration of a loaded package"
                )

            loads = tuple(expand_loads(package_loads))
            if len(loads):
                handler_loads[handler] = loads
                handler_mods[handler] = mod

        except Exception as exception:
            print_exception(exception)

    package_groups = group_loads(handler_loads)
    total_package_count = sum(len(package_group.packages) for package_group in package_groups)


def begin_loading() -> None:
    global loaded_package_count
    loaded_package_count = 0

    _ui.begin_loading_dialog()

    _memory.force_gc()

    Viewport_Tick.enable()


@hook("WillowGame.WillowGameViewportClient:Tick")
def Viewport_Tick(_1: UObject, _2: WrappedStruct, _3: Any, _4: BoundFunction) -> None:
    global package_groups, dialog_ticks, total_package_count, loaded_package_count

    _memory.tick_gc()
    if dev_mode and _memory.garbage_collecting:
        return

    if len(package_groups):
        group = package_groups[0]

        size_estimate = group.get_size_estimate()
        if _memory.is_memory_critical(size_estimate):
            if _memory.garbage_collecting:
                return
            warning(
                f"Memory critial at {_memory.get_memory_usage()}"
                f" with {size_estimate} required for {group.packages}"
            )

        del package_groups[0]

        packages = group.get_load_sequence()
        for package in packages:
            load_package(package)

        for handler, load in tuple(group.all_loads()):
            if handler not in handler_mods:
                continue

            load_iterator._next = load
            load_iterator._allow_next = True
            try:
                next(handler)
            except Exception as exception:
                del handler_mods[handler]

                total_package_count = loaded_package_count

                for package_group in tuple(package_groups):
                    package_group.remove_handler(handler)

                    if package_count := len(package_group.packages):
                        total_package_count += package_count
                    else:
                        package_groups.remove(package_group)

                if not isinstance(exception, StopIteration):
                    print_exception(exception)

        _memory.force_gc()

        loaded_package_count += len(packages)
        _ui.set_loading_dialog(
            loaded_package_count / total_package_count * 100 if total_package_count else 100
        )

        if not len(package_groups):
            load_iterator._next = None
            for handler in handler_mods:
                try:
                    next(handler)
                except StopIteration:
                    pass
                except Exception as exception:
                    print_exception(exception)

    elif not _memory.garbage_collecting:
        Viewport_Tick.disable()
        _ui.continue_game()
