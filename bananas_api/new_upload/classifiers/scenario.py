from ...helpers.api_schema import Classification
from ...helpers.enums import (
    Climate,
    Shape,
    Size,
    TerrainType,
)
from ..readers.scenario import (
    Landscape,
    Scenario,
)


def classify_scenario(scenario: Scenario) -> Classification:
    classification = {}

    surface = scenario.map_size[0] * scenario.map_size[1]
    if surface < 256 * 256:
        classification["size"] = Size.SMALL
    elif surface == 256 * 256:
        classification["size"] = Size.NORMAL
    elif surface <= 1024 * 1024:
        classification["size"] = Size.LARGE
    else:
        classification["size"] = Size.HUGE

    aspect_ratio = scenario.map_size[0] / scenario.map_size[1]
    if aspect_ratio < 1:
        aspect_ratio = 1 / aspect_ratio

    if aspect_ratio < 1.2:
        classification["shape"] = Shape.SQUARE
    elif aspect_ratio < 2.5:
        classification["shape"] = Shape.RECTANGLE
    else:
        classification["shape"] = Shape.NARROW

    # Only keep the lower heights and skip sea-level.
    small_histogram = [0] * 16
    for i in range(1, 15):
        small_histogram[i] = scenario.histogram[i]
    for i in range(15, 256):
        small_histogram[15] += scenario.histogram[i]
    # Normalize the histogram.
    small_histogram = [value * 100 / (surface - scenario.histogram[0]) for value in small_histogram]

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

    if scenario.landscape == Landscape.TEMPERATE:
        classification["climate"] = Climate.TEMPERATE
    elif scenario.landscape == Landscape.ARCTIC:
        classification["climate"] = Climate.SUB_ARCTIC
    elif scenario.landscape == Landscape.TROPIC:
        classification["climate"] = Climate.SUB_TROPICAL
    elif scenario.landscape == Landscape.TOYLAND:
        classification["climate"] = Climate.TOYLAND

    return Classification().load(classification)
