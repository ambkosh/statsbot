#!/usr/bin/python3.6

import cloudinary
import logging
import cloudinary.uploader
from docs.conf import cloudinary_conf
from botmodules.log import prepare_logger


# cloudinary.config(cloud_name = cloudinary_conf['cloud_name'],
#   api_key = cloudinary_conf['api_key'],
#   api_secret = cloudinary_conf['api_secret'])

prepare_logger('upload_image')
logger = logging.getLogger('upload_image')

def upload_image(image, hash):
    """Takes a path to an image an uploads it. Return the Image URL"""

    cloudinary.config(cloud_name=cloudinary_conf['cloud_name'],
                      api_key=cloudinary_conf['api_key'],
                      api_secret=cloudinary_conf['api_secret'])

    try:
        result = cloudinary.uploader.upload(image, public_id = hash)
        URL = cloudinary.utils.cloudinary_url(result['public_id'])[0]
        logger.debug("Uploaded image: %s", URL)
    except cloudinary.api.Error as e:
        logger.warn("Failed to upload image: %s", e)
        URL = "http://res.cloudinary.com/destats/image/upload/" + hash
    return(URL)