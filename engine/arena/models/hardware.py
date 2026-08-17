"""Cross-platform hardware detection and bounded local-runtime policy.

The policy is intentionally conservative.  Unknown GPU or memory information
never enables acceleration automatically, and model loading is rejected when
Arena can prove that the configured model cannot fit in available resources.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
from typing import Literal, Optional


GIB = 1024 ** 3
MAX_LOCAL_THREADS = 16
MAX_LOCAL_CONTEXT = 16_384
MAX_LOCAL_MODEL_BYTES = 16 * GIB
_COMMAND_TIMEOUT_SECONDS = 3.0

GPUBackend = Literal["cpu", "metal", "cuda", "rocm", "vulkan"]
Quantization = Literal["Q4_K_M", "Q5_K_M"]


@dataclass(frozen=True)
class SystemSpec:
    """Arena's OS-independent capacity policy for local inference."""

    logical_cpus: int
    memory_bytes: int
    free_disk_bytes: int
    gpu_vram_bytes: int = 0


# Minimum supported capacity uses the lite pack on CPU.  The recommended tier
# is the baseline for consistently good editorial throughput and quality on
# Linux, macOS, and Windows; a discrete GPU is optional.
MINIMUM_LOCAL_SPEC = SystemSpec(
    logical_cpus=4,
    memory_bytes=8 * GIB,
    free_disk_bytes=8 * GIB,
)
RECOMMENDED_LOCAL_SPEC = SystemSpec(
    logical_cpus=8,
    memory_bytes=16 * GIB,
    free_disk_bytes=16 * GIB,
    gpu_vram_bytes=8 * GIB,
)


@dataclass(frozen=True)
class HardwareInfo:
    system: str
    machine: str
    logical_cpus: int
    memory_bytes: Optional[int]
    available_memory_bytes: Optional[int]
    apple_silicon: bool
    gpu_backend: GPUBackend = "cpu"
    gpu_name: Optional[str] = None
    vram_bytes: Optional[int] = None


@dataclass(frozen=True)
class RuntimeRecommendation:
    threads: int
    context_size: int
    gpu_layers: int
    quantization: Quantization
    model_pack: Literal["lite", "default", "pro"]
    speech_device: Literal["cpu", "cuda"]
    speech_compute_type: Literal["int8", "float16"]


@dataclass(frozen=True)
class SpecAssessment:
    meets_minimum: bool
    meets_recommended: bool
    issues: tuple[str, ...]


class LocalResourceError(ValueError):
    """Raised before native model loading when a resource bound is unsafe."""


def _run_probe(command: list[str]) -> Optional[str]:
    if not command or shutil.which(command[0]) is None:
        return None
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            env={
                key: value
                for key, value in os.environ.items()
                if key.upper() in {
                    "COMSPEC",
                    "LANG",
                    "LC_ALL",
                    "PATH",
                    "PATHEXT",
                    "SYSTEMROOT",
                    "WINDIR",
                }
            },
            shell=False,
            timeout=_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _unix_physical_memory() -> Optional[int]:
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_PHYS_PAGES")
        if isinstance(page_size, int) and isinstance(pages, int):
            return page_size * pages
    except (AttributeError, OSError, ValueError):
        pass
    return None


def _windows_memory() -> tuple[Optional[int], Optional[int]]:
    if platform.system().lower() != "windows":
        return None, None

    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("memory_load", ctypes.c_ulong),
            ("total_physical", ctypes.c_ulonglong),
            ("available_physical", ctypes.c_ulonglong),
            ("total_page_file", ctypes.c_ulonglong),
            ("available_page_file", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("available_virtual", ctypes.c_ulonglong),
            ("available_extended_virtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.length = ctypes.sizeof(MemoryStatus)
    try:
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_physical), int(status.available_physical)
    except (AttributeError, OSError, ValueError):
        pass
    return None, None


def _linux_available_memory() -> Optional[int]:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, UnicodeError, ValueError, IndexError):
        pass
    return None


def _macos_available_memory(total_memory_bytes: Optional[int] = None) -> Optional[int]:
    """Estimate reclaimable memory using macOS's own pressure calculation.

    ``vm_stat`` page classes alone undercount memory that macOS can reclaim.
    ``memory_pressure -Q`` reports available memory as a percentage of total
    memory, so prefer the larger valid estimate when physical memory is known.
    """
    estimates: list[int] = []
    output = _run_probe(["vm_stat"])
    if output:
        try:
            page_size_match = next(
                part for part in output.splitlines()[0].split() if part.isdigit()
            )
            page_size = int(page_size_match)
            pages = 0
            available_labels = {"Pages free", "Pages inactive", "Pages speculative"}
            for line in output.splitlines()[1:]:
                label, separator, raw_value = line.partition(":")
                if separator and label in available_labels:
                    pages += int(raw_value.strip().rstrip("."))
            if pages > 0:
                estimates.append(pages * page_size)
        except (StopIteration, ValueError):
            pass

    if total_memory_bytes is not None and total_memory_bytes > 0:
        pressure_output = _run_probe(["memory_pressure", "-Q"])
        if pressure_output:
            match = re.search(
                r"System-wide memory free percentage:\s*(\d{1,3})%",
                pressure_output,
            )
            if match:
                percentage = int(match.group(1))
                if 0 <= percentage <= 100:
                    estimates.append(int(total_memory_bytes * percentage / 100))

    return max(estimates) if estimates else None


