#!/usr/bin/python3.6

import cloudinary
import cloudinary.uploader
from docs.conf import cloudinary_conf

cloudinary.config(cloud_name = cloudinary_conf['cloud_name'],
  api_key = cloudinary_conf['api_key'],
  api_secret = cloudinary_conf['api_secret'])


def upload_image(image, hash):
    """Takes a path to an image an uploads it. Return the Image URL"""

    #print(image,hash)

    try:
        result = cloudinary.uploader.upload(image, public_id = hash)
        URL = cloudinary.utils.cloudinary_url(result['public_id'])[0]
    except cloudinary.api.Error as e:
        print(e)
        print("Image already uploaded")
        URL = "http://res.cloudinary.com/destats/image/upload/" + hash
        print(URL)
    return(URL)