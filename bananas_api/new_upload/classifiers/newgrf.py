from ...helpers.api_schema import Classification
from ...helpers.enums import (
    NewGRFSet,
    Palette,
)
from ..readers.newgrf import (
    Feature,
    NewGRF,
)


FEATURE_TO_CLASSIFICATION = {
    Feature.AIRCRAFT: NewGRFSet.AIRCRAFT,
    Feature.AIRPORT_TILES: NewGRFSet.AIRPORT,
    Feature.AIRPORTS: NewGRFSet.AIRPORT,
    Feature.BASECOSTS: NewGRFSet.ECONOMY,
    Feature.BASESET_BRIDGES: NewGRFSet.BRIDGE,
    Feature.BASESET_COLOUR_SCHEMA: NewGRFSet.GUI,
    Feature.BASESET_COMPANY_PROPERTY: NewGRFSet.TOWN,
    Feature.BASESET_FACES: NewGRFSet.GUI,
    Feature.BASESET_FONT: NewGRFSet.GUI,
    Feature.BASESET_GUI: NewGRFSet.GUI,
    Feature.BASESET_INFRA_AIR: NewGRFSet.AIRPORT,
    Feature.BASESET_INFRA_RAIL: NewGRFSet.RAIL_INFRA,
    Feature.BASESET_INFRA_ROAD: NewGRFSet.ROAD_INFRA,
    Feature.BASESET_INFRA_WATER: NewGRFSet.WATER_INFRA,
    Feature.BASESET_LANDSCAPE: NewGRFSet.LANDSCAPE,
    Feature.BASESET_SIGNALS: NewGRFSet.SIGNAL,
    Feature.BASESET_TREES: NewGRFSet.LANDSCAPE,
    Feature.BRIDGES: NewGRFSet.BRIDGE,
    Feature.CANALS: NewGRFSet.WATER_INFRA,
    Feature.CARGOS: NewGRFSet.ECONOMY,
    Feature.HOUSES: NewGRFSet.TOWN,
    Feature.INDUSTRIES: NewGRFSet.INDUSTRY,
    Feature.INDUSTRY_TILES: NewGRFSet.INDUSTRY,
    Feature.OBJECTS: NewGRFSet.OBJECT,
    Feature.RAILTYPES: NewGRFSet.RAIL_INFRA,
    Feature.ROAD_STOPS: NewGRFSet.ROAD_STOP,
    Feature.ROAD_VEHICLES: NewGRFSet.ROAD_VEHICLE,
    Feature.ROADTYPES: NewGRFSet.ROAD_INFRA,
    Feature.SHIPS: NewGRFSet.SHIP,
    Feature.SIGNALS: NewGRFSet.SIGNAL,
    Feature.SNOWLINE: NewGRFSet.LANDSCAPE,
    Feature.STATIONS: NewGRFSet.RAIL_STATION,
    Feature.TOWNNAMES: NewGRFSet.TOWNNAME,
    Feature.TRAINS: NewGRFSet.TRAIN,
    Feature.TRAMTYPES: NewGRFSet.ROAD_INFRA,
}

