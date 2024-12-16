import boto3
import os
from dotenv import load_dotenv
import requests
from botocore.exceptions import ClientError
import uuid
import time
from functools import wraps

load_dotenv()

class S3Error(Exception):
    """Base exception for S3 operations"""
    pass

class S3DownloadError(S3Error):
    """Raised when downloading from source URL fails"""
    pass

class S3UploadError(S3Error):
    """Raised when uploading to S3 fails"""
    pass

class S3URLGenerationError(S3Error):
    """Raised when generating presigned URL fails"""
    pass

def retry_on_failure(max_attempts=3, delay_seconds=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay_seconds * (attempt + 1))  # Exponential backoff
                    continue
            raise last_exception
        return wrapper
    return decorator

class S3Handler:
    def __init__(self):
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_DEFAULT_REGION')
            )
            self.bucket_name = os.getenv('S3_BUCKET')
            
            if not all([os.getenv('AWS_ACCESS_KEY_ID'), 
                       os.getenv('AWS_SECRET_ACCESS_KEY'),
                       os.getenv('AWS_DEFAULT_REGION'),
                       self.bucket_name]):
                raise S3Error("Missing required AWS credentials or configuration")
                
            # Set CORS configuration
            cors_configuration = {
                'CORSRules': [{
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'HEAD'],
                    'AllowedOrigins': ['*'],  # For development. In production, specify your domain
                    'ExposeHeaders': ['ETag'],
                    'MaxAgeSeconds': 3000
                }]
            }
            
            # Apply CORS configuration
            try:
                self.s3_client.put_bucket_cors(
                    Bucket=self.bucket_name,
                    CORSConfiguration=cors_configuration
                )
            except Exception as e:
                print(f"Warning: Failed to set CORS policy: {str(e)}")
                
        except Exception as e:
            raise S3Error(f"Failed to initialize S3 client: {str(e)}")

    @retry_on_failure(max_attempts=3)
    def download_file(self, url):
        """Download file from URL with retry logic"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise S3DownloadError(f"Failed to download file from {url}: {str(e)}")

    @retry_on_failure(max_attempts=3)
    def upload_to_s3(self, file_content, key, content_type):
        """Upload file to S3 with retry logic"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
        except ClientError as e:
            raise S3UploadError(f"Failed to upload file to S3: {str(e)}")
        except Exception as e:
            raise S3UploadError(f"Unexpected error during S3 upload: {str(e)}")

    @retry_on_failure(max_attempts=3)
    def generate_presigned_url(self, key):
        """Generate presigned URL with retry logic"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                    'ResponseContentType': 'audio/mpeg',
                    'ResponseContentDisposition': 'inline',
                    'ResponseCacheControl': 'no-cache',
                    'ResponseExpires': '0'
                },
                ExpiresIn=3600,
                HttpMethod='GET'
            )
            
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                    'ResponseContentType': 'audio/mpeg',
                    'ResponseContentDisposition': 'attachment',
                    'ResponseCacheControl': 'no-cache',
                    'ResponseExpires': '0'
                },
                ExpiresIn=3600,
                HttpMethod='GET'
            )
            
            return {
                'play_url': url,
                'download_url': download_url
            }
        except ClientError as e:
            raise S3URLGenerationError(f"Failed to generate presigned URL: {str(e)}")

    def download_and_upload_to_s3(self, source_url, song_id):
        """Main method to handle file processing"""
        try:
            # Download the file with proper headers
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'audio/mpeg,audio/*;q=0.9,*/*;q=0.8'
            }
            
            response = requests.get(source_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Generate S3 key
            s3_key = f"songs/{song_id}/{os.path.basename(source_url)}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=response.content,
                ContentType='audio/mpeg'
            )
            
            # Generate presigned URLs with proper HTTP methods
            play_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ResponseContentType': 'audio/mpeg',
                    'ResponseContentDisposition': 'inline'
                },
                ExpiresIn=3600,  # 1 hour
                HttpMethod='GET'
            )
            
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ResponseContentType': 'audio/mpeg',
                    'ResponseContentDisposition': 'attachment'
                },
                ExpiresIn=3600,  # 1 hour
                HttpMethod='GET'
            )
            
            return {
                'play_url': play_url,
                'download_url': download_url
            }
            
        except Exception as e:
            # If anything fails, return original URL
            return {
                'play_url': source_url,
                'download_url': source_url
            }

    def cleanup_old_files(self, prefix="songs/", max_age_days=7):
        """Clean up old files from S3"""
        try:
            # List objects in the bucket with the given prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' in response:
                current_time = time.time()
                for obj in response['Contents']:
                    # Check if file is older than max_age_days
                    age_days = (current_time - obj['LastModified'].timestamp()) / (24 * 3600)
                    if age_days > max_age_days:
                        self.s3_client.delete_object(
                            Bucket=self.bucket_name,
                            Key=obj['Key']
                        )

        except Exception as e:
            print(f"Warning: Failed to cleanup old files: {str(e)}")
            # Don't raise the exception as this is a maintenance operation 