from . import _loading

from mods_base import get_pc, hook
from unrealsdk import find_all, find_class
from unrealsdk.unreal import UObject, WrappedStruct, BoundFunction
from unrealsdk.hooks import Block as BlockHook

from enum import IntEnum
from typing import Any

gfx_dialog: UObject
loading_message: str


class GameSelection(IntEnum):
    NewGame = -1
    Matchmaking = -2
    LanBrowser = -3
    OnlineBrowser = -4


game_selection: int


@hook("WillowGame.FrontendGFxMovie:LaunchSaveGameEx", immediately_enable=True)
def Frontend_LaunchSaveGameEx(
    _1: UObject, args: WrappedStruct, _3: Any, _4: BoundFunction
) -> type[BlockHook] | None:
    global game_selection

    _loading.probe_mods()

    if _loading.total_package_count > 0:
        game_selection = args.PlayThrough
        show_dialog(confirmation=_loading.total_package_count > 100)
        return BlockHook


@hook("WillowGame.FrontendGFxMovie:LaunchNewGame", immediately_enable=True)
def Frontend_LaunchNewGame(
    _1: UObject, _2: WrappedStruct, _3: Any, _4: BoundFunction
) -> type[BlockHook] | None:
    global game_selection

    _loading.probe_mods()

    if _loading.total_package_count > 0:
        game_selection = GameSelection.NewGame
        show_dialog(confirmation=_loading.total_package_count > 100)
        return BlockHook


@hook("WillowGame.FrontendGFxMovie:StartMatchmaking", immediately_enable=True)
def Frontend_StartMatchmaking(
    _1: UObject, _2: WrappedStruct, _3: Any, _4: BoundFunction
) -> type[BlockHook] | None:
    global game_selection

    _loading.probe_mods()

    if _loading.total_package_count > 0:
        game_selection = GameSelection.Matchmaking
        show_dialog(confirmation=_loading.total_package_count > 100)
        return BlockHook


@hook("WillowGame.FrontendGFxMovie:ShowServerBrowser", immediately_enable=True)
def Frontend_ShowServerBrowser(
    _1: UObject, args: WrappedStruct, _3: Any, _4: BoundFunction
) -> type[BlockHook] | None:
    global game_selection

    _loading.probe_mods()

    if _loading.total_package_count > 0:
        if args.bIsLanBrowser:
            game_selection = GameSelection.LanBrowser
        else:
            game_selection = GameSelection.OnlineBrowser
        show_dialog(confirmation=_loading.total_package_count > 100)
        return BlockHook


def show_dialog(*, confirmation: bool) -> None:
    global gfx_dialog, loading_message

    Default__WillowGFxDialogBox = find_class("WillowGFxDialogBox").ClassDefaultObject
    for other_dialog_box in find_all(Default__WillowGFxDialogBox.Class):
        if other_dialog_box is not Default__WillowGFxDialogBox:
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
    Frontend_LaunchSaveGameEx.disable()
    Frontend_LaunchNewGame.disable()
    Frontend_StartMatchmaking.disable()
    Frontend_ShowServerBrowser.disable()

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
) -> type[BlockHook] | None:
    if args.uevent == 1 and obj.GetVariableBool("tooltips._visible"):
        if args.ukey in ("Enter", "XboxTypeS_A"):
            _loading.begin_loading()
        elif args.ukey in ("Escape", "XboxTypeS_B"):
            close_dialog()
    return BlockHook


def close_dialog() -> None:
    global gfx_dialog
    gfx_dialog.Close()
    del gfx_dialog
    DialogBox_HandleInputKey.disable()


def continue_game() -> None:
    close_dialog()

    frontend = get_pc().GetFrontendMovie()

    if game_selection == GameSelection.NewGame:
        frontend.LaunchNewGame()
    elif game_selection == GameSelection.Matchmaking:
        frontend.StartMatchmaking()
    elif game_selection == GameSelection.LanBrowser:
        frontend.ShowServerBrowser(True)
    elif game_selection == GameSelection.OnlineBrowser:
        frontend.ShowServerBrowser(False)
    else:
        frontend.LaunchSaveGameEx(game_selection)
