from collections.abc import Mapping
from marshmallow import (
    fields,
    Schema,
    validate,
    validates,
    validates_schema,
)
from marshmallow.exceptions import ValidationError

from .content_storage import get_indexed_package
from .enums import (
    Availability,
    Branch,
    Climate,
    ContentType,
    License,
    NewGRFSet,
    Palette,
    Resolution,
    Shape,
    Size,
    Status,
    TerrainType,
)
from .regions import REGIONS

DEPENDENCY_CHECK = True


def set_dependency_check(state):
    global DEPENDENCY_CHECK
    DEPENDENCY_CHECK = state


def _normalize_message(entry):
    if not isinstance(entry, Mapping):
        return entry

    if "_schema" in entry:
        return entry["_schema"]

    errors = {}
    for key, value in entry.items():
        errors[key] = _normalize_message(value)
    return errors


def normalize_message(exception):
    # Schema validation errors look like:
    #   "field": {"_schema": ["error1", "error2"]}
    #   "field": {0: {"_schema": ["error1", "error2"]}}
    # We like to unwind the "_schema" entry, to make a more consistent error
    # format.

    errors = {}
    for key, value in exception.normalized_messages().items():
        errors[key] = _normalize_message(value)

    return errors


class ValidateURL(validate.URL):
    def __call__(self, value):
        if not value:
            return value

        if len(value) > 95:
            raise ValidationError("Longer than maximum length 95.")

        return super().__call__(value)


class ValidateBytesLength(validate.Length):
    def __call__(self, value):
        return super().__call__(value.encode()).decode()

    def _format_error(self, value, message):
        return super()._format_error(value.decode(), message)


class ValidateRegion(validate.Validator):
    def __call__(self, value):
        if value not in REGIONS.keys():
            raise ValidationError("Invalid region.")

        return value


class OrderedSchema(Schema):
    class Meta:
        ordered = True


class ReplacedBy(OrderedSchema):
    unique_id = fields.String(data_key="unique-id", validate=validate.Length(equal=8))


class Global(OrderedSchema):
    read_only = ["archived", "replaced_by"]

    # Most of these limits are limitations in the OpenTTD client.
    name = fields.String(validate=ValidateBytesLength(max=31))
    archived = fields.Boolean()
    replaced_by = fields.Nested(ReplacedBy(), data_key="replaced-by", allow_none=True)
    description = fields.String(validate=ValidateBytesLength(max=511))
    url = fields.String(validate=ValidateURL())
    tags = fields.List(fields.String(validate=ValidateBytesLength(max=31)))
    regions = fields.List(fields.String(validate=ValidateRegion()), validate=validate.Length(max=10))


class Author(OrderedSchema):
    display_name = fields.String(data_key="display-name")
    openttd = fields.String(allow_none=True)
    github = fields.String(allow_none=True)
    developer = fields.String(allow_none=True)


class Authors(OrderedSchema):
    authors = fields.List(fields.Nested(Author))


class Dependency(OrderedSchema):
    content_type = fields.Enum(ContentType, data_key="content-type", by_value=True)
    unique_id = fields.String(data_key="unique-id", validate=validate.Length(equal=8))
    md5sum_partial = fields.String(data_key="md5sum-partial", validate=validate.Length(equal=8))

    @validates_schema
    def validate_dependency(self, data, **kwargs):
        if not DEPENDENCY_CHECK:
            return

        # Check the unique-id exists
        package = get_indexed_package(data["content_type"], data["unique_id"])
        if package is None:
            raise ValidationError(
                f"Package with unique-id '{data['unique_id']}' does not exist for {data['content_type'].value}."
            )

        # Check there is any version with that md5sum-partial
        for version in package["versions"]:
            if version["md5sum_partial"] == data["md5sum_partial"]:
                break
        else:
            raise ValidationError(
                f"No version with md5sum-partial '{data['md5sum_partial']}' exist for "
                f"{data['content_type'].value} with unique-id '{data['unique_id']}'."
            )


