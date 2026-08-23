from . import _loading

from mods_base import get_pc, hook
from unrealsdk import find_all, hooks
from unrealsdk.unreal import UObject, WrappedStruct, BoundFunction

from copy import deepcopy
from typing import Any

gfx_dialog: UObject
loading_message: str

frontend_func: BoundFunction
frontend_args: WrappedStruct

frontend_intercepts = ("LaunchSaveGameEx", "LaunchNewGame", "StartMatchmaking", "ShowServerBrowser")


def intercept_frontend(
    _1: UObject, args: WrappedStruct, _3: Any, func: BoundFunction
) -> type[hooks.Block] | None:
    global frontend_func, frontend_args

    _loading.probe_mods()
    if _loading.total_package_count:
        show_dialog(confirmation=_loading.total_package_count > 100)

        frontend_func = func
        frontend_args = deepcopy(args)
        return hooks.Block


for func_name in frontend_intercepts:
    hooks.add_hook(
        func="WillowGame.FrontendGFxMovie:" + func_name,
        type=hooks.Type.PRE,
        identifier=__file__,
        callback=intercept_frontend,
    )


def show_dialog(*, confirmation: bool) -> None:
    global gfx_dialog, loading_message

    for other_dialog_box in find_all("WillowGFxDialogBox", exact=False):
        if other_dialog_box is not other_dialog_box.Class.ClassDefaultObject:
            other_dialog_box.Close()

    gfx_dialog = get_pc().GFxUIManager.ShowDialog()
    gfx_dialog.SetPriority(254)

    mod_name_list = [
        f"<font color='#FFDD88'>{mod.name}</font>" for mod in _loading.handler_mods.values()
    ]
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
        gfx_dialog.DlgCaptionMarkup = "Loading Data"
        gfx_dialog.DlgTextMarkup = (
            f"Before you begin the game, the mod{"s" if len(mod_name_list) > 1 else ""}"
            f" {mod_names} must load data, which may take some time. Would you like to continue?"
        )
        gfx_dialog.SetTooltips(
            "<StringAliasMap:GFx_Accept> Continue     <StringAliasMap:GFx_Cancel> Cancel"
        )
        gfx_dialog.ApplyLayout()
    else:
        _loading.begin_loading()

    DialogBox_HandleInputKey.enable()


def begin_loading_dialog() -> None:
    for func_name in frontend_intercepts:
        hooks.remove_hook(
            func="WillowGame.FrontendGFxMovie:" + func_name,
            type=hooks.Type.PRE,
            identifier=__file__,
        )

    gfx_dialog.DlgCaptionMarkup = "Loading Data"
    gfx_dialog.DlgTextMarkup = loading_message + "0%"
    gfx_dialog.ShowTooltips(False)
    gfx_dialog.ApplyLayout()


def set_loading_dialog(percentage: float) -> None:
    gfx_dialog.DlgTextMarkup = loading_message + f"{percentage:.0f}%"
    gfx_dialog.ApplyLayout()


@hook("WillowGame.WillowGFxDialogBox:HandleInputKey")
def DialogBox_HandleInputKey(
    obj: UObject, args: WrappedStruct, _3: Any, _4: BoundFunction
) -> type[hooks.Block] | None:
    if args.uevent == 1 and obj.GetVariableBool("tooltips._visible"):
        if args.ukey in ("Enter", "XboxTypeS_A"):
            _loading.begin_loading()
        elif args.ukey in ("Escape", "XboxTypeS_B"):
            close_dialog()
    return hooks.Block


def close_dialog() -> None:
    global gfx_dialog
    gfx_dialog.Close()
    del gfx_dialog
    DialogBox_HandleInputKey.disable()


def continue_frontend() -> None:
    global frontend_func, frontend_args
    close_dialog()
    frontend_func(frontend_args)
    del frontend_func, frontend_args
