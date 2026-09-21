# -*- coding: utf-8 -*-
"""DXF test-fixture generator — creates minimal deterministic DXF drawings."""

from __future__ import annotations


def make_minimal_dxf(path: str) -> None:
    """A blank DXF with modelspace and a single default layer."""
    import ezdxf
    doc = ezdxf.new()
    doc.saveas(path)


def make_basic_entities_dxf(path: str) -> None:
    """DXF with LINE, CIRCLE, ARC, LWPOLYLINE on multiple layers."""
    import ezdxf
    doc = ezdxf.new()
    msp = doc.modelspace()
    doc.layers.add("WALLS")
    doc.layers.add("DIMENSIONS")
    doc.layers.add("HIDDEN")
    msp.add_line((0, 0, 0), (10, 0, 0), dxfattribs={"layer": "WALLS"})
    msp.add_line((10, 0, 0), (10, 5, 0), dxfattribs={"layer": "WALLS"})
    msp.add_line((10, 5, 0), (0, 5, 0), dxfattribs={"layer": "WALLS"})
    msp.add_line((0, 5, 0), (0, 0, 0), dxfattribs={"layer": "WALLS"})
    msp.add_circle((5, 2.5, 0), 1.0, dxfattribs={"layer": "HIDDEN"})
    msp.add_arc((5, 2.5, 0), 2.0, 0, 90, dxfattribs={"layer": "DIMENSIONS"})
    msp.add_lwpolyline([(0, 0), (3, 0), (3, 3)], dxfattribs={"layer": "WALLS"})
    doc.saveas(path)


def make_text_dxf(path: str) -> None:
    """DXF with TEXT and MTEXT (including Unicode)."""
    import ezdxf
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_text(
        "Simple label",
        dxfattribs={"insert": (1, 8, 0), "height": 0.8, "layer": "LABELS"},
    )
    msp.add_text(
        "\u0639\u0631\u0628\u064a\u30c6\u30b9\u30c8",
        dxfattribs={"insert": (1, 7, 0), "height": 0.6, "layer": "LABELS", "rotation": 15},
    )
    msp.add_mtext(
        "Multiline note\nSecond line.",
        dxfattribs={"insert": (1, 5, 0), "width": 6.0, "layer": "NOTES"},
    )
    msp.add_mtext(
        "Mix: Hello world",
        dxfattribs={"insert": (1, 3, 0), "width": 6.0, "layer": "NOTES"},
    )
    doc.saveas(path)


def make_block_insert_dxf(path: str) -> None:
    """DXF with a block definition and multiple INSERT references."""
    import ezdxf
    doc = ezdxf.new()
    msp = doc.modelspace()
    blk = doc.blocks.new("MYVALVE")
    blk.add_line((0, 0), (1, 1), dxfattribs={"layer": "BLOCK_GEOM"})
    blk.add_line((0.5, 0), (0.5, 1), dxfattribs={"layer": "BLOCK_GEOM"})
    blk.add_circle((0.5, 0.5), 0.25, dxfattribs={"layer": "BLOCK_GEOM"})
    msp.add_blockref(
        "MYVALVE", insert=(2, 2, 0),
        dxfattribs={"layer": "INSTALLS", "rotation": 0},
    )
    msp.add_blockref(
        "MYVALVE", insert=(5, 2, 0),
        dxfattribs={"layer": "INSTALLS", "rotation": 45},
    )
    msp.add_blockref(
        "MYVALVE", insert=(8, 2, 0),
        dxfattribs={"layer": "INSTALLS", "rotation": 90},
    )
    doc.saveas(path)


def make_dimension_dxf(path: str) -> None:
    """DXF with linear, aligned, and radial dimensions."""
    import ezdxf
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0, 0), (10, 0, 0), dxfattribs={"layer": "BASE"})
    # linear_dim(p1, p2, def_point) — def_point is the text position.
    msp.add_linear_dim((0, 0), (10, 0), (5, 2), dxfattribs={"layer": "DIM_LINEAR"})
    # aligned_dim(p1, p2, distance) — distance is perpendicular offset.
    msp.add_aligned_dim((0, 0), (5, 5), 1.5, dxfattribs={"layer": "DIM_ALIGNED"})
    # radius_dim(center, hole_corner, leader_length).
    msp.add_radius_dim((5, 5), (7, 5), 0.5, dxfattribs={"layer": "DIM_RADIAL"})
    doc.saveas(path)


def make_unsupported_entity_dxf(path: str) -> None:
    """DXF that includes an entity type not in our V1 supported set."""
    import ezdxf
    doc = ezdxf.new()
    msp = doc.modelspace()
    # SOLID is a valid DXF entity type but not in V1 supported list.
    msp.add_solid(((0, 0), (1, 0), (1, 1), (0, 1)), dxfattribs={"layer": "SHAPE"})
    msp.add_line((2, 0, 0), (3, 0, 0), dxfattribs={"layer": "LINE"})
    doc.saveas(path)


def make_malformed_dxf(path: str) -> None:
    """Write invalid text as a .dxf file so ezdxf.readfile fails."""
    with open(path, "w", encoding="ascii") as f:
        f.write("not a dxf file at all\n")


def make_empty_modelspace_dxf(path: str) -> None:
    """A valid DXF with no entities in modelspace."""
    import ezdxf
    doc = ezdxf.new()
    doc.saveas(path)


def make_3d_points_dxf(path: str) -> None:
    """DXF with 3D entities and Z coordinates."""
    import ezdxf
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0, 0), (5, 5, 5), dxfattribs={"layer": "AXIS"})
    msp.add_circle((5, 5, 5), 1.0, dxfattribs={"layer": "AXIS"})
    msp.add_lwpolyline([(0, 0, 0), (2, 1, 3), (4, 0, 2)], dxfattribs={"layer": "AXIS"})
    doc.saveas(path)
