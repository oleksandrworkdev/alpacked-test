import mimetypes
import os

from pulumi import export, FileAsset
from pulumi_aws import s3, cloudfront, iam


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


web_bucket = s3.Bucket(
  's3-website-bucket',
  acl="private",
)

content_dir = "../public"
uploadDirectory(content_dir, web_bucket.id)

bucket_name = web_bucket.id
cf_origin_access_identity = cloudfront.OriginAccessIdentity("website-origin-access-identity", comment="Identity")

def s3_policy_for_bucket(bucket_name):
    return iam.get_policy_document(statements=[iam.GetPolicyDocumentStatementArgs(
    actions=["s3:GetObject"],
    resources=[f"arn:aws:s3:::{bucket_name}/*"],
    principals=[iam.GetPolicyDocumentStatementPrincipalArgs(
        type="AWS",
        identifiers=[cf_origin_access_identity.iam_arn],
    )],
)]).json

bucket_policy = s3.BucketPolicy("bucket-policy",
  bucket=bucket_name,
  policy=bucket_name.apply(s3_policy_for_bucket))

s3_origin_id = "myS3Origin"
s3_distribution = cloudfront.Distribution("s3Distribution",
    origins=[cloudfront.DistributionOriginArgs(
        domain_name=web_bucket.bucket_regional_domain_name,
        origin_id=s3_origin_id,
        s3_origin_config=cloudfront.DistributionOriginS3OriginConfigArgs(
            origin_access_identity=cf_origin_access_identity.cloudfront_access_identity_path
        )
    )],
    enabled=True,
    default_root_object="index.html",
    default_cache_behavior=cloudfront.DistributionDefaultCacheBehaviorArgs(
        allowed_methods=[
            "DELETE",
            "GET",
            "HEAD",
            "OPTIONS",
            "PATCH",
            "POST",
            "PUT",
        ],
        cached_methods=[
            "GET",
            "HEAD",
        ],
        target_origin_id=s3_origin_id,
        forwarded_values=cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
            query_string=False,
            cookies=cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                forward="none",
            ),
        ),
        viewer_protocol_policy="allow-all",
        min_ttl=0,
        default_ttl=3600,
        max_ttl=86400,
    ),
    tags={
        "Environment": "production",
    },
    restrictions=cloudfront.DistributionRestrictionsArgs(
      geo_restriction=cloudfront.DistributionRestrictionsGeoRestrictionArgs(
        restriction_type="none",
      )
    ),
    viewer_certificate=cloudfront.DistributionViewerCertificateArgs(
        cloudfront_default_certificate=True,
    ))


# Export the name of the bucket
export('bucket_name', web_bucket.id)
export('cf_distribution_url', s3_distribution.domain_name)
