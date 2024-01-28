"""Class for interacting with AWS services."""

from pathlib import Path

import boto3
import discord
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger

from valentina.utils import ValentinaConfig, errors


class AWSService:
    """Class for interacting with AWS services."""

    def __init__(self) -> None:
        """Initialize the AWS Service class with credentials.

        Args:
            aws_access_key_id (str): AWS access key ID.
            aws_secret_access_key (str): AWS secret access key.
            bucket_name (str): Name of the S3 bucket to use.
        """
        self.aws_access_key_id = ValentinaConfig().aws_access_key_id
        self.aws_secret_access_key = ValentinaConfig().aws_secret_access_key
        self.bucket_name = ValentinaConfig().s3_bucket_name

        if not self.aws_access_key_id or not self.aws_secret_access_key or not self.bucket_name:
            msg = "AWS"
            raise errors.MissingConfigurationError(msg)

        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            config=Config(retries={"max_attempts": 10, "mode": "standard"}),
        )
        self.bucket = self.bucket_name
        self.location = self.s3.get_bucket_location(Bucket=self.bucket)  # Ex. us-east-1

    def copy_object(self, source_key: str, dest_key: str) -> bool:
        """Copy an object within the S3 bucket or to another bucket.

        Args:
            source_key (str): Key of the source object.
            dest_key (str): Key for the destination object.

        Returns:
            bool: True if the copy is successful, False otherwise.
        """
        copy_source = {"Bucket": self.bucket, "Key": source_key}
        try:
            self.s3.copy_object(CopySource=copy_source, Bucket=self.bucket, Key=dest_key)
        except ClientError as e:
            logger.error(f"Failed to copy object {source_key} to {dest_key}: {e}")
            raise

        return True

    def delete_object(self, key: str) -> bool:
        """Delete an object from the S3 bucket.

        Attempt to delete the object from the S3 bucket using the provided key.
        If the deletion fails, log the error and return False.

        Args:
            key (str): Key of the object to delete from the S3 bucket.

        Returns:
            bool: True if the deletion is successful, False otherwise.
        """
        try:
            # Attempt to delete the object from the S3 bucket
            result = self.s3.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            logger.error(f"Failed to delete object {key}: {e}")
            raise

        # Check the DeleteMarker to confirm deletion
        return bool(result.get("DeleteMarker", False))

    def download_file(self, key: str, download_path: str) -> bool:
        """Download a file from the S3 bucket to Valentina's server.

        Args:
            key (str): Key of the object to download from the S3 bucket.
            download_path (str): Local path to save the downloaded file.

        Returns:
            bool: True if the download is successful, False otherwise.
        """
        try:
            self.s3.download_file(Bucket=self.bucket, Key=key, Filename=download_path)
        except ClientError as e:
            logger.error(f"Failed to download object {key}: {e}")
            raise

        return True

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str | None:
        """Generate a presigned URL for an object in the S3 bucket.

        A presigned URL grants temporary access to a specific S3 object without requiring AWS security credentials or permissions from the end user.

        Args:
            key (str): Key of the object.
            expiration (int): Time in seconds for the URL to expire. (Default: 1 hour)

        Returns:
            str | None: Presigned URL or None if the operation fails.
        """
        try:
            url = self.s3.generate_presigned_url(
                "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expiration
            )
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            return None

        return url

    @staticmethod
    def get_key_prefix(
        ctx: discord.ApplicationContext, object_type: str, **kwargs: str | int
    ) -> str:
        """Generate a key prefix for an object to be uploaded to Amazon S3.

        The key prefix is generated based on the area (guild, author, character, campaign, etc.)
        that the object belongs to. Some areas may require additional information like a character_id
        or a campaign_id.

        Args:
            ctx (ApplicationContext): Context of the command.
            object_type (str): Type of object to generate a key prefix for.
            **kwargs (str | int): Additional arguments to use in the key prefix, such as 'character_id' or 'campaign_id'.

        Returns:
            str: The generated key prefix.

        Raises:
            KeyError: If the object_type is not recognized or if required additional arguments are missing.
        """
        # TODO: Refactor to make kwargs more obvious
        guild_id = ctx.guild.id
        try:
            match object_type:
                case "guild":
                    return f"{guild_id}"

                case "author" | "user":
                    return f"{guild_id}/users/{ctx.author.id}"

                case "character":
                    # Access the key directly and catch KeyError
                    character_id = kwargs["character_id"]
                    return f"{guild_id}/characters/{character_id}"

                case "campaign":
                    # Access the key directly and catch KeyError
                    campaign_id = kwargs["campaign_id"]
                    return f"{guild_id}/campaigns/{campaign_id}"

                case _:
                    logger.error(f"Invalid object_type: {object_type}")
                    raise errors.ValidationError(object_type)

        except KeyError as e:
            logger.error(f"Missing required argument to _key_error: {e}")
            raise

    def get_url(self, key: str) -> str:
        """Get the URL for an object in the S3 bucket."""
        return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    def list_objects(self, prefix: str) -> list[str]:
        """List all objects in the S3 bucket with a given prefix.

        Use the S3 bucket's object filter method to find all objects that have keys starting with the given prefix. Return these keys as a list of strings.

        Args:
            prefix (str): The prefix to filter object keys by.

        Returns:
            list[str]: A list of object keys that start with the given prefix.
        """
        result = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [obj["Key"] for obj in result.get("Contents", [])]

    def object_exist(self, key: str) -> bool:
        """Check if an object exists in the S3 bucket.

        Attempt to load the object from the S3 bucket using the provided key.
        If the object does not exist, or an error occurs, log the error and return False.

        Args:
            key (str): Key of the object to check in the S3 bucket.

        Returns:
            bool: True if the object exists, False otherwise.
        """
        return key in self.list_objects(key)

    def upload_image(self, data: bytes, key: str, overwrite: bool = False) -> bool:
        """Upload a an image to an S3 bucket.

        Take the provided bytes data and attempt to upload it to the S3 bucket.
        If the upload fails, log the error and return False.

        Args:
            data (bytes): Data to upload.
            key (str): Name of the file in the bucket.
            overwrite (bool): Whether to overwrite the file if it already exists in the bucket.

        Returns:
            bool: True if the upload is successful, False otherwise.
        """
        # Check if the object exists and whether we should overwrite it
        if not overwrite and self.object_exist(key):
            raise errors.S3ObjectExistsError()

        try:
            # Attempt to upload the file to the S3 bucket
            self.s3.put_object(Key=key, Bucket=self.bucket, Body=data)
        except (ClientError, discord.HTTPException) as e:
            logger.error(f"Failed to upload file: {e}")
            return False

        return True

    def upload_file(
        self,
        ctx: discord.ApplicationContext,
        path: Path,
        name: str | None = None,
        overwrite: bool = False,
    ) -> bool:
        """Upload a file to an S3 bucket.

        Open the file in binary mode and attempt to upload it to the S3 bucket.
        If the upload fails, log the error and return False.

        Args:
            ctx (discord.ApplicationContext): Context of the command.
            path (Path): Path to the file to upload on the server.
            name (str | None): Optional name of the file in the bucket. Defaults to a name based on the guild ID.
            overwrite (bool): Whether to overwrite the file if it already exists in the bucket.

        Returns:
            bool: True if the upload is successful, False otherwise.
        """
        # Determine the name of the file in the S3 bucket
        key = name or f"{ctx.guild.id}/{path.name}"

        # Check if the object exists and whether we should overwrite it
        if not overwrite and self.object_exist(key):
            raise errors.S3ObjectExistsError()

        try:
            # Open the file in binary mode
            with path.open("rb") as data:
                # Attempt to upload the file to the S3 bucket
                self.s3.put_object(Key=key, Bucket=self.bucket, Body=data)
        except (ClientError, FileNotFoundError) as e:
            # Log the error and return False
            logger.error(f"Failed to upload file: {e}")
            return False

        return True
