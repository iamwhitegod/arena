"""
Platform-specific video formatting for social media

Converts clips to optimal format, aspect ratio, and resolution for:
- TikTok, Instagram Reels, YouTube Shorts (9:16 vertical)
- YouTube, LinkedIn (16:9 horizontal)
- Instagram Feed, Twitter/X (1:1 square)
"""
from pathlib import Path
from typing import Dict, List, Optional, Literal
import subprocess
import json
from dataclasses import dataclass


@dataclass
class PlatformSpec:
    """Platform video specifications"""
    name: str
    width: int
    height: int
    aspect_ratio: str
    max_duration: int  # seconds
    max_file_size: int  # bytes
    recommended_bitrate: str  # e.g., "5M"
    audio_bitrate: str  # e.g., "128k"
    fps: int


# Platform specifications
PLATFORMS = {
    'tiktok': PlatformSpec(
        name='TikTok',
        width=1080,
        height=1920,
        aspect_ratio='9:16',
        max_duration=180,  # 3 minutes
        max_file_size=287_000_000,  # 287 MB
        recommended_bitrate='5M',
        audio_bitrate='128k',
        fps=30
    ),
    'instagram-reels': PlatformSpec(
        name='Instagram Reels',
        width=1080,
        height=1920,
        aspect_ratio='9:16',
        max_duration=90,  # 90 seconds
        max_file_size=100_000_000,  # 100 MB (conservative)
        recommended_bitrate='4M',
        audio_bitrate='128k',
        fps=30
    ),
    'youtube-shorts': PlatformSpec(
        name='YouTube Shorts',
        width=1080,
        height=1920,
        aspect_ratio='9:16',
        max_duration=60,  # 60 seconds
        max_file_size=100_000_000,  # No official limit, using 100MB
        recommended_bitrate='5M',
        audio_bitrate='128k',
        fps=30
    ),
    'youtube': PlatformSpec(
        name='YouTube (16:9)',
        width=1920,
        height=1080,
        aspect_ratio='16:9',
        max_duration=None,  # No limit
        max_file_size=256_000_000_000,  # 256 GB
        recommended_bitrate='8M',
        audio_bitrate='192k',
        fps=30
    ),
    'instagram-feed': PlatformSpec(
        name='Instagram Feed (Square)',
        width=1080,
        height=1080,
        aspect_ratio='1:1',
        max_duration=60,  # 60 seconds for feed videos
        max_file_size=100_000_000,  # 100 MB
        recommended_bitrate='4M',
        audio_bitrate='128k',
        fps=30
    ),
    'twitter': PlatformSpec(
        name='Twitter/X',
        width=1280,
        height=720,
        aspect_ratio='16:9',
        max_duration=140,  # 2:20
        max_file_size=512_000_000,  # 512 MB
        recommended_bitrate='6M',
        audio_bitrate='128k',
        fps=30
    ),
    'linkedin': PlatformSpec(
        name='LinkedIn',
        width=1920,
        height=1080,
        aspect_ratio='16:9',
        max_duration=600,  # 10 minutes
        max_file_size=5_000_000_000,  # 5 GB
        recommended_bitrate='8M',
        audio_bitrate='192k',
        fps=30
    ),
}


