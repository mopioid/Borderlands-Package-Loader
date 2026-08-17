from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from typing import ClassVar, Iterable, Iterator, Self, Sequence

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
    Assassin = "GD_Assassin_Streaming_SF"
    Mercenary = "GD_Mercenary_Streaming_SF"
    Siren = "GD_Siren_Streaming_SF"
    Soldier = "GD_Soldier_Streaming_SF"
    Mechro = "GD_Tulip_Mechro_Streaming_SF"
    Psycho = "GD_Lilac_Psycho_Streaming_SF"

    @dataclass(kw_only=True)
    class All(PackageLoadAll):
        """
        A convenience object that expands to additional objects representing characters to be
        loaded.

        Args:
            blacklist: A Sequence of `PackageLoadCharacter` or character package names to skip.
        """

        blacklist: Sequence[str | PackageLoadCharacter] = ()

        def __iter__(self) -> Iterator[PackageLoad]:
            return (
                character for character in PackageLoadCharacter if character not in self.blacklist
            )


class PackageLoadLevel:
    """
    An object representing packages to be loaded for a specific level. All packages for the level
    will be loaded as a group, in the order indicated in the game's LevelDependencyList objects.
    """

    __slots__ = "name", "persistent_map", "secondary_maps", "dlc"

    name: str
    """The level's human-readable name, e.g. "Southpaw Steam & Power" """
    persistent_map: str
    """The level's persistent map, e.g. "SouthpawFactory_P" """
    secondary_maps: Sequence[str]
    """The level's secondary maps"""
    dlc: str | None
    """TODO"""

    _instances: ClassVar[dict[str, Self]] = dict()

    def __new__(cls, persistent_map: str) -> Self:
        return cls._instances[persistent_map]

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self.persistent_map}")'

    def packages(self) -> Iterator[str]:
        """Produces every package that will be loaded for this level, in order."""
        yield self.persistent_map
        yield from self.secondary_maps

    @dataclass(kw_only=True)
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
        blacklist: Sequence[str | PackageLoadLevel] = ()

        def __iter__(self) -> Iterator[PackageLoad]:
            return (
                persistent_map if self.persistent_only else level
                for persistent_map, level in PackageLoadLevel._instances.items()
                if persistent_map not in self.blacklist and level not in self.blacklist
            )

        def __contains__(self, item: object) -> bool:
            if self.persistent_only:
                return isinstance(item, str) and item not in self.blacklist
            else:
                return (
                    isinstance(item, PackageLoadLevel)
                    and item not in self.blacklist
                    and item.persistent_map not in self.blacklist
                )


def level(dlc: str, name: str, persistent_map: str, secondary_maps: Sequence[str]) -> None:
    instance = super(PackageLoadLevel, PackageLoadLevel).__new__(PackageLoadLevel)
    PackageLoadLevel._instances[persistent_map] = instance

    instance.name = name
    instance.persistent_map = persistent_map
    instance.secondary_maps = secondary_maps
    instance.dlc = dlc