# This map indicates which feature (the one on the left) suppresses the other (the one on the right).
# For example, if a NewGRF has both Feature.AIRCRAFT and Feature.CARGOS, we only care about the
# Feature.AIRCRAFT, as that is the one that is most likely to be the main feature of the NewGRF.
SUPPRESS_LIST = [
    (Feature.AIRCRAFT, Feature.AIRPORT_TILES),
    (Feature.AIRCRAFT, Feature.AIRPORTS),
    (Feature.AIRCRAFT, Feature.BASESET_INFRA_AIR),
    (Feature.AIRCRAFT, Feature.CARGOS),
    (Feature.AIRPORTS, Feature.AIRPORT_TILES),
    (Feature.AIRPORTS, Feature.BASESET_INFRA_AIR),
    (Feature.BASECOSTS, Feature.CARGOS),
    (Feature.BASESET_INFRA_RAIL, Feature.BASESET_BRIDGES),
    (Feature.BASESET_INFRA_RAIL, Feature.BASESET_INFRA_ROAD),
    (Feature.BASESET_INFRA_ROAD, Feature.BASESET_BRIDGES),
    (Feature.BASESET_LANDSCAPE, Feature.SNOWLINE),
    (Feature.BRIDGES, Feature.BASESET_BRIDGES),
    (Feature.BRIDGES, Feature.BASESET_INFRA_RAIL),
    (Feature.BRIDGES, Feature.BASESET_INFRA_ROAD),
    (Feature.BRIDGES, Feature.RAILTYPES),
    (Feature.BRIDGES, Feature.ROADTYPES),
    (Feature.BRIDGES, Feature.TRAMTYPES),
    (Feature.CANALS, Feature.BASESET_INFRA_WATER),
    (Feature.CANALS, Feature.RAILTYPES),
    (Feature.CANALS, Feature.ROADTYPES),
    (Feature.CANALS, Feature.TRAMTYPES),
    (Feature.HOUSES, Feature.BASESET_INFRA_AIR),
    (Feature.HOUSES, Feature.BASESET_INFRA_RAIL),
    (Feature.HOUSES, Feature.BASESET_INFRA_ROAD),
    (Feature.HOUSES, Feature.BASESET_INFRA_WATER),
    (Feature.HOUSES, Feature.BRIDGES),
    (Feature.HOUSES, Feature.CARGOS),
    (Feature.INDUSTRIES, Feature.CARGOS),
    (Feature.INDUSTRIES, Feature.INDUSTRY_TILES),
    (Feature.INDUSTRIES, Feature.RAILTYPES),
    (Feature.INDUSTRIES, Feature.ROADTYPES),
    (Feature.INDUSTRIES, Feature.TRAMTYPES),
    (Feature.OBJECTS, Feature.BASECOSTS),
    (Feature.RAILTYPES, Feature.BASESET_INFRA_RAIL),
    (Feature.RAILTYPES, Feature.BASESET_SIGNALS),
    (Feature.RAILTYPES, Feature.BRIDGES),
    (Feature.ROAD_VEHICLES, Feature.BASESET_INFRA_RAIL),
    (Feature.ROAD_VEHICLES, Feature.BASESET_INFRA_ROAD),
    (Feature.ROAD_VEHICLES, Feature.BRIDGES),
    (Feature.ROAD_VEHICLES, Feature.CARGOS),
    (Feature.ROAD_VEHICLES, Feature.ROADTYPES),
    (Feature.ROAD_VEHICLES, Feature.TRAMTYPES),
    (Feature.ROADTYPES, Feature.BASESET_INFRA_ROAD),
    (Feature.ROADTYPES, Feature.BRIDGES),
    (Feature.ROADTYPES, Feature.TRAMTYPES),
    (Feature.SHIPS, Feature.BASESET_INFRA_WATER),
    (Feature.SHIPS, Feature.CANALS),
    (Feature.SHIPS, Feature.CARGOS),
    (Feature.SIGNALS, Feature.BASESET_SIGNALS),
    (Feature.STATIONS, Feature.BASESET_INFRA_AIR),
    (Feature.STATIONS, Feature.BASESET_INFRA_RAIL),
    (Feature.STATIONS, Feature.BASESET_INFRA_ROAD),
    (Feature.STATIONS, Feature.BASESET_INFRA_WATER),
    (Feature.TOWNNAMES, Feature.BASESET_INFRA_AIR),
    (Feature.TOWNNAMES, Feature.BASESET_INFRA_RAIL),
    (Feature.TOWNNAMES, Feature.BASESET_INFRA_ROAD),
    (Feature.TOWNNAMES, Feature.BASESET_INFRA_WATER),
    (Feature.TOWNNAMES, Feature.BASESET_TREES),
    (Feature.TOWNNAMES, Feature.CANALS),
    (Feature.TOWNNAMES, Feature.RAILTYPES),
    (Feature.TRAINS, Feature.BASESET_BRIDGES),
    (Feature.TRAINS, Feature.BASESET_INFRA_RAIL),
    (Feature.TRAINS, Feature.BASESET_INFRA_ROAD),
    (Feature.TRAINS, Feature.BRIDGES),
    (Feature.TRAINS, Feature.CARGOS),
    (Feature.TRAINS, Feature.RAILTYPES),
    (Feature.TRAMTYPES, Feature.BRIDGES),
]

MAJOR_FEATURE = (
    Feature.AIRCRAFT,
    Feature.AIRPORTS,
    Feature.BRIDGES,
    Feature.HOUSES,
    Feature.INDUSTRIES,
    Feature.RAILTYPES,
    Feature.ROAD_VEHICLES,
    Feature.ROADTYPES,
    Feature.SHIPS,
    Feature.SIGNALS,
    Feature.STATIONS,
    Feature.TOWNNAMES,
    Feature.TRAINS,
)

BASESET_FEATURE = (
    Feature.BASESET_BRIDGES,
    Feature.BASESET_COLOUR_SCHEMA,
    Feature.BASESET_COMPANY_PROPERTY,
    Feature.BASESET_FACES,
    Feature.BASESET_FONT,
    Feature.BASESET_GUI,
    Feature.BASESET_INFRA_AIR,
    Feature.BASESET_INFRA_RAIL,
    Feature.BASESET_INFRA_ROAD,
    Feature.BASESET_INFRA_WATER,
    Feature.BASESET_LANDSCAPE,
    Feature.BASESET_SIGNALS,
    Feature.BASESET_TREES,
    Feature.CANALS,  # Bit odd duck, but often it acts more like a baseset feature than anything else.
    Feature.OBJECTS,  # Same as above.
)