class Compatability(OrderedSchema):
    name = fields.Enum(Branch, by_value=True)
    conditions = fields.List(fields.String(), validate=validate.Length(min=1, max=2))

    @validates("conditions")
    def validate_conditions(self, data, **kwargs):
        if len(data) == 1:
            if not data[0].startswith((">= ", "< ")):
                raise ValidationError(
                    f"Condition can only mark the first client-version this version does or doesn't work for;"
                    f" expected '>= VERSION' or '< VERSION', got '{data[0]}'."
                )

            if data[0].startswith(">="):
                condition = data[0][3:]
            else:
                condition = data[0][2:]

            # Check if all parts of the version are integers
            try:
                [int(p) for p in condition.split(".")]
            except ValueError:
                raise ValidationError(
                    f"Versions in a condition should be a stable release in the form of '12.0' or '1.8.0',"
                    f" got '{condition}'."
                )
        else:
            if not data[0].startswith(">= "):
                raise ValidationError(
                    f"First condition can only mark the first client-version this version does work for;"
                    f" expected '>= VERSION', got '{data[0]}'."
                )
            if not data[1].startswith("< "):
                raise ValidationError(
                    f"Second condition can only mark the first client-version this version doesn't work for;"
                    f" expected '< VERSION', got '{data[0]}'."
                )

            # Check if all parts of the version are integers
            try:
                [int(p) for p in data[0][3:].split(".")]
            except ValueError:
                raise ValidationError(
                    f"Versions in a condition should be a stable release in the form of '12.0' or '1.8.0',"
                    f" got '{data[0][3:]}'."
                )

            # Check if all parts of the version are integers
            try:
                [int(p) for p in data[1][2:].split(".")]
            except ValueError:
                raise ValidationError(
                    f"Versions in a condition should be a stable release in the form of '12.0' or '1.8.0',"
                    f" got '{data[1][2:]}'."
                )


class Classification(OrderedSchema):
    set = fields.Enum(NewGRFSet, by_value=True)
    palette = fields.Enum(Palette, by_value=True)
    has_high_res = fields.Boolean(data_key="has-high-res")
    has_sound_effects = fields.Boolean(data_key="has-sound-effects")
    shape = fields.Enum(Shape, by_value=True)
    resolution = fields.Enum(Resolution, by_value=True)
    terrain_type = fields.Enum(TerrainType, by_value=True, data_key="terrain-type")
    size = fields.Enum(Size, by_value=True)
    climate = fields.Enum(Climate, by_value=True)


class VersionMinimized(Global):
    read_only = ["upload_date", "md5sum_partial", "classification", "filesize", "license", "availability"]
    read_only_for_new = ["upload_date", "md5sum_partial", "classification", "filesize", "availability"]

    version = fields.String(validate=ValidateBytesLength(max=15))
    license = fields.Enum(License, by_value=True)
    upload_date = fields.DateTime(data_key="upload-date", format="iso")
    md5sum_partial = fields.String(data_key="md5sum-partial", validate=validate.Length(equal=8))
    classification = fields.Nested(Classification())
    filesize = fields.Integer()
    availability = fields.Enum(Availability, by_value=True)
    dependencies = fields.List(fields.Nested(Dependency()))
    compatibility = fields.List(fields.Nested(Compatability()))


class Package(Global):
    read_only = ["content_type", "unique_id", "archived", "replaced_by"]

    content_type = fields.Enum(ContentType, data_key="content-type", by_value=True)
    unique_id = fields.String(data_key="unique-id", validate=validate.Length(equal=8))
    authors = fields.List(fields.Nested(Author))
    versions = fields.List(fields.Nested(VersionMinimized))


class Version(VersionMinimized):
    read_only = ["content_type", "unique_id"]

    content_type = fields.Enum(ContentType, data_key="content-type", by_value=True)
    unique_id = fields.String(data_key="unique-id", validate=validate.Length(equal=8))


class UploadStatusFiles(OrderedSchema):
    uuid = fields.String()
    filename = fields.String()
    filesize = fields.Integer()
    errors = fields.List(fields.String())


class UploadStatus(Version):
    files = fields.List(fields.Nested(UploadStatusFiles))
    warnings = fields.List(fields.String)
    errors = fields.List(fields.String)
    status = fields.Enum(Status, by_value=True)


class UploadNew(OrderedSchema):
    upload_token = fields.String(data_key="upload-token")


class UserToken(OrderedSchema):
    access_token = fields.String()
    token_type = fields.String()


class UserProfile(OrderedSchema):
    display_name = fields.String(data_key="display-name")


class ConfigUserAudience(OrderedSchema):
    name = fields.String()
    description = fields.String()
    settings_url = fields.String(data_key="settings-url")


class ConfigLicense(OrderedSchema):
    name = fields.String()
    deprecated = fields.Boolean()


class ConfigBranch(OrderedSchema):
    name = fields.String()
    description = fields.String()


class ConfigRegion(OrderedSchema):
    code = fields.String()
    name = fields.String()
    parent = fields.String()
