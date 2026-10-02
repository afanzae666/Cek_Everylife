from pathlib import Path
from PIL import Image
import json


ROOT = Path(__file__).resolve().parents[1]

BASE_PATH = ROOT / "eyes_base.png"
IRIS_PATH = ROOT / "eyes_iris.png"

REPORT_PATH = ROOT / "eye_layer_audit.json"


def image_info(path: Path):
    if not path.exists():
        return {
            "exists": False,
            "path": str(path),
        }

    image = Image.open(path).convert("RGBA")

    alpha = image.getchannel("A")

    bbox = alpha.getbbox()

    alpha_values = list(alpha.getdata())

    opaque = sum(1 for a in alpha_values if a == 255)
    transparent = sum(1 for a in alpha_values if a == 0)
    partial = len(alpha_values) - opaque - transparent

    return {
        "exists": True,
        "filename": path.name,
        "format": image.format,
        "mode": image.mode,
        "size": list(image.size),
        "expected_size": [512, 512],
        "size_correct": image.size == (512, 512),
        "bbox": list(bbox) if bbox else None,
        "opaque_pixels": opaque,
        "partial_alpha_pixels": partial,
        "transparent_pixels": transparent,
        "total_pixels": len(alpha_values),
    }


def compare_layers(base_path: Path, iris_path: Path):
    result = {
        "comparison_possible": False,
    }

    if not base_path.exists() or not iris_path.exists():
        return result

    base = Image.open(base_path).convert("RGBA")
    iris = Image.open(iris_path).convert("RGBA")

    if base.size != iris.size:
        result["error"] = "Canvas sizes differ."
        return result

    base_alpha = base.getchannel("A")
    iris_alpha = iris.getchannel("A")

    base_pixels = list(base.getdata())
    iris_pixels = list(iris.getdata())
    base_a = list(base_alpha.getdata())
    iris_a = list(iris_alpha.getdata())

    overlap = 0
    iris_only = 0
    base_only = 0
    both_transparent = 0

    for ba, ia in zip(base_a, iris_a):
        base_visible = ba > 0
        iris_visible = ia > 0

        if base_visible and iris_visible:
            overlap += 1
        elif iris_visible:
            iris_only += 1
        elif base_visible:
            base_only += 1
        else:
            both_transparent += 1

    # Detect whether iris layer contains obvious non-white opaque colors.
    # This does NOT declare them wrong; it only reports them.
    iris_nonwhite_visible = 0

    for rgba, alpha in zip(iris_pixels, iris_a):
        if alpha > 0:
            r, g, b, _ = rgba
            if (r, g, b) != (255, 255, 255):
                iris_nonwhite_visible += 1

    result.update(
        {
            "comparison_possible": True,
            "canvas": list(base.size),
            "base_visible_pixels": sum(a > 0 for a in base_a),
            "iris_visible_pixels": sum(a > 0 for a in iris_a),
            "overlap_pixels": overlap,
            "iris_only_pixels": iris_only,
            "base_only_pixels": base_only,
            "both_transparent_pixels": both_transparent,
            "iris_nonwhite_visible_pixels": iris_nonwhite_visible,
        }
    )

    return result


def main():
    report = {
        "audit": "EveryLife Eye Layer Audit",
        "purpose": (
            "Non-destructive structural audit of eyes_base.png "
            "and eyes_iris.png."
        ),
        "files": {
            "eyes_base": image_info(BASE_PATH),
            "eyes_iris": image_info(IRIS_PATH),
        },
        "layer_comparison": compare_layers(BASE_PATH, IRIS_PATH),
    }

    # Basic pass/fail checks.
    base = report["files"]["eyes_base"]
    iris = report["files"]["eyes_iris"]

    checks = {}

    checks["base_exists"] = base.get("exists", False)
    checks["iris_exists"] = iris.get("exists", False)

    checks["base_512x512"] = base.get("size_correct", False)
    checks["iris_512x512"] = iris.get("size_correct", False)

    comparison = report["layer_comparison"]

    if comparison.get("comparison_possible"):
        checks["layers_same_canvas"] = (
            comparison.get("canvas") == [512, 512]
        )

        checks["iris_has_visible_pixels"] = (
            comparison.get("iris_visible_pixels", 0) > 0
        )

        checks["base_has_visible_pixels"] = (
            comparison.get("base_visible_pixels", 0) > 0
        )

        checks["no_layer_overlap"] = (
            comparison.get("overlap_pixels", 0) == 0
        )

    report["checks"] = checks

    if all(checks.values()):
        report["verdict"] = "STRUCTURAL PASS"
    else:
        report["verdict"] = "STRUCTURAL REVIEW REQUIRED"

    REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