def classify_newgrf(newgrf: NewGRF) -> Classification:
    features = {}
    features.update(newgrf.features)

    classification = {}

    # No features known.
    if len(features) == 0:
        classification["set"] = NewGRFSet.UNKNOWN
        return Classification().load(classification)

    if Feature.SOUND_EFFECTS in features:
        classification["has-sound-effects"] = True
    else:
        classification["has-sound-effects"] = False

    # If over 50% of the sprites are 32bpp, classify as 32bpp.
    if len(features.get(Feature.SPRITES_32BPP, [])) > len(features.get(Feature.SPRITES, [])) / 2:
        classification["palette"] = Palette.BPP_32
    else:
        classification["palette"] = Palette.BPP_8

    # If over 50% of the sprites are zoomed in, classify as high resolution.
    if len(features.get(Feature.SPRITES_ZOOMIN, [])) > len(features.get(Feature.SPRITES, [])) / 2:
        classification["has-high-res"] = True
    else:
        classification["has-high-res"] = False

    # Features not used for further classification.
    for feature in (Feature.SOUND_EFFECTS, Feature.SPRITES, Feature.SPRITES_32BPP, Feature.SPRITES_ZOOMIN):
        if feature in features:
            del features[feature]

    # Remove features that are being suppressed by another.
    for feature, suppresses in SUPPRESS_LIST:
        if feature in features and suppresses in features:
            del features[suppresses]

    # Detect if the NewGRF contains a major feature.
    contains_major_feature = 0
    for feature in MAJOR_FEATURE:
        if feature in features:
            contains_major_feature += 1

    # When a major feature is present, we don't care about certain features.
    # This can also be written in the table above, but as these repeat themselves,
    # it is easier liker this.
    # Canal is a bit special, as it is a mix between a major and a baseset feature.
    if contains_major_feature > 0 or Feature.CANALS in features:
        if Feature.BASESET_FONT in features:
            del features[Feature.BASESET_FONT]
        if Feature.BASESET_GUI in features:
            del features[Feature.BASESET_GUI]
        if Feature.OBJECTS in features:
            del features[Feature.OBJECTS]
        if Feature.BASECOSTS in features:
            del features[Feature.BASECOSTS]
        if Feature.BASESET_COMPANY_PROPERTY in features:
            del features[Feature.BASESET_COMPANY_PROPERTY]

    # Landscape is a bit special, and the major feature only wins from it when there is nothing else left.
    if contains_major_feature and Feature.BASESET_LANDSCAPE in features and len(features) == 2:
        del features[Feature.BASESET_LANDSCAPE]

    # If all that we have left are major features, check if one stands out more than the rest.
    # If the biggest feature is four times as big as the rest, that is the major feature we
    # are going with. It is not perfect, but it is a good guess.
    if contains_major_feature > 1 and contains_major_feature == len(features):
        sorted_features = sorted(features.items(), key=lambda feature: -len(feature[1]))
        if len(sorted_features[0][1]) > len(sorted_features[1][1]) * 4:
            features = {sorted_features[0][0]: sorted_features[0][1]}

    # Detect if the NewGRF contains a baseset feature.
    contains_baseset_feature = 0
    for feature in BASESET_FEATURE:
        if feature in features:
            contains_baseset_feature += 1

    # Similar to major features, but now with baseset features.
    if contains_baseset_feature > 1 and contains_baseset_feature == len(features):
        sorted_features = sorted(features.items(), key=lambda feature: -len(feature[1]))
        if len(sorted_features[0][1]) > len(sorted_features[1][1]) * 2:
            features = {sorted_features[0][0]: sorted_features[0][1]}
        elif Feature.BASESET_LANDSCAPE in features:
            # If all entries are basesets, and landscape is one of them, this is most likely a "baseset" GRF.
            # We classify that as landscape.
            features = {Feature.BASESET_LANDSCAPE: features[Feature.BASESET_LANDSCAPE]}

    # Finally, if something heavily out-weights the rest, we can safely assume that is the
    # major feature.
    if len(features) > 1:
        sorted_features = sorted(features.items(), key=lambda feature: -len(feature[1]))
        if len(sorted_features[0][1]) > len(sorted_features[1][1]) * 10:
            features = {sorted_features[0][0]: sorted_features[0][1]}

    if len(features) == 0:
        classification["set"] = NewGRFSet.UNKNOWN
    elif len(features) == 1:
        classification["set"] = FEATURE_TO_CLASSIFICATION[list(features.keys())[0]]
    else:
        # If there are only vehicle-types in there, we classify it as a vehicle-set.
        for feature in features:
            if feature not in (Feature.TRAINS, Feature.AIRCRAFT, Feature.SHIPS, Feature.ROAD_VEHICLES):
                classification["set"] = NewGRFSet.MIXED
                break
        else:
            classification["set"] = NewGRFSet.VEHICLE

    return Classification().load(classification)
