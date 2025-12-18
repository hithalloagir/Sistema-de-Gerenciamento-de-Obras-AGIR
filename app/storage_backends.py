from cloudinary_storage.storage import MediaCloudinaryStorage


class CloudinaryMediaStorage(MediaCloudinaryStorage):
    resource_type = "auto"

