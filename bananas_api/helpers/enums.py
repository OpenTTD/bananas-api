from enum import Enum


class ContentType(Enum):
    AI = "ai"
    AI_LIBRARY = "ai-library"
    BASE_GRAPHICS = "base-graphics"
    BASE_MUSIC = "base-music"
    BASE_SOUNDS = "base-sounds"
    GAME_SCRIPT = "game-script"
    GAME_SCRIPT_LIBRARY = "game-script-library"
    HEIGHTMAP = "heightmap"
    NEWGRF = "newgrf"
    SCENARIO = "scenario"


class PackageType(Enum):
    # Identical to ContentType, but you cannot extend Enums
    AI = "ai"
    AI_LIBRARY = "ai-library"
    BASE_GRAPHICS = "base-graphics"
    BASE_MUSIC = "base-music"
    BASE_SOUNDS = "base-sounds"
    GAME_SCRIPT = "game-script"
    GAME_SCRIPT_LIBRARY = "game-script-library"
    HEIGHTMAP = "heightmap"
    NEWGRF = "newgrf"
    SCENARIO = "scenario"

    # Some extra filetypes that are internally used for validation
    SCRIPT_FILES = "scripts"
    SCRIPT_MAIN_FILE = "main-script"
    SOUND_FILES = "sounds"
    MUSIC_FILES = "music"


class License(Enum):
    GPL_v2 = "GPL v2"
    GPL_v3 = "GPL v3"
    LGPL_v2_1 = "LGPL v2.1"
    CC_0_v1_0 = "CC-0 v1.0"
    CC_BY_v3_0 = "CC-BY v3.0"
    CC_BY_SA_v3_0 = "CC-BY-SA v3.0"
    CC_BY_NC_SA_v3_0 = "CC-BY-NC-SA v3.0"
    CC_BY_NC_ND_v3_0 = "CC-BY-NC-ND v3.0"
    CUSTOM = "Custom"


class Branch(Enum):
    VANILLA = "vanilla"
    JGRPP = "jgrpp"


class Availability(Enum):
    NEW_GAMES = "new-games"
    SAVEGAMES_ONLY = "savegames-only"


class Status(Enum):
    OK = "OK"
    WARNINGS = "Warnings"
    ERRORS = "Errors"


class NewGRFSet(Enum):
    AIRCRAFT = "aircraft"
    AIRPORT = "airport"
    BRIDGE = "bridge"
    ECONOMY = "economy"
    GUI = "gui"
    INDUSTRY = "industry"
    LANDSCAPE = "landscape"
    MIXED = "mixed"
    OBJECT = "object"
    RAIL_INFRA = "rail-infra"
    RAIL_STATION = "rail-station"
    ROAD_INFRA = "road-infra"
    ROAD_STOP = "road-stop"
    ROAD_VEHICLE = "road-vehicle"
    SHIP = "ship"
    SIGNAL = "signal"
    TOWN = "town"
    TOWNNAME = "townname"
    TRAIN = "train"
    VEHICLE = "vehicle"
    WATER_INFRA = "water-infra"
    UNKNOWN = "unknown"


class Palette(Enum):
    BPP_32 = "32bpp"
    BPP_8 = "8bpp"
