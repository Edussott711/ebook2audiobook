"""
System Resources Module
Provides utilities for detecting system resources (RAM, VRAM).
"""

import os
import platform
import subprocess


def get_ram() -> int:
    """
    Get the total amount of RAM in the system.

    Returns:
        int: Total RAM in gigabytes (GB)
    """
    import psutil
    vm = psutil.virtual_memory()
    return vm.total // (1024 ** 3)


def get_vram() -> int:
    """
    Get the total amount of VRAM (video memory) in the system.

    Supports multiple GPU vendors and operating systems:
    - NVIDIA (Windows, Linux, macOS) via pynvml
    - AMD (Windows via wmic, Linux via lspci)
    - Intel (Linux via sysfs)
    - macOS (OpenGL fallback)

    Returns:
        int: Total VRAM in gigabytes (GB), or 0 if detection fails
    """
    os_name = platform.system()

    # NVIDIA (Cross-Platform: Windows, Linux, macOS)
    try:
        from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)  # First GPU
        info = nvmlDeviceGetMemoryInfo(handle)
        vram = info.total
        return int(vram // (1024 ** 3))  # Convert to GB
    except ImportError:
        pass
    except Exception:
        pass

    # AMD (Windows)
    if os_name == "Windows":
        try:
            cmd = 'wmic path Win32_VideoController get AdapterRAM'
            output = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            lines = output.stdout.splitlines()
            vram_values = [int(line.strip()) for line in lines if line.strip().isdigit()]
            if vram_values:
                return int(vram_values[0] // (1024 ** 3))
        except Exception:
            pass

    # AMD (Linux)
    if os_name == "Linux":
        try:
            cmd = "lspci -v | grep -i 'VGA' -A 12 | grep -i 'preallocated' | awk '{print $2}'"
            output = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if output.stdout.strip().isdigit():
                return int(output.stdout.strip()) // 1024
        except Exception:
            pass

    # Intel (Linux Only)
    intel_vram_paths = [
        "/sys/kernel/debug/dri/0/i915_vram_total",  # Intel dedicated GPUs
        "/sys/class/drm/card0/device/resource0"  # Some integrated GPUs
    ]
    for path in intel_vram_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    vram = int(f.read().strip()) // (1024 ** 3)
                    return vram
            except Exception:
                pass

    # macOS (OpenGL Alternative)
    if os_name == "Darwin":
        try:
            from OpenGL.GL import glGetIntegerv
            from OpenGL.GLX import GLX_RENDERER_VIDEO_MEMORY_MB_MESA
            vram = int(glGetIntegerv(GLX_RENDERER_VIDEO_MEMORY_MB_MESA) // 1024)
            return vram
        except ImportError:
            pass
        except Exception:
            pass

    # Could not detect GPU VRAM
    msg = 'Could not detect GPU VRAM Capacity!'
    print(msg)
    return 0