def _cgroup_memory() -> tuple[Optional[int], Optional[int]]:
    candidates = (
        (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory.current")),
        (
            Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
            Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"),
        ),
    )
    for limit_path, usage_path in candidates:
        try:
            raw = limit_path.read_text(encoding="ascii").strip()
            if raw != "max":
                limit = int(raw)
                # Some cgroup v1 hosts expose an effectively unlimited value.
                if 0 < limit < 1 << 60:
                    try:
                        usage = max(0, int(usage_path.read_text(encoding="ascii").strip()))
                    except (OSError, UnicodeError, ValueError):
                        return limit, limit
                    return limit, max(0, limit - usage)
        except (OSError, UnicodeError, ValueError):
            continue
    return None, None


def _probe_nvidia() -> tuple[Optional[str], Optional[int]]:
    output = _run_probe([
        "nvidia-smi",
        "--query-gpu=name,memory.total",
        "--format=csv,noheader,nounits",
    ])
    if not output:
        return None, None
    first = output.splitlines()[0]
    try:
        name, memory_mib = (part.strip() for part in first.rsplit(",", 1))
        return name[:256], int(float(memory_mib)) * 1024 ** 2
    except (TypeError, ValueError):
        return None, None


def _probe_rocm() -> tuple[Optional[str], Optional[int]]:
    output = _run_probe(["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--json"])
    if not output:
        return None, None
    try:
        data = json.loads(output)
        if not isinstance(data, dict) or not data:
            return None, None
        card = next(value for value in data.values() if isinstance(value, dict))
        name = next(
            (str(value) for key, value in card.items() if "card series" in key.lower()),
            "AMD GPU",
        )
        memory = next(
            (
                int(value)
                for key, value in card.items()
                if "total memory" in key.lower() and isinstance(value, (int, str))
            ),
            None,
        )
        return name[:256], memory
    except (StopIteration, TypeError, ValueError, json.JSONDecodeError):
        return None, None


def _probe_windows_gpu() -> tuple[Optional[str], Optional[int]]:
    if platform.system().lower() != "windows":
        return None, None
    output = _run_probe([
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json -Compress",
    ])
    if not output:
        return None, None
    try:
        parsed = json.loads(output)
        devices = parsed if isinstance(parsed, list) else [parsed]
        devices = [device for device in devices if isinstance(device, dict)]
        if not devices:
            return None, None
        device = max(devices, key=lambda item: int(item.get("AdapterRAM") or 0))
        return str(device.get("Name") or "Windows GPU")[:256], int(device.get("AdapterRAM") or 0) or None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None, None


def detect_hardware() -> HardwareInfo:
    system = platform.system().lower()
    machine = platform.machine().lower()
    logical_cpus = max(1, min(os.cpu_count() or 1, MAX_LOCAL_THREADS))

    windows_total, windows_available = _windows_memory()
    memory_bytes = windows_total or _unix_physical_memory()
    available_memory = windows_available
    if system == "linux":
        available_memory = _linux_available_memory()
        cgroup_limit, cgroup_available = _cgroup_memory()
        if cgroup_limit is not None:
            memory_bytes = min(memory_bytes or cgroup_limit, cgroup_limit)
            available_memory = min(
                available_memory or cgroup_available or cgroup_limit,
                cgroup_available if cgroup_available is not None else cgroup_limit,
            )
    elif system == "darwin":
        available_memory = _macos_available_memory(memory_bytes)

    apple_silicon = system == "darwin" and machine in {"arm64", "aarch64"}
    if apple_silicon:
        gpu_backend: GPUBackend = "metal"
        gpu_name, vram_bytes = "Apple Silicon unified memory", memory_bytes
    else:
        gpu_name, vram_bytes = _probe_nvidia()
        if gpu_name:
            gpu_backend = "cuda"
        else:
            gpu_name, vram_bytes = _probe_rocm()
            if gpu_name:
                gpu_backend = "rocm"
            else:
                gpu_name, vram_bytes = _probe_windows_gpu()
                gpu_backend = "vulkan" if gpu_name else "cpu"

    return HardwareInfo(
        system=system,
        machine=machine,
        logical_cpus=logical_cpus,
        memory_bytes=memory_bytes,
        available_memory_bytes=available_memory,
        apple_silicon=apple_silicon,
        gpu_backend=gpu_backend,
        gpu_name=gpu_name,
        vram_bytes=vram_bytes,
    )


def assess_system(
    info: Optional[HardwareInfo] = None,
    *,
    free_disk_bytes: Optional[int] = None,
) -> SpecAssessment:
    detected = info or detect_hardware()
    issues: list[str] = []
    if detected.logical_cpus < MINIMUM_LOCAL_SPEC.logical_cpus:
        issues.append(f"at least {MINIMUM_LOCAL_SPEC.logical_cpus} logical CPU cores are required")
    if detected.memory_bytes is not None and detected.memory_bytes < MINIMUM_LOCAL_SPEC.memory_bytes:
        issues.append("at least 8 GiB RAM is required")
    if free_disk_bytes is not None and free_disk_bytes < MINIMUM_LOCAL_SPEC.free_disk_bytes:
        issues.append("at least 8 GiB free disk space is required")

    meets_recommended = (
        detected.logical_cpus >= RECOMMENDED_LOCAL_SPEC.logical_cpus
        and detected.memory_bytes is not None
        and detected.memory_bytes >= RECOMMENDED_LOCAL_SPEC.memory_bytes
        and (free_disk_bytes is None or free_disk_bytes >= RECOMMENDED_LOCAL_SPEC.free_disk_bytes)
    )
    return SpecAssessment(not issues, meets_recommended, tuple(issues))


def recommend_runtime(info: Optional[HardwareInfo] = None) -> RuntimeRecommendation:
    detected = info or detect_hardware()
    memory = detected.memory_bytes or 0
    vram = detected.vram_bytes or 0

    if memory >= 24 * GIB and (detected.apple_silicon or vram >= 8 * GIB):
        pack: Literal["lite", "default", "pro"] = "pro"
        context = 12_288
        quantization: Quantization = "Q4_K_M"
    elif memory >= RECOMMENDED_LOCAL_SPEC.memory_bytes:
        pack = "default"
        context = 8192
        quantization = "Q4_K_M"
    else:
        pack = "lite"
        context = 4096
        quantization = "Q4_K_M"

    can_full_offload = (
        detected.apple_silicon and memory >= MINIMUM_LOCAL_SPEC.memory_bytes
    ) or (
        detected.gpu_backend in {"cuda", "rocm", "vulkan"} and vram >= 4 * GIB
    )
    speech_cuda = detected.gpu_backend == "cuda" and vram >= 4 * GIB
    return RuntimeRecommendation(
        threads=max(1, min(detected.logical_cpus, MAX_LOCAL_THREADS)),
        context_size=min(context, MAX_LOCAL_CONTEXT),
        gpu_layers=-1 if can_full_offload else 0,
        quantization=quantization,
        model_pack=pack,
        speech_device="cuda" if speech_cuda else "cpu",
        speech_compute_type="float16" if speech_cuda else "int8",
    )


def estimate_model_memory(model_bytes: int, context_size: int) -> int:
    """Conservative load estimate: weights, native overhead, and KV cache."""
    bounded_context = clamp_context(context_size)
    return int(model_bytes * 1.20) + max(512 * 1024 ** 2, bounded_context * 128 * 1024)


def enforce_model_resources(
    model_path: Path,
    *,
    context_size: int,
    gpu_layers: int,
    info: Optional[HardwareInfo] = None,
) -> None:
    detected = info or detect_hardware()
    try:
        model_bytes = model_path.stat().st_size if model_path.is_file() else sum(
            item.stat().st_size for item in model_path.rglob("*") if item.is_file()
        )
    except OSError as exc:
        raise LocalResourceError("Local model size could not be measured") from exc
    if model_bytes <= 0 or model_bytes > MAX_LOCAL_MODEL_BYTES:
        raise LocalResourceError("Local model exceeds Arena's runtime size limit")

    required = estimate_model_memory(model_bytes, context_size)
    memory_limit = detected.available_memory_bytes or detected.memory_bytes
    if memory_limit is not None and required > memory_limit:
        raise LocalResourceError(
            f"Local model needs about {required / GIB:.1f} GiB but only "
            f"{memory_limit / GIB:.1f} GiB RAM is available"
        )
    if gpu_layers == -1 and not detected.apple_silicon and detected.vram_bytes is not None:
        gpu_required = int(model_bytes * 1.10) + 512 * 1024 ** 2
        if gpu_required > detected.vram_bytes:
            raise LocalResourceError(
                f"Full GPU offload needs about {gpu_required / GIB:.1f} GiB VRAM but only "
                f"{detected.vram_bytes / GIB:.1f} GiB is available"
            )


def clamp_threads(value: Optional[int]) -> int:
    default = recommend_runtime().threads
    return max(1, min(value if value is not None else default, MAX_LOCAL_THREADS))


def clamp_context(value: int) -> int:
    return max(256, min(value, MAX_LOCAL_CONTEXT))
