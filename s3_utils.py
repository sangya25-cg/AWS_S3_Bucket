import os
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_s3_client() -> boto3.client:
    """
    Creates and returns a boto3 S3 client using credentials from environment variables.
    
    Raises:
        ValueError: If AWS credentials or region are not found in the environment.
        Exception: For other initialization errors.
    """
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_REGION")
    
    # Check if credentials are empty or contain only placeholders
    if not aws_access_key or not aws_secret_key or not region_name:
        raise ValueError("Missing AWS credentials in configuration. Please check your .env file.")
        
    aws_access_key = aws_access_key.strip()
    aws_secret_key = aws_secret_key.strip()
    region_name = region_name.strip()
    
    if not aws_access_key or not aws_secret_key or not region_name:
        raise ValueError("AWS credentials in .env are empty. Please fill them in.")

    try:
        return boto3.client(
            "s3",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region_name
        )
    except Exception as e:
        raise Exception(f"Failed to create S3 client: {str(e)}")

def verify_bucket_existence(client: Any, bucket_name: str) -> bool:
    """
    Verifies if a bucket exists and is accessible.
    
    Args:
        client: The boto3 S3 client.
        bucket_name: The name of the S3 bucket.
        
    Returns:
        bool: True if bucket exists and is accessible.
        
    Raises:
        ValueError: If bucket_name is empty or bucket does not exist.
        PermissionError: If user lacks permission to access the bucket.
    """
    if not bucket_name or not bucket_name.strip():
        raise ValueError("Bucket name is empty. Please configure BUCKET_NAME in your .env file.")
        
    bucket_name = bucket_name.strip()
    try:
        client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        # 404 means bucket doesn't exist, 403 means forbidden (IAM permission issue)
        if error_code == '404':
            raise ValueError(f"The bucket '{bucket_name}' does not exist. Please check your configuration.")
        elif error_code == '403':
            raise PermissionError(f"Access Denied to bucket '{bucket_name}'. Please check your IAM policy and credentials.")
        else:
            raise Exception(f"S3 Connection Error: {e.response.get('Error', {}).get('Message', str(e))}")

def upload_file(client: Any, file_obj: Any, filename: str, bucket_name: str) -> bool:
    """
    Uploads a file object to the specified S3 bucket.
    
    Args:
        client: The boto3 S3 client.
        file_obj: The file-like object to upload.
        filename: The destination key/name in S3.
        bucket_name: The destination S3 bucket.
        
    Returns:
        bool: True if upload was successful.
    """
    try:
        client.upload_fileobj(file_obj, bucket_name, filename)
        return True
    except ClientError as e:
        raise Exception(f"S3 Upload failed: {e.response.get('Error', {}).get('Message', str(e))}")
    except Exception as e:
        raise Exception(f"Upload failed: {str(e)}")

def list_files(client: Any, bucket_name: str) -> List[Dict[str, Any]]:
    """
    Lists all objects in the specified S3 bucket.
    
    Args:
        client: The boto3 S3 client.
        bucket_name: The S3 bucket name.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing:
            - 'Key': File name
            - 'Size': Size in bytes
            - 'LastModified': Last modified datetime
    """
    try:
        response = client.list_objects_v2(Bucket=bucket_name)
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    'Key': obj['Key'],
                    'Size': obj['Size'],
                    'LastModified': obj['LastModified']
                })
        return files
    except ClientError as e:
        raise Exception(f"Failed to list S3 objects: {e.response.get('Error', {}).get('Message', str(e))}")

def download_file(client: Any, bucket_name: str, object_key: str) -> bytes:
    """
    Downloads an object from the specified S3 bucket as bytes.
    
    Args:
        client: The boto3 S3 client.
        bucket_name: The S3 bucket name.
        object_key: The S3 object key.
        
    Returns:
        bytes: The raw file content.
    """
    try:
        response = client.get_object(Bucket=bucket_name, Key=object_key)
        return response['Body'].read()
    except ClientError as e:
        raise Exception(f"Failed to download file: {e.response.get('Error', {}).get('Message', str(e))}")

def delete_file(client: Any, bucket_name: str, object_key: str) -> bool:
    """
    Deletes an object from the specified S3 bucket.
    
    Args:
        client: The boto3 S3 client.
        bucket_name: The S3 bucket name.
        object_key: The S3 object key.
        
    Returns:
        bool: True if deletion was successful.
    """
    try:
        client.delete_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        raise Exception(f"Failed to delete file: {e.response.get('Error', {}).get('Message', str(e))}")

def get_bucket_size(client: Any, bucket_name: str) -> Tuple[int, int]:
    """
    Retrieves the total number of files and cumulative size of the bucket.
    
    Args:
        client: The boto3 S3 client.
        bucket_name: The S3 bucket name.
        
    Returns:
        Tuple[int, int]: (total_file_count, total_size_in_bytes)
    """
    try:
        response = client.list_objects_v2(Bucket=bucket_name)
        total_files = 0
        total_size = 0
        if 'Contents' in response:
            for obj in response['Contents']:
                total_files += 1
                total_size += obj['Size']
        return total_files, total_size
    except ClientError as e:
        raise Exception(f"Failed to calculate bucket statistics: {e.response.get('Error', {}).get('Message', str(e))}")

def format_size(size_in_bytes: int) -> str:
    """
    Formats byte sizes into human-readable units (KB, MB, GB, etc.).
    
    Args:
        size_in_bytes: The file size in bytes.
        
    Returns:
        str: Formatted file size string.
    """
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 ** 2:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024 ** 3:
        return f"{size_in_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_in_bytes / (1024 ** 3):.2f} GB"

def get_file_icon(filename: str) -> str:
    """
    Determines an emoji representing the file type based on extension.
    
    Args:
        filename: Name of the file.
        
    Returns:
        str: Emoji representing the file type.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    # Emojis for document/media types
    icons = {
        # Archives
        '.zip': '📦', '.tar': '📦', '.gz': '📦', '.rar': '📦', '.7z': '📦',
        # Documents
        '.pdf': '📕',
        '.doc': '📄', '.docx': '📄', '.odt': '📄',
        '.xls': '📊', '.xlsx': '📊', '.csv': '📊',
        '.ppt': '📉', '.pptx': '📉',
        # Code
        '.py': '🐍', '.js': '📜', '.ts': '📜', '.html': '🌐', '.css': '🎨',
        '.json': '⚙️', '.xml': '⚙️', '.yaml': '⚙️', '.yml': '⚙️', '.sh': '🐚',
        # Images
        '.png': '🖼️', '.jpg': '🖼️', '.jpeg': '🖼️', '.gif': '🖼️', '.svg': '🖼️', '.webp': '🖼️',
        # Audio
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.ogg': '🎵',
        # Video
        '.mp4': '🎥', '.avi': '🎥', '.mkv': '🎥', '.mov': '🎥',
        # Text
        '.txt': '📝', '.md': '📝', '.log': '📝'
    }
    
    return icons.get(ext, '📄')
