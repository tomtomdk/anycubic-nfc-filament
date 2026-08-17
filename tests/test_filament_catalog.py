from anycubic_nfc_app.filaments import FILAMENT_PRESETS, FILAMENT_SKUS
from anycubic_nfc_app.nfc_manager.spool_reader import SpoolData


EXPECTED_TYPES = [
    "PLA Basic",
    "PLA+",
    "PLA High Speed",
    "PLA Matte",
    "PLA Matte Dual",
    "PLA Silk",
    "PLA Silk Multi-Color",
    "PLA Glow",
    "PLA Metal",
    "PLA Marble",
    "PLA Galaxy",
    "PLA Special",
    "PLA-CF",
    "PETG",
    "PETG Translucent",
    "PETG-CF",
    "ABS",
    "ASA",
    "TPU 95A",
    "TPU 68D",
    "PC",
]


def test_current_filament_catalog_is_consistent():
    assert list(FILAMENT_PRESETS) == EXPECTED_TYPES
    assert list(FILAMENT_SKUS) == EXPECTED_TYPES
    assert all(len(filament_type) <= 20 for filament_type in EXPECTED_TYPES)


def test_custom_tag_preserves_specific_filament_type():
    specs = {
        **FILAMENT_PRESETS["PETG-CF"],
        "manufacturer": "AC",
        "color": "#2d2926",
    }

    tag = SpoolData(specs)
    result = tag.get_spool_specs()

    assert result["type"] == "PETG-CF"
    assert result["raw"]["sku"] == FILAMENT_SKUS["PETG-CF"]
    assert result["raw"]["is_custom"] is True


def test_legacy_material_names_decode_to_current_names():
    tag = SpoolData()
    tag._write_string(0x05, "HFGBL-101")
    tag._write_string(0x0f, "PLA Luminous")

    assert tag.get_spool_specs()["type"] == "PLA Glow"
