import boto3
import click
import os

from ..helpers.click import click_additional_options

_bucket_name = None


class Storage:
    def __init__(self):
        if _bucket_name is None:
            raise Exception("--storage-s3-bucket has to be given if storage is s3")

        self._s3 = boto3.client("s3")

    def move_to_storage(self, filename, content_type, unique_id, md5sum):
        folder = f"{content_type.value}/{unique_id}"
        new_filename = f"{folder}/{md5sum}.tar.gz"

        with open(filename, "rb") as fp:
            self._s3.put_object(Body=fp, Bucket=_bucket_name, Key=new_filename)
        os.unlink(filename)


@click_additional_options
@click.option(
    "--storage-s3-bucket", help="Name of the bucket to upload the files. (storage=s3 only)",
)
def click_storage_s3(storage_s3_bucket):
    global _bucket_name

    _bucket_name = storage_s3_bucket
