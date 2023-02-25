from ...helpers.api_schema import Classification
from ...helpers.enums import (
    Resolution,
    Shape,
    TerrainType,
)
from ..readers.heightmap import Heightmap


def classify_heightmap(heightmap: Heightmap) -> Classification:
    classification = {}

    surface = heightmap.size[0] * heightmap.size[1]
    if surface < 256 * 256:
        classification["resolution"] = Resolution.LOW
    elif surface < 1024 * 1024:
        classification["resolution"] = Resolution.NORMAL
    else:
        classification["resolution"] = Resolution.HIGH

    aspect_ratio = heightmap.size[0] / heightmap.size[1]
    if aspect_ratio < 1:
        aspect_ratio = 1 / aspect_ratio

    if aspect_ratio < 1.2:
        classification["shape"] = Shape.SQUARE
    elif aspect_ratio < 2.5:
        classification["shape"] = Shape.RECTANGLE
    else:
        classification["shape"] = Shape.NARROW

    # Change the histogram in small bins, skipping sea-level.
    small_histogram = [0] * 16
    for i, value in enumerate(heightmap.histogram):
        if i == 0:
            continue
        small_histogram[i // 16] += value
    # Normalize the histogram.
    small_histogram = [value * 100 / (surface - heightmap.histogram[0]) for value in small_histogram]

    # Find all elevations with a certain surface amount. One hill doesn't
    # make a mountain (yes, this is meant ironically).
    common_elevations = [i for i, v in enumerate(small_histogram) if v >= 1]
    # And check the difference between the highest and lowest elevation.
    height_difference = max(common_elevations) - min(common_elevations)

    if height_difference > 9:
        classification["terrain-type"] = TerrainType.MOUNTAINOUS
    elif height_difference > 4:
        classification["terrain-type"] = TerrainType.HILLY
    elif height_difference > 1:
        classification["terrain-type"] = TerrainType.FLAT
    else:
        classification["terrain-type"] = TerrainType.VERY_FLAT

    return Classification().load(classification)
