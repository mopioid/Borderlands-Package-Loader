from mods_base import ENGINE

from unrealsdk.logging import error, info, misc, warning  # pyright: ignore[reportUnusedImport]

import ctypes
from ctypes import c_size_t, c_long, c_ulong, c_void_p

import threading
from time import time

CRITICAL_MEMORY = int(1024 * 1024 * 1024 * 3)
IDLE_MEMORY_RANGE = 1024 * 128
IDLE_MEMORY_WAIT = 0.5

gc_barrier = threading.Barrier(parties=2)

memory_last_tick = 0
time_memory_within_range: float | None = None
garbage_collecting = True


GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
GetCurrentProcess.argtypes = ()
GetCurrentProcess.restype = c_void_p

CURRENT_PROCESS: c_void_p = GetCurrentProcess()


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = (
        ("cb", c_ulong),
        ("PageFaultCount", c_ulong),
        ("PeakWorkingSetSize", c_size_t),
        ("WorkingSetSize", c_size_t),
        ("QuotaPeakPagedPoolUsage", c_size_t),
        ("QuotaPagedPoolUsage", c_size_t),
        ("QuotaPeakNonPagedPoolUsage", c_size_t),
        ("QuotaNonPagedPoolUsage", c_size_t),
        ("PagefileUsage", c_size_t),
        ("PeakPagefileUsage", c_size_t),
        ("PrivateUsage", c_size_t),
    )


GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
GetProcessMemoryInfo.argtypes = [
    c_void_p,
    ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
    c_ulong,
]
GetProcessMemoryInfo.restype = c_long


def get_memory_usage() -> int:
    memory = PROCESS_MEMORY_COUNTERS()
    if GetProcessMemoryInfo(CURRENT_PROCESS, ctypes.byref(memory), ctypes.sizeof(memory)):
        return memory.PrivateUsage
    raise ctypes.WinError()


def is_memory_critical() -> bool:
    return get_memory_usage() > CRITICAL_MEMORY


def force_gc() -> None:
    global memory_last_tick, time_memory_within_range, garbage_collecting

    memory_last_tick = get_memory_usage()
    time_memory_within_range = None
    garbage_collecting = True

    ENGINE.TimeBetweenPurgingPendingKillObjects = 0.0
    ENGINE.GetCurrentWorldInfo().ForceGarbageCollection(True)
    ENGINE.TimeBetweenPurgingPendingKillObjects = float("inf")

    misc("Performing garbage collection, memory at", memory_last_tick)


def await_gc() -> None:
    gc_barrier.wait()


def pause_gc() -> None:
    ENGINE.TimeBetweenPurgingPendingKillObjects = float("inf")


def resume_gc() -> None:
    global garbage_collecting
    garbage_collecting = True
    ENGINE.TimeBetweenPurgingPendingKillObjects = 60.0
    ENGINE.GetCurrentWorldInfo().ForceGarbageCollection(True)


def tick_gc() -> None:
    global memory_last_tick, time_memory_within_range, garbage_collecting

    if garbage_collecting:
        memory = get_memory_usage()
        now = time()

        if memory_last_tick - memory > IDLE_MEMORY_RANGE:
            time_memory_within_range = None

        elif not time_memory_within_range:
            time_memory_within_range = now

        elif time_memory_within_range + IDLE_MEMORY_WAIT <= now:
            if memory > CRITICAL_MEMORY:
                warning("Garbage collection completed, memory still critial at", memory)
            else:
                misc("Garbage collection completed, memory at", memory)

            garbage_collecting = False
            if gc_barrier.n_waiting:
                gc_barrier.wait()

        memory_last_tick = memory

    elif gc_barrier.n_waiting:
        force_gc()
