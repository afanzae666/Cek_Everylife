from pathlib import Path
from collections import Counter
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "screenshot" / "current"
OUT = ROOT / "audit" / "head_base_pixel_audit.txt"

FILES = [
    "infant_head_base.png",
    "toddler_head_base.png",
    "child_head_base.png",
    "teen_head_base.png",
    "young_adult_head_base.png",
    "adult_head_base.png",
    "senior_head_base.png",
]


def pct(value, total):
    return (value / total * 100.0) if total else 0.0


def audit(path):
    image = Image.open(path).convert("RGBA")
    pixels = list(image.getdata())

    total = len(pixels)

    opaque = [pixel for pixel in pixels if pixel[3] > 0]
    semi = [pixel for pixel in pixels if 0 < pixel[3] < 255]
    transparent = [pixel for pixel in pixels if pixel[3] == 0]

    rgb = [(r, g, b) for r, g, b, _ in opaque]

    grayscale = [
        pixel
        for pixel in rgb
        if pixel[0] == pixel[1] == pixel[2]
    ]

    average_rgb = tuple(
        sum(pixel[channel] for pixel in rgb) / len(rgb)
        if rgb
        else 0
        for channel in range(3)
    )

    channel_differences = [
        (
            abs(r - g),
            abs(g - b),
            abs(r - b),
        )
        for r, g, b in rgb
    ]

    max_rg = max(
        (value[0] for value in channel_differences),
        default=0,
    )

    max_gb = max(
        (value[1] for value in channel_differences),
        default=0,
    )

    max_rb = max(
        (value[2] for value in channel_differences),
        default=0,
    )

    average_rg = (
        sum(abs(r - g) for r, g, b in rgb) / len(rgb)
        if rgb
        else 0
    )

    average_gb = (
        sum(abs(g - b) for r, g, b in rgb) / len(rgb)
        if rgb
        else 0
    )

    average_rb = (
        sum(abs(r - b) for r, g, b in rgb) / len(rgb)
        if rgb
        else 0
    )

    # Diagnostic only:
    # positive values mean the image is warmer because R > B.
    warm_index = (
        sum(r - b for r, g, b in rgb) / len(rgb)
        if rgb
        else 0
    )

    luminance = [
        0.2126 * r +
        0.7152 * g +
        0.0722 * b
        for r, g, b in rgb
    ]

    common_colors = Counter(rgb).most_common(10)

    return {
        "size": f"{image.width}x{image.height}",
        "mode": image.mode,
        "total": total,
        "opaque": len(opaque),
        "semi": len(semi),
        "transparent": len(transparent),
        "alpha_coverage": pct(len(opaque), total),
        "grayscale_pct": pct(len(grayscale), len(rgb)),
        "average_rgb": average_rgb,
        "average_rg": average_rg,
        "average_gb": average_gb,
        "average_rb": average_rb,
        "max_rg": max_rg,
        "max_gb": max_gb,
        "max_rb": max_rb,
        "warm_index": warm_index,
        "luminance_min": min(luminance, default=0),
        "luminance_max": max(luminance, default=0),
        "common_colors": common_colors,
    }


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    lines = []

    lines.append("EVERYLIFE HEAD BASE PIXEL AUDIT")
    lines.append("=" * 72)
    lines.append("Source: screenshot/current")
    lines.append(
        "Only existing PNG assets are inspected. "
        "No asset is modified."
    )
    lines.append("")

    results = []

    for filename in FILES:
        path = SOURCE / filename

        if not path.exists():
            lines.append(f"MISSING: {filename}")
            lines.append("")
            continue

        result = audit(path)
        results.append((filename, result))

        lines.append(f"[{filename}]")
        lines.append(
            f"size={result['size']} "
            f"mode={result['mode']}"
        )

        lines.append(
            f"pixels={result['total']} "
            f"opaque={result['opaque']} "
            f"semi={result['semi']} "
            f"transparent={result['transparent']}"
        )

        lines.append(
            "opaque_alpha_coverage="
            f"{result['alpha_coverage']:.4f}%"
        )

        lines.append(
            "exact_grayscale_rgb="
            f"{result['grayscale_pct']:.4f}%"
        )

        average = result["average_rgb"]

        lines.append(
            "average_rgb="
            f"({average[0]:.3f}, "
            f"{average[1]:.3f}, "
            f"{average[2]:.3f})"
        )

        lines.append(
            "avg_abs_channel_diff: "
            f"R-G={result['average_rg']:.3f}, "
            f"G-B={result['average_gb']:.3f}, "
            f"R-B={result['average_rb']:.3f}"
        )

        lines.append(
            "max_abs_channel_diff: "
            f"R-G={result['max_rg']}, "
            f"G-B={result['max_gb']}, "
            f"R-B={result['max_rb']}"
        )

        lines.append(
            "warm_index_R_minus_B="
            f"{result['warm_index']:.3f}"
        )

        lines.append(
            "luminance_range="
            f"{result['luminance_min']:.3f}.."
            f"{result['luminance_max']:.3f}"
        )

        lines.append("most_common_10_rgb:")

        for color, count in result["common_colors"]:
            lines.append(
                f"  {color}: {count} pixels "
                f"({pct(count, result['opaque']):.4f}%)"
            )

        lines.append("")

    lines.append("CROSS-STAGE SUMMARY")
    lines.append("-" * 72)

    if results:
        grayscale_values = [
            result["grayscale_pct"]
            for _, result in results
        ]

        warm_values = [
            result["warm_index"]
            for _, result in results
        ]

        lines.append(
            "exact_grayscale_range="
            f"{min(grayscale_values):.4f}%.."
            f"{max(grayscale_values):.4f}%"
        )

        lines.append(
            "warm_index_range="
            f"{min(warm_values):.3f}.."
            f"{max(warm_values):.3f}"
        )

    lines.append("")

    report = "\n".join(lines) + "\n"

    OUT.write_text(report, encoding="utf-8")

    print(report)


if __name__ == "__main__":
    main()
