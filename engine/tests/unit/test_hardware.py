"""Cross-platform local inference capacity and resource-policy tests."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arena.models.hardware import (
    GIB,
    HardwareInfo,
    LocalResourceError,
    assess_system,
    enforce_model_resources,
    estimate_model_memory,
    recommend_runtime,
)


def hardware(
    *,
    system: str = "linux",
    memory_gib: int = 16,
    available_gib: int = 12,
    cpus: int = 8,
    backend: str = "cpu",
    vram_gib: int = 0,
    apple: bool = False,
) -> HardwareInfo:
    return HardwareInfo(
        system=system,
        machine="arm64" if apple else "x86_64",
        logical_cpus=cpus,
        memory_bytes=memory_gib * GIB,
        available_memory_bytes=available_gib * GIB,
        apple_silicon=apple,
        gpu_backend=backend,  # type: ignore[arg-type]
        gpu_name="test gpu" if backend != "cpu" else None,
        vram_bytes=vram_gib * GIB if vram_gib else None,
    )


class TestSystemSpecification(unittest.TestCase):

    def test_minimum_is_os_independent(self):
        for system in ("linux", "darwin", "windows"):
            with self.subTest(system=system):
                result = assess_system(
                    hardware(system=system, memory_gib=8, available_gib=6, cpus=4),
                    free_disk_bytes=8 * GIB,
                )
                self.assertTrue(result.meets_minimum)

    def test_below_minimum_reports_all_capacity_failures(self):
        result = assess_system(
            hardware(memory_gib=4, available_gib=3, cpus=2),
            free_disk_bytes=4 * GIB,
        )
        self.assertFalse(result.meets_minimum)
        self.assertEqual(len(result.issues), 3)


class TestRuntimeRecommendation(unittest.TestCase):

    def test_cpu_system_selects_safe_default(self):
        result = recommend_runtime(hardware())
        self.assertEqual(result.model_pack, "default")
        self.assertEqual(result.gpu_layers, 0)
        self.assertEqual(result.speech_compute_type, "int8")

    def test_apple_silicon_uses_metal_but_cpu_speech(self):
        result = recommend_runtime(
            hardware(system="darwin", memory_gib=24, available_gib=18, apple=True, backend="metal")
        )
        self.assertEqual(result.model_pack, "pro")
        self.assertEqual(result.quantization, "Q4_K_M")
        self.assertEqual(result.gpu_layers, -1)
        # CTranslate2 does not expose a Metal backend.
        self.assertEqual(result.speech_device, "cpu")

    def test_nvidia_system_selects_cuda_speech(self):
        result = recommend_runtime(
            hardware(memory_gib=32, available_gib=24, backend="cuda", vram_gib=12)
        )
        self.assertEqual(result.model_pack, "pro")
        self.assertEqual(result.gpu_layers, -1)
        self.assertEqual(result.speech_device, "cuda")
        self.assertEqual(result.speech_compute_type, "float16")

    def test_windows_amd_uses_vulkan_for_llama_and_cpu_for_speech(self):
        result = recommend_runtime(
            hardware(
                system="windows",
                memory_gib=32,
                available_gib=24,
                backend="vulkan",
                vram_gib=12,
            )
        )
        self.assertEqual(result.gpu_layers, -1)
        self.assertEqual(result.speech_device, "cpu")


class TestPlatformMemoryDetection(unittest.TestCase):

    @patch("arena.models.hardware._run_probe")
    def test_macos_available_memory_uses_vm_stat(self, run_probe):
        from arena.models.hardware import _macos_available_memory

        run_probe.return_value = """Mach Virtual Memory Statistics: (page size of 4096 bytes)
Pages free:                               100.
Pages active:                             50.
Pages inactive:                          200.
Pages speculative:                        25.
"""
        self.assertEqual(_macos_available_memory(), 325 * 4096)

    @patch("arena.models.hardware._run_probe")
    def test_macos_available_memory_uses_system_pressure(self, run_probe):
        from arena.models.hardware import _macos_available_memory

        run_probe.side_effect = [
            """Mach Virtual Memory Statistics: (page size of 4096 bytes)
Pages free:                               100.
Pages inactive:                          200.
Pages speculative:                        25.
""",
            "System-wide memory free percentage: 35%",
        ]

        self.assertEqual(_macos_available_memory(16 * GIB), int(16 * GIB * 0.35))

    @patch("arena.models.hardware._linux_available_memory", return_value=12 * GIB)
    @patch("arena.models.hardware._cgroup_memory", return_value=(8 * GIB, 3 * GIB))
    @patch("arena.models.hardware._unix_physical_memory", return_value=32 * GIB)
    @patch("arena.models.hardware._probe_nvidia", return_value=(None, None))
    @patch("arena.models.hardware._probe_rocm", return_value=(None, None))
    @patch("arena.models.hardware.platform.machine", return_value="x86_64")
    @patch("arena.models.hardware.platform.system", return_value="Linux")
    def test_linux_uses_cgroup_limit_and_current_availability(self, *_mocks):
        from arena.models.hardware import detect_hardware

        result = detect_hardware()

        self.assertEqual(result.memory_bytes, 8 * GIB)
        self.assertEqual(result.available_memory_bytes, 3 * GIB)

class TestResourcePreflight(unittest.TestCase):

    def test_memory_estimate_includes_weight_overhead_and_context_cache(self):
        small_context = estimate_model_memory(2 * GIB, 1024)
        large_context = estimate_model_memory(2 * GIB, 8192)

        self.assertGreater(small_context, 2 * GIB)
        self.assertGreater(large_context, small_context)

    def test_model_larger_than_available_ram_is_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            model = Path(tempdir) / "large.gguf"
            with model.open("wb") as output:
                output.truncate(2 * GIB)

            with self.assertRaises(LocalResourceError):
                enforce_model_resources(
                    model,
                    context_size=4096,
                    gpu_layers=0,
                    info=hardware(memory_gib=4, available_gib=2),
                )

    def test_full_gpu_offload_larger_than_vram_is_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            model = Path(tempdir) / "large.gguf"
            with model.open("wb") as output:
                output.truncate(4 * GIB)

            with self.assertRaises(LocalResourceError):
                enforce_model_resources(
                    model,
                    context_size=4096,
                    gpu_layers=-1,
                    info=hardware(
                        memory_gib=16,
                        available_gib=12,
                        backend="cuda",
                        vram_gib=4,
                    ),
                )

    @patch("arena.models.hardware._run_probe")
    def test_nvidia_probe_is_bounded_and_parsed(self, run_probe):
        from arena.models.hardware import _probe_nvidia

        run_probe.return_value = "NVIDIA RTX Test, 8192"
        self.assertEqual(_probe_nvidia(), ("NVIDIA RTX Test", 8192 * 1024 ** 2))


if __name__ == "__main__":
    unittest.main()
