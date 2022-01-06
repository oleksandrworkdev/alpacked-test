import json
import mimetypes
import os

from pulumi import export, FileAsset
from pulumi_aws import s3


def uploadDirectory(path, bucket_name):
  for root, _, files in os.walk(path):
    for file in files:
      filepath = os.path.join(root, file)
      relative_path = os.path.relpath(filepath, path)
      mime_type, _ = mimetypes.guess_type(filepath)
      s3.BucketObject(relative_path,
        bucket=bucket_name,
        source=FileAsset(filepath),
        content_type=mime_type)


web_bucket = s3.Bucket('s3-website-bucket',
  website=s3.BucketWebsiteArgs(
      index_document="index.html",
      error_document="404.html",
  ))

content_dir = "../public"
uploadDirectory(content_dir, web_bucket.id)

def public_read_policy_for_bucket(bucket_name):
  return json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": "*",
        "Action": [
            "s3:GetObject"
        ],
        "Resource": [
            f"arn:aws:s3:::{bucket_name}/*",
        ]
    }]
  })

bucket_name = web_bucket.id
bucket_policy = s3.BucketPolicy("bucket-policy",
  bucket=bucket_name,
  policy=bucket_name.apply(public_read_policy_for_bucket))

# Export the name of the bucket
export('bucket_name', web_bucket.id)
export('website_url', web_bucket.website_endpoint)