class PlatformFormatter:
    """
    Format video clips for specific social media platforms

    Handles:
    - Aspect ratio conversion (crop, pad, or scale)
    - Resolution targeting
    - Bitrate optimization
    - File size constraints
    - FPS normalization
    """

    CropStrategy = Literal['center', 'smart', 'top', 'bottom']
    PadStrategy = Literal['blur', 'black', 'white', 'color']

    def __init__(self):
        """Initialize platform formatter"""
        self.platforms = PLATFORMS

    def get_platform_spec(self, platform: str) -> PlatformSpec:
        """Get specification for a platform"""
        if platform not in self.platforms:
            available = ', '.join(self.platforms.keys())
            raise ValueError(
                f"Unknown platform: {platform}. "
                f"Available: {available}"
            )
        return self.platforms[platform]

    def list_platforms(self) -> List[str]:
        """List all available platforms"""
        return list(self.platforms.keys())

    def get_video_dimensions(self, video_path: Path) -> Dict:
        """Get video dimensions using ffprobe"""
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-select_streams', 'v:0',
            str(video_path)
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        data = json.loads(result.stdout.decode('utf-8'))
        stream = data['streams'][0]

        return {
            'width': int(stream['width']),
            'height': int(stream['height']),
            'aspect_ratio': stream.get('display_aspect_ratio', 'N/A'),
            'fps': self._parse_fps(stream.get('r_frame_rate', '30/1'))
        }

    def _parse_fps(self, fps_string: str) -> float:
        """Parse FPS from ffprobe format (e.g., '30/1')"""
        try:
            num, denom = fps_string.split('/')
            return float(num) / float(denom)
        except:
            return 30.0

    def format_for_platform(
        self,
        input_path: Path,
        output_path: Path,
        platform: str,
        crop_strategy: CropStrategy = 'center',
        pad_strategy: PadStrategy = 'blur',
        pad_color: str = '#000000',
        maintain_quality: bool = True
    ) -> Dict:
        """
        Format video for specific platform

        Args:
            input_path: Input video file
            output_path: Output video file
            platform: Platform name (tiktok, instagram-reels, youtube, etc.)
            crop_strategy: How to crop if needed (center, smart, top, bottom)
            pad_strategy: How to pad if needed (blur, black, white, color)
            pad_color: Color for padding (hex, e.g., '#000000')
            maintain_quality: Use higher quality settings

        Returns:
            Dict with formatting metadata
        """
        spec = self.get_platform_spec(platform)
        source_dims = self.get_video_dimensions(input_path)

        # Determine if we need to crop, pad, or just scale
        source_ar = source_dims['width'] / source_dims['height']
        target_ar = spec.width / spec.height

        # Build FFmpeg filter
        filters = []

        # FPS conversion if needed
        if source_dims['fps'] != spec.fps:
            filters.append(f"fps={spec.fps}")

        # Aspect ratio conversion
        if abs(source_ar - target_ar) > 0.01:  # Different aspect ratios
            if source_ar > target_ar:
                # Source is wider - need to crop or pad vertically
                filter_str = self._build_aspect_filter(
                    source_dims['width'],
                    source_dims['height'],
                    spec.width,
                    spec.height,
                    'wider',
                    crop_strategy,
                    pad_strategy,
                    pad_color
                )
            else:
                # Source is taller - need to crop or pad horizontally
                filter_str = self._build_aspect_filter(
                    source_dims['width'],
                    source_dims['height'],
                    spec.width,
                    spec.height,
                    'taller',
                    crop_strategy,
                    pad_strategy,
                    pad_color
                )
            filters.append(filter_str)
        else:
            # Same aspect ratio, just scale
            filters.append(f"scale={spec.width}:{spec.height}")

        # Build FFmpeg command
        command = [
            'ffmpeg',
            '-i', str(input_path),
            '-vf', ','.join(filters),
            '-c:v', 'libx264',
            '-preset', 'medium' if maintain_quality else 'fast',
            '-b:v', spec.recommended_bitrate,
            '-maxrate', spec.recommended_bitrate,
            '-bufsize', f"{int(spec.recommended_bitrate.rstrip('M')) * 2}M",
            '-c:a', 'aac',
            '-b:a', spec.audio_bitrate,
            '-ar', '48000',  # 48kHz audio
            '-movflags', '+faststart',
            '-y',
            str(output_path)
        ]

        # Execute
        try:
            subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            # Get output file info
            output_size = output_path.stat().st_size
            output_dims = self.get_video_dimensions(output_path)

            # Check constraints
            warnings = []
            if output_size > spec.max_file_size:
                warnings.append(
                    f"File size ({output_size / 1_000_000:.1f}MB) exceeds "
                    f"{spec.name} limit ({spec.max_file_size / 1_000_000:.1f}MB)"
                )

            return {
                'success': True,
                'platform': platform,
                'output_path': str(output_path),
                'source_dimensions': source_dims,
                'output_dimensions': output_dims,
                'file_size': output_size,
                'file_size_mb': round(output_size / 1_000_000, 2),
                'spec': {
                    'width': spec.width,
                    'height': spec.height,
                    'aspect_ratio': spec.aspect_ratio,
                    'bitrate': spec.recommended_bitrate
                },
                'warnings': warnings
            }

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to format for {spec.name}: {e.stderr.decode('utf-8')}"
            )

    def _build_aspect_filter(
        self,
        src_w: int,
        src_h: int,
        tgt_w: int,
        tgt_h: int,
        relationship: str,
        crop_strategy: CropStrategy,
        pad_strategy: PadStrategy,
        pad_color: str
    ) -> str:
        """
        Build FFmpeg filter for aspect ratio conversion

        Args:
            src_w, src_h: Source dimensions
            tgt_w, tgt_h: Target dimensions
            relationship: 'wider' or 'taller'
            crop_strategy: How to crop
            pad_strategy: How to pad
            pad_color: Padding color

        Returns:
            FFmpeg filter string
        """
        # Default: center crop to target aspect ratio, then scale
        if relationship == 'wider':
            # Source is wider (e.g., 16:9 → 9:16)
            # Calculate crop dimensions to match target aspect ratio
            new_width = int(src_h * tgt_w / tgt_h)

            if crop_strategy == 'center':
                x_offset = (src_w - new_width) // 2
            elif crop_strategy == 'smart':
                # Smart crop: slightly favor center-right for faces
                x_offset = int((src_w - new_width) * 0.45)
            elif crop_strategy == 'top':
                x_offset = 0
            else:  # bottom
                x_offset = src_w - new_width

            return f"crop={new_width}:{src_h}:{x_offset}:0,scale={tgt_w}:{tgt_h}"

        else:
            # Source is taller (e.g., 9:16 → 16:9)
            # Option 1: Crop (default)
            if crop_strategy != 'pad':
                new_height = int(src_w * tgt_h / tgt_w)

                if crop_strategy == 'center':
                    y_offset = (src_h - new_height) // 2
                elif crop_strategy == 'smart':
                    # Favor upper portion for faces/action
                    y_offset = int((src_h - new_height) * 0.35)
                elif crop_strategy == 'top':
                    y_offset = 0
                else:  # bottom
                    y_offset = src_h - new_height

                return f"crop={src_w}:{new_height}:0:{y_offset},scale={tgt_w}:{tgt_h}"

            # Option 2: Pad with blur background
            else:
                if pad_strategy == 'blur':
                    # Scale original to fit height, blur and scale background to full
                    return (
                        f"[0:v]scale={tgt_w}:{tgt_h}:force_original_aspect_ratio=decrease,"
                        f"boxblur=10:1[fg];"
                        f"[0:v]scale={tgt_w}:{tgt_h},boxblur=20:5[bg];"
                        f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
                    )
                else:
                    # Simple pad with color
                    color = pad_color.lstrip('#')
                    return (
                        f"scale={tgt_w}:{tgt_h}:force_original_aspect_ratio=decrease,"
                        f"pad={tgt_w}:{tgt_h}:(ow-iw)/2:(oh-ih)/2:color={color}"
                    )

    def batch_format(
        self,
        clips: List[Dict],
        output_dir: Path,
        platform: str,
        crop_strategy: CropStrategy = 'center',
        pad_strategy: PadStrategy = 'blur',
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Format multiple clips for a platform

        Args:
            clips: List of clip dicts with 'path' key
            output_dir: Output directory for formatted clips
            platform: Platform name
            crop_strategy: Crop strategy
            pad_strategy: Pad strategy
            progress_callback: Optional callback(current, total, result)

        Returns:
            List of formatting result dicts
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        total = len(clips)

        for i, clip in enumerate(clips, 1):
            input_path = Path(clip['path'])

            # Generate output filename with platform suffix
            stem = input_path.stem
            output_filename = f"{stem}_{platform}.mp4"
            output_path = output_dir / output_filename

            try:
                result = self.format_for_platform(
                    input_path,
                    output_path,
                    platform,
                    crop_strategy=crop_strategy,
                    pad_strategy=pad_strategy
                )

                result['clip_index'] = i
                result['original_clip'] = clip
                results.append(result)

                if progress_callback:
                    progress_callback(i, total, result)

            except Exception as e:
                error_result = {
                    'success': False,
                    'clip_index': i,
                    'error': str(e),
                    'original_clip': clip
                }
                results.append(error_result)

                if progress_callback:
                    progress_callback(i, total, error_result)

        return results

    def get_format_preview(
        self,
        source_width: int,
        source_height: int,
        platform: str
    ) -> Dict:
        """
        Preview how a video will be formatted without processing

        Args:
            source_width: Source video width
            source_height: Source video height
            platform: Target platform

        Returns:
            Dict describing the transformation
        """
        spec = self.get_platform_spec(platform)

        source_ar = source_width / source_height
        target_ar = spec.width / spec.height

        action = 'scale'
        if abs(source_ar - target_ar) > 0.01:
            if source_ar > target_ar:
                action = 'crop_horizontal'
                crop_pct = (1 - (target_ar / source_ar)) * 100
            else:
                action = 'crop_vertical'
                crop_pct = (1 - (source_ar / target_ar)) * 100
        else:
            crop_pct = 0

        return {
            'source': {
                'width': source_width,
                'height': source_height,
                'aspect_ratio': f"{source_ar:.2f}"
            },
            'target': {
                'width': spec.width,
                'height': spec.height,
                'aspect_ratio': spec.aspect_ratio,
                'platform': spec.name
            },
            'transformation': {
                'action': action,
                'crop_percentage': round(crop_pct, 1) if action != 'scale' else 0,
                'description': self._get_transformation_description(
                    action, crop_pct if action != 'scale' else 0
                )
            }
        }

    def _get_transformation_description(self, action: str, crop_pct: float) -> str:
        """Get human-readable transformation description"""
        if action == 'scale':
            return "Video will be scaled to fit (no cropping)"
        elif action == 'crop_horizontal':
            return f"Video will be cropped horizontally (~{crop_pct:.0f}% removed from sides)"
        else:
            return f"Video will be cropped vertically (~{crop_pct:.0f}% removed from top/bottom)"
