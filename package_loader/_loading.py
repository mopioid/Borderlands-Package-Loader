from . import _memory
from ._data import PackageLoad, PackageLoaderError
from ._groups import (
    LoadHandler,
    PackageGroup,
    expand_loads,
    group_loads,
)

from mods_base import Mod, get_pc, hook
from unrealsdk import find_all, find_class, load_package
from unrealsdk.logging import error, info, misc, warning  # pyright: ignore[reportUnusedImport]
from unrealsdk.unreal import UObject, WrappedStruct, BoundFunction
from unrealsdk.hooks import Block as BlockHook

from time import sleep
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

playthrough: int

handler_mods: dict[LoadHandler, Mod]
package_groups: list[PackageGroup]

gfx_dialog: UObject
loading_message: str
total_package_count: int = 0
loaded_package_count: int = 0


@hook("WillowGame.FrontendGFxMovie:LaunchSaveGameEx", immediately_enable=True)
def Frontend_LaunchSaveGameEx(
    _1: UObject, args: WrappedStruct, _3: Any, _4: BoundFunction
) -> type[BlockHook] | None:
    global playthrough

    probe_mods()

    if total_package_count > 0:
        playthrough = args.PlayThrough
        start_dialog(confirmation=total_package_count > 100)
        return BlockHook


def start_dialog(*, confirmation: bool) -> None:
    global gfx_dialog, loading_message

    Default__WillowGFxDialogBox = find_class("WillowGFxDialogBox").ClassDefaultObject
    for other_dialog_box in find_all(Default__WillowGFxDialogBox.Class):
        if other_dialog_box is not Default__WillowGFxDialogBox:
            other_dialog_box.Close()

    gfx_dialog = get_pc().GFxUIManager.ShowDialog()
    gfx_dialog.SetPriority(254)

    mod_name_list = [f"<font color='#FFDD88'>{mod.name}</font>" for mod in handler_mods.values()]
    if len(mod_name_list) > 2:
        mod_names = f"{", ".join(mod_name_list[:-1])}, and {mod_name_list[-1]}"
    elif len(mod_name_list) == 2:
        mod_names = f"{mod_name_list[0]} and {mod_name_list[1]}"
    else:
        mod_names = mod_name_list[0]

    loading_message = (
        f"The mod{f"s {mod_names} are" if len(mod_name_list) > 1 else f" {mod_names} is"} currently"
        " loading data. This may take some time.\n\nLoaded: "
    )

    if confirmation:
        update_dialog(
            title="Loading Data",
            message=f"Before you begin the game, the mod{"s" if len(mod_name_list) > 1 else ""}"
            f" {mod_names} must load data, which may take some time. Would you like to continue?",
            tooltips="<StringAliasMap:GFx_Accept> Continue     <StringAliasMap:GFx_Cancel> Cancel",
        )
    else:
        begin_loading()

    DialogBox_HandleInputKey.enable()


def update_dialog(
    *,
    title: str | None = None,
    message: str | None = None,
    tooltips: str | None = None,
) -> None:
    if title is not None:
        gfx_dialog.DlgCaptionMarkup = title
    if message is not None:
        gfx_dialog.DlgTextMarkup = message
    if tooltips == "":
        gfx_dialog.ShowTooltips(False)
    elif tooltips is not None:
        gfx_dialog.SetTooltips(tooltips)
    gfx_dialog.ApplyLayout()


@hook("WillowGame.WillowGFxDialogBox:HandleInputKey")
def DialogBox_HandleInputKey(
    obj: UObject, args: WrappedStruct, _3: Any, _4: BoundFunction
) -> type[BlockHook] | None:
    if args.uevent == 1 and obj.GetVariableBool("tooltips._visible"):
        if args.ukey in ("Enter", "XboxTypeS_A"):
            begin_loading()
        elif args.ukey in ("Escape", "XboxTypeS_B"):
            close_dialog()
    return BlockHook


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

    update_dialog(title="Loading Data", message=loading_message + "0%", tooltips="")

    _memory.force_gc()

    Frontend_LaunchSaveGameEx.disable()
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
        loaded_percentage = (
            f"{loaded_package_count / total_package_count * 100:.0f}%"
            if total_package_count
            else "100%"
        )
        update_dialog(message=loading_message + loaded_percentage)

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
        close_dialog()
        get_pc().GetFrontendMovie().LaunchSaveGameEx(playthrough)


def close_dialog() -> None:
    global gfx_dialog
    gfx_dialog.Close()
    del gfx_dialog
    DialogBox_HandleInputKey.disable()
