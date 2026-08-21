from mods_base import ENGINE
from unrealsdk.logging import error, info, misc, warning  # pyright: ignore[reportUnusedImport]

import ctypes
from ctypes import c_size_t, c_long, c_ulong, c_void_p
from time import time

CRITICAL_MEMORY = int(1024 * 1024 * 1024 * 2.8)
IDLE_MEMORY_RANGE = 1024 * 128
IDLE_MEMORY_WAIT = 1.5

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


def is_memory_critical(needed: int = 0) -> bool:
    return get_memory_usage() + needed > CRITICAL_MEMORY


def force_gc() -> None:
    global memory_last_tick, time_memory_within_range, garbage_collecting

    memory_last_tick = get_memory_usage()
    time_memory_within_range = None
    garbage_collecting = True

    ENGINE.GetCurrentWorldInfo().ForceGarbageCollection(True)
    # get_pc().ConsoleCommand("obj garbage")

    # misc("Performing garbage collection, memory at", memory_last_tick)


def tick_gc():
    global memory_last_tick, time_memory_within_range, garbage_collecting

    if not garbage_collecting:
        return

    memory = get_memory_usage()
    now = time()

    if memory_last_tick - memory > IDLE_MEMORY_RANGE:
        time_memory_within_range = None

    elif not time_memory_within_range:
        time_memory_within_range = now

    elif time_memory_within_range + IDLE_MEMORY_WAIT <= now:
        garbage_collecting = False

        if is_memory_critical():
            warning("Memory critial at", memory)

    memory_last_tick = memory
