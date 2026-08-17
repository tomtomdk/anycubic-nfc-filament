from typing import Any


def _preset(
    filament_type: str,
    nozzle_min: int,
    nozzle_max: int,
    bed_min: int,
    bed_max: int,
) -> dict[str, Any]:
    return {
        "type": filament_type,
        "range_a": {
            "nozzle_min": nozzle_min,
            "nozzle_max": nozzle_max,
        },
        "bed_min": bed_min,
        "bed_max": bed_max,
        "diameter": 1.75,
        "length": 330,
        "weight": 1000,
    }


# Current Anycubic filament families. Refill products share the same material
# profile as their spooled equivalent and are intentionally not duplicated.
FILAMENT_PRESETS: dict[str, dict[str, Any]] = {
    "PLA Basic": _preset("PLA Basic", 190, 230, 55, 65),
    "PLA+": _preset("PLA+", 190, 230, 55, 65),
    "PLA High Speed": {
        "type": "PLA High Speed",
        "range_a": {
            "speed_min": 50,
            "speed_max": 150,
            "nozzle_min": 190,
            "nozzle_max": 210,
        },
        "range_b": {
            "speed_min": 150,
            "speed_max": 300,
            "nozzle_min": 210,
            "nozzle_max": 230,
        },
        "range_c": {
            "speed_min": 300,
            "speed_max": 600,
            "nozzle_min": 230,
            "nozzle_max": 260,
        },
        "bed_min": 55,
        "bed_max": 65,
        "diameter": 1.75,
        "length": 330,
        "weight": 1000,
    },
    "PLA Matte": _preset("PLA Matte", 190, 230, 60, 65),
    "PLA Matte Dual": _preset("PLA Matte Dual", 190, 230, 60, 65),
    "PLA Silk": _preset("PLA Silk", 210, 240, 55, 65),
    "PLA Silk Multi-Color": _preset("PLA Silk Multi-Color", 210, 240, 55, 65),
    "PLA Glow": _preset("PLA Glow", 200, 230, 60, 70),
    "PLA Metal": _preset("PLA Metal", 200, 230, 50, 60),
    "PLA Marble": _preset("PLA Marble", 200, 230, 55, 65),
    "PLA Galaxy": _preset("PLA Galaxy", 200, 230, 60, 65),
    "PLA Special": _preset("PLA Special", 190, 230, 55, 65),
    "PLA-CF": _preset("PLA-CF", 210, 250, 55, 70),
    "PETG": _preset("PETG", 230, 250, 60, 70),
    "PETG Translucent": _preset("PETG Translucent", 230, 250, 60, 70),
    "PETG-CF": _preset("PETG-CF", 240, 270, 65, 70),
    "ABS": _preset("ABS", 240, 280, 80, 100),
    "ASA": _preset("ASA", 255, 275, 80, 100),
    "TPU 95A": _preset("TPU 95A", 195, 230, 50, 60),
    "TPU 68D": _preset("TPU 68D", 210, 250, 35, 60),
    "PC": _preset("PC", 270, 290, 100, 120),
}


# Known NFC SKUs are retained where available. New finish/compound variants use
# the closest compatible family SKU while their exact type is stored separately.
FILAMENT_SKUS: dict[str, str] = {
    "PLA Basic": "AHPLBK-101",
    "PLA+": "AHPLPBK-102",
    "PLA High Speed": "AHHSBK-102",
    "PLA Matte": "HYGBK-101",
    "PLA Matte Dual": "HYGBK-101",
    "PLA Silk": "HSCWH-101",
    "PLA Silk Multi-Color": "HSCWH-101",
    "PLA Glow": "HFGBL-101",
    "PLA Metal": "AHPLBK-101",
    "PLA Marble": "AHPLBK-101",
    "PLA Galaxy": "AHPLBK-101",
    "PLA Special": "AHPLBK-101",
    "PLA-CF": "AHPLBK-101",
    "PETG": "HPEBK-103",
    "PETG Translucent": "HPEBK-103",
    "PETG-CF": "HPEBK-103",
    "ABS": "HABBK-102",
    "ASA": "HASBK-101",
    "TPU 95A": "HTPBK-101",
    "TPU 68D": "HTPBK-101",
    "PC": "CUSTOM-PC",
}


SKU_PREFIX_TYPES: dict[str, str] = {
    "AHPL": "PLA Basic",
    "AHPLP": "PLA+",
    "AHHS": "PLA High Speed",
    "HYG": "PLA Matte",
    "HSC": "PLA Silk",
    "HPE": "PETG",
    "HAS": "ASA",
    "HAB": "ABS",
    "HTP": "TPU 95A",
    "HFG": "PLA Glow",
}