#fmt: off
level("GD_Globals.General.LevelList",                       "Arid Nexus - Boneyard",          "Fyrestone_P",            ['Fyrestone_Combat', 'Fyrestone_Dynamic', 'Fyrestone_Audio', 'Fyrestone_FX', 'Fyrestone_Light'])
level("GD_Globals.General.LevelList",                       "The Holy Spirits",               "Luckys_P",               ['Luckys_Light', 'Luckys_FX', 'Luckys_Audio', 'Luckys_Dynamic'])
level("GD_Globals.General.LevelList",                       "Southpaw Steam & Power",         "SouthpawFactory_P",      ['SouthpawFactory_Light', 'SouthpawFactory_Dynamic', 'SouthpawFactory_Audio'])
level("GD_Globals.General.LevelList",                       "Sanctuary Hole",                 "Sanctuary_Hole_P",       ['Sanctuary_Hole_Audio', 'Sanctuary_Hole_Combat', 'Sanctuary_Hole_Dynamic', 'Sanctuary_Hole_FX', 'Sanctuary_Hole_Light', 'Sanctuary_Hole_Skybox'])
level("GD_Globals.General.LevelList",                       "Hero's Pass",                    "FinalBossAscent_P",      ['FinalBossAscent_Combat', 'FinalBossAscent_Dynamic', 'FinalBossAscent_Skybox', 'FinalBossAscent_Audio', 'FinalBossAscent_FX', 'FinalBossAscent_Light'])
level("GD_Globals.General.LevelList",                       "Bloodshot Stronghold",           "dam_p",                  ['Dam_Audio', 'Dam_Combat', 'Dam_Dynamic', 'Dam_FX'])
level("GD_Globals.General.LevelList",                       "Three Horns - Valley",           "Frost_P",                ['Frost_Audio', 'Frost_Dynamic', 'Frost_FX', 'Frost_Light'])
level("GD_Globals.General.LevelList",                       "Sanctuary",                      "Sanctuary_P",            ['Sanctuary_Light', 'Sanctuary_Audio', 'Sanctuary_FX', 'Sanctuary_Dynamic', 'Sanctuary_Combat', 'Sanctuary_Land', 'Sanctuary_Outer', 'Sanctuary_Side'])
level("GD_Globals.General.LevelList",                       "Thousand Cuts",                  "Grass_Cliffs_P",         ['Grass_Cliffs_Dynamic', 'Grass_Cliffs_Combat', 'Grass_Cliffs_FX', 'Grass_Cliffs_Audio', 'Grass_Cliffs_Light'])
level("GD_Globals.General.LevelList",                       "End of the Line",                "TundraTrain_P",          ['TundraTrain_Audio', 'TundraTrain_Combat', 'TundraTrain_Dynamic', 'TundraTrain_FX', 'TundraTrain_Light'])
level("GD_Globals.General.LevelList",                       "Wildlife Exploitation Preserve", "PandoraPark_P",          ['PandoraPark_Audio', 'PandoraPark_Combat', 'PandoraPark_Light', 'PandoraPark_Dynamic', 'PandoraPark_Bloodwing'])
level("GD_Globals.General.LevelList",                       "Terramorphous Peak",             "ThresherRaid_P",         ['ThresherRaid_Light', 'ThresherRaid_Audio', 'ThresherRaid_FX', 'ThresherRaid_Dynamic', 'ThresherRaid_Combat'])
level("GD_Globals.General.LevelList",                       "Tundra Express",                 "tundraexpress_p",        ['TundraExpress_Light', 'TundraExpress_Audio', 'TundraExpress_Combat', 'TundraExpress_Dynamic', 'TundraExpress_FX'])
level("GD_Globals.General.LevelList",                       "The Fridge",                     "Fridge_P",               ['Fridge_Audio', 'Fridge_Caves', 'Fridge_Light', 'Fridge_Combat', 'Fridge_Dynamic', 'Fridge_FX', 'Fridge_Skybox'])
level("GD_Globals.General.LevelList",                       "Southern Shelf - Bay",           "Cove_P",                 ['Cove_Audio', 'Cove_Dynamic', 'Cove_FX', 'Cove_LiarsBerg', 'Cove_Skybox', 'Cove_Light'])
level("GD_Globals.General.LevelList",                       "Frostburn Canyon",               "icecanyon_p",            ['IceCanyon_Light', 'IceCanyon_Audio', 'IceCanyon_Dynamic', 'IceCanyon_FX', 'IceCanyon_Combat'])
level("GD_Globals.General.LevelList",                       "Fink's Slaughterhouse",          "BanditSlaughter_P",      ['BanditSlaughter_Light', 'BanditSlaughter_FX', 'BanditSlaughter_Audio', 'BanditSlaughter_Dynamic', 'BanditSlaughter_Skybox', 'BanditSlaughter_Combat'])
level("GD_Globals.General.LevelList",                       "Three Horns - Divide",           "Ice_P",                  ['Ice_Light', 'Ice_Dynamic', 'Ice_Audio', 'Ice_FX'])
level("GD_Globals.General.LevelList",                       "The Highlands",                  "Grass_P",                ['Grass_Dynamic', 'Grass_Dam', 'Grass_Audio', 'Grass_Light', 'Grass_Combat'])
level("GD_Globals.General.LevelList",                       "Natural Selection Annex",        "CreatureSlaughter_P",    ['CreatureSlaughter_Light', 'CreatureSlaughter_FX', 'CreatureSlaughter_Audio', 'CreatureSlaughter_Dynamic', 'CreatureSlaughter_Skybox', 'CreatureSlaughter_Combat'])
level("GD_Globals.General.LevelList",                       "The Dust",                       "Interlude_P",            ['Interlude_Light', 'Interlude_Audio', 'Interlude_Dynamic', 'Interlude_Combat', 'Interlude_FX', 'Interlude_Skybox'])
level("GD_Globals.General.LevelList",                       "Opportunity",                    "HyperionCity_P",         ['HyperionCity_Skybox', 'HyperionCity_Light', 'HyperionCity_Audio', 'HyperionCity_FX', 'HyperionCity_Combat', 'HyperionCity_Dynamic'])
level("GD_Globals.General.LevelList",                       "Bloodshot Ramparts",             "damtop_p",               ['DamTop_Skybox', 'DamTop_Light', 'DamTop_Combat', 'DamTop_Dynamic', 'DamTop_FX', 'DamTop_Audio'])
level("GD_Globals.General.LevelList",                       "Control Core Angel",             "VOGChamber_P",           ['VOGChamber_Audio', 'VOGChamber_Combat', 'VOGChamber_Dynamic', 'VOGChamber_SanctuaryRoom', 'VOGChamber_FX', 'VOGChamber_Light', 'VOGChamber_Skybox'])
level("GD_Globals.General.LevelList",                       "Sanctuary",                      "SanctuaryAir_P",         ['SanctuaryAir_Audio', 'SanctuaryAir_Combat', 'SanctuaryAir_Dynamic', 'SanctuaryAir_FX', 'SanctuaryAir_Light', 'SanctuaryAir_Side'])
level("GD_Globals.General.LevelList",                       "Ore Chasm",                      "RobotSlaughter_P",       ['RobotSlaughter_Light', 'RobotSlaughter_FX', 'RobotSlaughter_Audio', 'RobotSlaughter_Dynamic', 'RobotSlaughter_Skybox'])
level("GD_Globals.General.LevelList",                       "Arid Nexus - Badlands",          "Stockade_P",             ['Stockade_Audio', 'Stockade_Combat', 'Stockade_Dynamic', 'Stockade_FX', 'Stockade_Light'])
level("GD_Globals.General.LevelList",                       "Southern Shelf",                 "SouthernShelf_P",        ['SouthernShelf_Audio', 'SouthernShelf_Combat', 'SouthernShelf_Dynamic', 'SouthernShelf_Freighter', 'SouthernShelf_FX', 'SouthernShelf_LiarsBerg', 'SouthernShelf_Light', 'SouthernShelf_Skybox', 'SouthernShelf_Tundra'])
level("GD_Globals.General.LevelList",                       "The Highlands - Outwash",        "Outwash_P",              ['Outwash_Light', 'Outwash_Dynamic', 'Outwash_Dam', 'Outwash_Combat', 'Outwash_Audio'])
level("GD_Globals.General.LevelList",                       "Sawtooth Cauldron",              "CraterLake_P",           ['CraterLake_Light', 'CraterLake_Combat', 'CraterLake_Dynamic', 'CraterLake_FX', 'CraterLake_Audio'])
level("GD_Globals.General.LevelList",                       "Friendship Gulag",               "HypInterlude_P",         ['HypInterlude_Dynamic', 'HypInterlude_Light', 'HypInterlude_Audio'])
level("GD_Globals.General.LevelList",                       "Caustic Caverns",                "caverns_p",              ['Caverns_Top', 'Caverns_Audio', 'Caverns_Combat', 'Caverns_Dynamic', 'Caverns_FX', 'Caverns_Light', 'Caverns_Skybox'])
level("GD_Globals.General.LevelList",                       "Lynchwood",                      "Grass_Lynchwood_P",      ['Grass_Lynchwood_Audio', 'Grass_Lynchwood_Combat', 'Grass_Lynchwood_Dynamic', 'Grass_Lynchwood_FX', 'Grass_Lynchwood_Light'])
level("GD_Globals.General.LevelList",                       "Windshear Waste",                "Glacial_P",              ['Glacial_Light', 'Glacial_Skybox', 'Glacial_Audio', 'Glacial_FX', 'Glacial_Dynamic', 'Glacial_Tundra'])
level("GD_Globals.General.LevelList",                       "The Bunker",                     "Boss_Cliffs_P",          ['Boss_Cliffs_Dynamic', 'Boss_Cliffs_Combat', 'Boss_Cliffs_CombatLoader', 'Boss_Cliffs_Audio', 'Boss_Cliffs_FX', 'Boss_Cliffs_Light', 'Boss_Cliffs_Skybox', 'Boss_Cliffs_Skybox_Grass', 'Boss_Cliffs_VOGAntechamber'])
level("GD_Globals.General.LevelList",                       "Vault of the Warrior",           "Boss_Volcano_P",         ['Boss_Volcano_Dynamic', 'Boss_Volcano_Combat', 'Boss_Volcano_Audio', 'Boss_Volcano_FX', 'Boss_Volcano_Light', 'Boss_Volcano_Skybox', 'Boss_Volcano_Combat_Monster', 'Boss_Volcano_Cutscenes'])
level("GD_Globals.General.LevelList",                       "Eridium Blight",                 "Ash_P",                  ['Ash_Light', 'Ash_Combat', 'Ash_Dynamic', 'Ash_FX', 'Ash_Audio'])
level("GD_AlliumPackageDef.AlliumTG_LevelList",             "Gluttony Gulch",                 "Hunger_P",               ['HUNGER_AUDIO', 'Hunger_Dynamic', 'Hunger_Boss', 'Hunger_Mission_1', 'Hunger_Mission_2', 'Hunger_Mission_3', 'Hunger_Mission_Intro', 'Hunger_Machinery'])
level("GD_AlliumPackageDef.AlliumXmas_LevelList",           "Frost Bottom",                   "Xmas_P",                 ['Xmas_Audio', 'Xmas_Combat', 'Xmas_Dynamic', 'XMas_Light', 'Xmas_Skybox', 'Xmas_Boss', 'Xmas_Mission'])
level("GD_AnemonePackageDef.Anemone_LevelList",             "Helios Fallen",                  "Helios_P",               ['Helios_Audio', 'Helios_Light', 'Helios_Skybox', 'Helios_VFX', 'Helios_Mission_Main', 'Helios_Mission_Side', 'Helios_LD', 'Helios_Interactive', 'Helios_MoonshotCannon', 'Helios_UranusArena', 'Helios_Landscape', 'Helios_Floor1', 'Helios_LaserControlRoom', 'Helios_SideA', 'Helios_RobotFactory', 'Helios_SniperArea', 'Helios_MoxxiArea', 'Helios_HangarSpaceShips', 'Helios_Warehouse_Rockets', 'Helios_DahlMine_Before', 'Helios_DahlMine_After', 'Helios_Toggle_Sanctuary'])
level("GD_AnemonePackageDef.Anemone_LevelList",             "Paradise Sanctum",               "GaiusSanctuary_P",       ['GaiusSanctuary_Audio', 'GaiusSanctuary_Light', 'GaiusSanctuary_Cinema', 'GaiusSanctuary_SkyBox', 'GaiusSanctuary_VFX', 'GaiusSanctuary_MissionMain', 'GaiusSanctuary_MissionSide', 'GaiusSanctuary_Nav', 'GaiusSanctuary_Interactive', 'GaiusSanctuary_Moxxi', 'GaiusSanctuary_Scooter', 'GaiusSanctuary_Boss', 'GaiusSanctuary_Catwalk', 'GaiusSanctuary_MarcusHQ', 'GaiusSanctuary_Reactor'])
level("GD_AnemonePackageDef.Anemone_LevelList",             "The Backburner",                 "BackBurner_P",           ['BackBurner_Landscape', 'BackBurner_Mountain', 'BackBurner_Skybox', 'BackBurner_VFX', 'BackBurner_Audio', 'BackBurner_Light', 'BackBurner_Camp', 'BackBurner_LD', 'BackBUrner_Mission_Main', 'BackBurnerInteractive', 'BackBurner_Mission_Side', 'BackBurner_Toggle_Brick_ON', 'BackBurner_Toggle_Brick_OFF', 'BackBurner_Toggle_Moxxi_ON', 'BackBurner_Toggle_Moxxi_OFF', 'BackBurner_Toggle_Ellie_ON', 'BackBurner_Toggle_Ellie_OFF', 'BackBurner_Toggle_Tina_ON', 'BackBurner_Toggle_Tina_OFF', 'BackBurner_Toggle_Mordecai_ON', 'BackBurner_Toggle_Mordecai_OFF', 'BackBurner_Toggle_Zed_ON', 'BackBurner_Toggle_Zed_OFF', 'BackBurner_Toggle_Marcus_ON', 'BackBurner_Toggle_Marcus_OFF', 'BackBurner_Toggle_Claptrap_ON'])
level("GD_AnemonePackageDef.Anemone_LevelList",             "Fight for Sanctuary",            "SanctIntro_P",           ['SANCTINTRO_AUDIO', 'SanctIntro_Cinema', 'SanctIntro_Combat', 'SanctIntro_Dynamic', 'SanctIntro_Interactive', 'SanctIntro_Light', 'SanctIntro_Loot', 'SanctIntro_MissionMain', 'SanctIntro_MissionSide', 'SanctIntro_Nav', 'SanctIntro_SkyBox', 'SanctIntro_VFX', 'SanctIntro_Infection'])
level("GD_AnemonePackageDef.Anemone_LevelList",             "Dahl Abandon",                   "OldDust_P",              ['OldDust_Audio', 'OldDust_Light', 'OldDust_Skybox', 'OldDust_VFX', 'OldDust_Mission_Main', 'OldDust_Mission_Side', 'OldDust_LD', 'OldDust_Interactive', 'OldDust_Backburner', 'OldDust_Mountain', 'OldDust_SandwormEntrance', 'OldDust_Lair', 'OldDust_Landscape', 'OldDust_Approach', 'OldDust_DahlDoorBefore', 'OldDust_DahlDoorAfter', 'OldDust_Sanctuary_Before', 'OldDust_Sanctuary_After'])
level("GD_AnemonePackageDef.Anemone_LevelList",             "Mt. Scarab Research Center",     "ResearchCenter_P",       ['ResearchCenter_Audio', 'ResearchCenter_Cinema', 'ResearchCenter_Light', 'ResearchCenter_SkyBox', 'ResearchCenter_VFX', 'ResearchCenter_MissionSide', 'ResearchCenter_MissionMain', 'ResearchCenter_Interactive', 'ResearchCenter_Nav', 'ResearchCenter_Entrance', 'ResearchCenter_Lift', 'ResearchCenter_Dev', 'ResearchCenter_Research', 'ResearchCenter_Boss', 'ResearchCenter_Exterior', 'ResearchCenter_Prison'])
level("GD_AnemonePackageDef.Anemone_LevelList",             "Writhing Deep",                  "SandwormLair_P",         ['SandwormLair_Terrain', 'SandwormLair_GD', 'SandwormLair_VFX', 'SandwormLair_Audio', 'SandwormLair_LD', 'SandwormLair_Light'])
level("GD_AnemonePackageDef.Anemone_LevelList",             "The Burrows",                    "Sandworm_P",             ['Sandworm_Light', 'Sandworm_Skybox', 'Sandworm_Audio', 'Sandworm_VFX', 'Sandworm_Mission_Main', 'Sandworm_Mission_Side', 'Sandworm_Interactive', 'Sandworm_Side_HypoOathPart2', 'Sandworm_Encounters', 'Sandworm_Landscape', 'Sandworm_Tunnel', 'Sandworm_Zone_01', 'Sandworm_Zone_02', 'Sandworm_Zone_03', 'Sandworm_Zone_04', 'Sandworm_Zone_05'])
level("GD_AsterPackageDef.Aster_LevelList",                 "The Forest",                     "Dark_Forest_P",          ['Dark_Forest_Audio', 'Dark_Forest_Combat', 'Dark_Forest_Dynamic', 'Dark_Forest_FX', 'Dark_Forest_Light', 'Dark_Forest_Skybox', 'Dark_Forest_Missions'])
level("GD_AsterPackageDef.Aster_LevelList",                 "Immortal Woods",                 "Dead_Forest_P",          ['Dead_Forest_Audio', 'Dead_Forest_Combat', 'Dead_Forest_Dynamic', 'Dead_Forest_FX', 'Dead_Forest_Light', 'Dead_Forest_Skybox', 'Dead_Forest_Mission'])
level("GD_AsterPackageDef.Aster_LevelList",                 "Dragon Keep",                    "CastleKeep_P",           ['CastleKeep_Audio', 'CastleKeep_Combat', 'CastleKeep_Dynamic', 'CastleKeep_FX', 'CastleKeep_Light', 'CastleKeep_Skybox', 'CastleKeep_Mission'])
level("GD_AsterPackageDef.Aster_LevelList",                 "Unassuming Docks",               "Docks_P",                ['Docks_Audio', 'Docks_Combat', 'Docks_Dynamic', 'Docks_FX', 'DOCKS_LIGHT', 'Docks_Skybox', 'Docks_Mission'])
level("GD_AsterPackageDef.Aster_LevelList",                 "Flamerock Refuge",               "Village_P",              ['Village_Audio', 'Village_Dynamic', 'Village_FX', 'Village_Light', 'Village_Skybox', 'Village_Mission'])
level("GD_AsterPackageDef.Aster_LevelList",                 "Hatred's Shadow",                "CastleExterior_P",       ['CastleExterior_Audio', 'CastleExterior_Combat', 'CastleExterior_Dynamic', 'CastleExterior_FX', 'CastleExterior_Light', 'CastleExterior_Skybox', 'CastleExterior_Mission'])
level("GD_AsterPackageDef.Aster_LevelList",                 "Lair of Infinite Agony",         "Dungeon_P",              ['Dungeon_Audio', 'Dungeon_Combat', 'Dungeon_Dynamic', 'Dungeon_FX', 'Dungeon_Light', 'Dungeon_Skybox', 'Dungeon_Mission'])
level("GD_AsterPackageDef.Aster_LevelList",                 "Murderlin's Temple",             "TempleSlaughter_P",      ['TempleSlaughter_Audio', 'TempleSlaughter_Combat', 'TempleSlaughter_Light'])
level("GD_AsterPackageDef.Aster_LevelList",                 "Mines of Avarice",               "Mines_P",                ['Mines_Audio', 'Mines_Combat', 'Mines_Dynamic', 'Mines_FX', 'Mines_Light', 'Mines_Skybox', 'Mines_Mission'])
level("GD_AsterPackageDef.Aster_LevelList",                 "The Winged Storm",               "DungeonRaid_P",          ['DungeonRaid_Audio', 'DungeonRaid_Combat', 'DungeonRaid_Dynamic', 'DungeonRaid_FX', 'DungeonRaid_Light', 'DungeonRaid_Skybox'])
level("GD_FlaxPackageDef.Flax_LevelList",                   "Hallowed Hollow",                "Pumpkin_Patch_P",        ['PUMPKIN_PATCH_COMBAT', 'PUMPKIN_PATCH_AUDIO', 'Pumpkin_Patch_Dynamic', 'Pumpkin_Patch_FX', 'Pumpkin_Patch_Boss'])
level("GD_IrisPackageDef.LevelList.Iris_LevelList",         "The Beatdown",                   "Iris_DL2_P",             ['Iris_DL2_Audio', 'Iris_DL2_Combat', 'Iris_DL2_Dynamic', 'Iris_DL2_FX', 'Iris_DL2_Light', 'Iris_DL2_Skybox'])
level("GD_IrisPackageDef.LevelList.Iris_LevelList",         "Southern Raceway",               "Iris_Hub2_P",            ['Iris_Hub2_Audio', 'Iris_Hub2_Colosseum', 'Iris_Hub2_Combat', 'Iris_Hub2_Dynamic', 'Iris_Hub2_FX', 'Iris_Hub2_Light', 'Iris_Hub2_Raid', 'Iris_Hub2_Skybox'])
level("GD_IrisPackageDef.LevelList.Iris_LevelList",         "Badass Crater of Badassitude",   "Iris_Hub_P",             ['IRIS_HUB_SKYBOX', 'Iris_Hub_Light', 'Iris_Hub_Colosseum', 'Iris_Hub_Audio', 'Iris_Hub_Combat', 'Iris_Hub_Dynamic', 'Iris_Hub_FX', 'Iris_Hub_Race'])
level("GD_IrisPackageDef.LevelList.Iris_LevelList",         "Arena",                          "Iris_DL1_TAS_P",         ['Iris_DL1_TAS_Audio', 'Iris_DL1_TAS_Combat', 'Iris_DL1_TAS_Dynamic', 'Iris_DL1_TAS_FX', 'Iris_DL1_TAS_Light', 'Iris_DL1_TAS_Skybox'])
level("GD_IrisPackageDef.LevelList.Iris_LevelList",         "Pyro Pete's Bar",                "Iris_DL2_Interior_P",    ['Iris_DL2_Interior_Audio', 'Iris_DL2_Interior_Combat', 'Iris_DL2_Interior_Dynamic', 'Iris_DL2_Interior_Light', 'Iris_DL2_Interior_Raid'])
level("GD_IrisPackageDef.LevelList.Iris_LevelList",         "Arena",                          "Iris_DL1_P",             ['Iris_DL1_Audio', 'Iris_DL1_Battle', 'Iris_DL1_Combat', 'Iris_DL1_Dynamic', 'Iris_DL1_FX', 'Iris_DL1_Light', 'Iris_DL1_Skybox'])
level("GD_IrisPackageDef.LevelList.Iris_LevelList",         "Badass Crater Bar",              "Iris_Moxxi_P",           ['Iris_Moxxi_Audio'])
level("GD_IrisPackageDef.LevelList.Iris_LevelList",         "Forge",                          "Iris_DL3_P",             ['Iris_DL3_Light', 'Iris_DL3_Dynamic', 'Iris_DL3_Combat', 'Iris_DL3_Audio', 'Iris_DL3_FX', 'Iris_DL3_Skybox'])
level("GD_LobeliaPackageDef.LevelList",                     "The Raid on Digistruct Peak",    "TestingZone_P",          ['TESTINGZONE_LIGHT', 'TESTINGZONE_COMBAT', 'TestingZone_Audio'])
level("GD_NasturtiumPackageDef.NasturtiumEaster_LevelList", "Wam Bam Island",                 "Easter_P",               ['Easter_Audio', 'Easter_Boss', 'Easter_Combat', 'Easter_Dynamic', 'Easter_FX', 'Easter_Lights', 'Easter_Mission', 'Easter_Mission_1', 'Easter_Mission_2', 'Easter_Mission_Side', 'Easter_Skybox'])
level("GD_NasturtiumPackageDef.NasturtiumVday_LevelList",   "Rotgut Distillery",              "Distillery_P",           ['Distillery_Audio', 'Distillery_Boss', 'Distillery_Dynamic', 'Distillery_Combat', 'Distillery_FX', 'Distillery_IntroOutro', 'DISTILLERY_LIGHT2', 'Distillery_Mission', 'Distillery_Mission2', 'Distillery_Mission3', 'Distillery_Side_Mission', 'Distillery_Skybox'])
level("GD_OrchidPackageDef.LevelList.Orchid_LevelList",     "The Leviathan's Lair",           "Orchid_WormBelly_P",     ['Orchid_WormBelly_Audio', 'Orchid_WormBelly_Dynamic', 'Orchid_WormBelly_FX', 'Orchid_WormBelly_Light'])
level("GD_OrchidPackageDef.LevelList.Orchid_LevelList",     "Washburne Refinery",             "Orchid_Refinery_P",      ['Orchid_Refinery_Combat', 'Orchid_Refinery_Dynamic', 'Orchid_Refinery_Light', 'Orchid_Refinery_Raid', 'Orchid_Refinery_Audio'])
level("GD_OrchidPackageDef.LevelList.Orchid_LevelList",     "Wurmwater",                      "Orchid_SaltFlats_P",     ['Orchid_SaltFlats_Audio', 'Orchid_SaltFlats_Combat', 'Orchid_SaltFlats_Dynamic', 'Orchid_SaltFlats_FX', 'Orchid_SaltFlats_Light', 'Orchid_SaltFlats_Race', 'Orchid_SaltFlats_Refinery', 'Orchid_SaltFlats_Ship', 'Orchid_SaltFlats_Skybox'])
level("GD_OrchidPackageDef.LevelList.Orchid_LevelList",     "Oasis",                          "Orchid_OasisTown_P",     ['Orchid_OasisTown_Combat', 'Orchid_OasisTown_Dynamic', 'Orchid_OasisTown_Light', 'Orchid_OasisTown_Skybox', 'Orchid_OasisTown_Audio'])
level("GD_OrchidPackageDef.LevelList.Orchid_LevelList",     "Magnys Lighthouse",              "Orchid_Spire_P",         ['Orchid_Spire_Audio', 'Orchid_Spire_Combat', 'Orchid_Spire_Dynamic', 'Orchid_Spire_FX', 'Orchid_Spire_Light', 'Orchid_Spire_Skybox'])
level("GD_OrchidPackageDef.LevelList.Orchid_LevelList",     "The Rustyards",                  "Orchid_ShipGraveyard_P", ['Orchid_ShipGraveyard_Combat', 'Orchid_ShipGraveyard_Dynamic', 'Orchid_ShipGraveyard_Light', 'Orchid_ShipGraveyard_Audio', 'Orchid_ShipGraveyard_Skybox'])
level("GD_OrchidPackageDef.LevelList.Orchid_LevelList",     "Hayter's Folly",                 "Orchid_Caves_P",         ['Orchid_Caves_Audio', 'Orchid_Caves_Combat', 'ORCHID_CAVES_DYNAMIC', 'Orchid_Caves_FX', 'ORCHID_CAVES_LIGHT', 'Orchid_Caves_Raid_C', 'Orchid_Caves_Raid_P', 'ORCHID_CAVES_SKYBOX'])
level("GD_SagePackageDef.LevelList.Sage_LevelList",         "Ardorton Station",               "Sage_PowerStation_P",    ['Sage_PowerStation_Audio', 'Sage_PowerStation_Combat', 'Sage_PowerStation_Dynamic', 'Sage_PowerStation_FX', 'Sage_PowerStation_Light', 'Sage_PowerStation_Skybox'])
level("GD_SagePackageDef.LevelList.Sage_LevelList",         "Hunter's Grotto",                "Sage_Underground_P",     ['Sage_Underground_Audio', 'Sage_Underground_Combat', 'Sage_Underground_Dynamic', 'Sage_Underground_Light'])
level("GD_SagePackageDef.LevelList.Sage_LevelList",         "Candlerakk's Crag",              "Sage_Cliffs_P",          ['Sage_Cliffs_Audio', 'SAGE_CLIFFS_COMBAT', 'Sage_Cliffs_Dynamic', 'SAGE_CLIFFS_LIGHT', 'SAGE_CLIFFS_SKYBOX', 'Sage_Cliffs_Raid'])
level("GD_SagePackageDef.LevelList.Sage_LevelList",         "H.S.S. Terminus",                "Sage_HyperionShip_P",    ['Sage_HyperionShip_Audio', 'Sage_HyperionShip_Dynamic', 'Sage_HyperionShip_Light'])
level("GD_SagePackageDef.LevelList.Sage_LevelList",         "Scylla's Grove",                 "Sage_RockForest_P",      ['Sage_RockForest_Audio', 'Sage_RockForest_Combat', 'Sage_RockForest_Dynamic', 'Sage_RockForest_FX', 'Sage_RockForest_Light', 'Sage_RockForest_Skybox'])
#fmt: on
