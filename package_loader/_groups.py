from __future__ import annotations

from ._data import PackageLoad, PackageLoadAll, PackageLoadLevel, PackageLoaderError

import os
import sys
from functools import cache, cached_property
from typing import Generator, Iterable, Sequence

type LoadHandler = Generator[None, None, None]


@cache
def upk_sizes() -> dict[str, int]:
    upks: dict[str, int] = dict()
    game_dir = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
    for dirpath, _, filenames in os.walk(game_dir):
        for filename in filenames:
            filename = filename.lower()
            if filename.endswith(".upk"):
                upk_path = os.path.join(dirpath, filename)
                upks[os.path.splitext(filename)[0]] = os.stat(upk_path).st_size
    return upks


def expand_loads(loads: Sequence[PackageLoad]) -> Iterable[PackageLoad]:
    for load in loads:
        if isinstance(load, PackageLoadAll):
            yield from load
        elif not (isinstance(load, Sequence) and not len(load)):
            yield load


def get_load_packages(load: PackageLoad) -> list[str]:
    if isinstance(load, str):
        return [load.lower()]
    if isinstance(load, PackageLoadLevel):
        return list(load.packages)
    if isinstance(load, Sequence):
        for package in load:
            if not isinstance(package, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise PackageLoaderError(
                    f"Package Sequences must be of package names, not {package}"
                )
        return [package.lower() for package in load]
    raise PackageLoaderError(f"Invalid package load specification: {load}")


class PackageGroup:
    handler_loads: dict[LoadHandler, list[PackageLoad]]
    completed: bool = False

    def __init__(self, handler: LoadHandler, load: PackageLoad) -> None:
        self.handler_loads = {handler: [load]}

    def all_loads(self) -> Iterable[tuple[LoadHandler, PackageLoad]]:
        for handler, loads in self.handler_loads.items():
            for load in loads:
                yield handler, load

    def is_empty(self) -> bool:
        return not bool(self.handler_loads)

    @cached_property
    def packages(self) -> set[str]:
        packages: set[str] = set()
        packages.update(*(get_load_packages(load) for _, load in self.all_loads()))
        return packages

    def has_overlap(self, load: PackageLoad) -> bool:
        return bool(self.packages.intersection(get_load_packages(load)))

    def add_handler_load(self, handler: LoadHandler, load: PackageLoad) -> None:
        self.handler_loads.setdefault(handler, list()).append(load)
        self.packages.update(get_load_packages(load))

    def remove_handler(self, handler: LoadHandler) -> None:
        if handler in self.handler_loads:
            del self.handler_loads[handler]
            del self.packages

    def merge_group(self, group: PackageGroup) -> None:
        for handler, loads in group.handler_loads.items():
            for load in loads:
                self.add_handler_load(handler, load)

    def get_size_estimate(self) -> int:
        sizes = upk_sizes()
        return sum(sizes[package] for package in self.packages)

    def get_load_sequence(self) -> Sequence[str]:
        sequence: list[str] = list()

        for _, load in self.all_loads():
            if isinstance(load, str):
                load = load.lower()
                if load not in sequence:
                    sequence.append(load)

            elif isinstance(load, Sequence):
                packages = get_load_packages(load)
                sequence = packages + [package for package in sequence if package not in packages]

        for _, load in self.all_loads():
            if isinstance(load, PackageLoadLevel):
                sequence = list(load.packages) + [
                    package for package in sequence if package not in load.packages
                ]

        return sequence


def group_loads(handler_loads: dict[LoadHandler, Sequence[PackageLoad]]) -> list[PackageGroup]:
    groups: list[PackageGroup] = list()

    for handler, loads in handler_loads.items():
        for load in loads:
            groups_index = 0
            while groups_index < len(groups):
                group = groups[groups_index]
                groups_index += 1

                if group.has_overlap(load):
                    group.add_handler_load(handler, load)
                    for further_group in tuple(groups[groups_index:]):
                        if further_group.has_overlap(load):
                            group.merge_group(further_group)
                            groups.remove(further_group)
                    break
            else:
                groups.append(PackageGroup(handler, load))

    return groups
