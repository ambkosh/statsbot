import cloudinary
import cloudinary.uploader
from conf import cloudinary_conf

cloudinary.config(cloud_name = cloudinary_conf['cloud_name'],
  api_key = cloudinary_conf['api_key'],
  api_secret = cloudinary_conf['api_secret'])


def upload_image(image, hash):
    """Takes a path to an image an uploads it. Return the Image URL"""

    result = cloudinary.uploader.upload(image, public_id = hash)
    URL = cloudinary.utils.cloudinary_url(result['public_id'])
    return(URL)