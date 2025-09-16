from PIL import Image
from io import BytesIO
from typing import Tuple, Optional
from fastapi import HTTPException, UploadFile
from app.core.config import settings
import structlog

logger = structlog.get_logger()


def validate_file_type(file_content: bytes, filename: str) -> Tuple[bool, str]:
    """Validate file type using PIL (Windows compatible)."""
    try:
        # Use PIL to detect image type
        image = Image.open(BytesIO(file_content))
        detected_type = f"image/{image.format.lower()}"
        
        if detected_type not in settings.ALLOWED_IMAGE_TYPES:
            logger.warning(
                "Invalid file type detected",
                filename=filename,
                detected_type=detected_type,
                allowed_types=settings.ALLOWED_IMAGE_TYPES
            )
            return False, f"File type {detected_type} not allowed"
        
        return True, detected_type
        
    except Exception as e:
        logger.error("Error validating file type", filename=filename, error=str(e))
        return False, "Unable to determine file type"


def validate_file_size(file_content: bytes) -> Tuple[bool, str]:
    """Validate file size."""
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
    
    if len(file_content) > max_size:
        return False, f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
    
    return True, ""


def reencode_image(file_content: bytes, target_format: str = "JPEG") -> bytes:
    """Re-encode image to safe format, stripping EXIF data."""
    try:
        # Open image with PIL
        image = Image.open(BytesIO(file_content))
        
        # Convert to RGB if necessary (for JPEG output)
        if target_format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
            # Create white background for transparent images
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background
        elif target_format == "JPEG" and image.mode != "RGB":
            image = image.convert("RGB")
        
        # Save to bytes with no EXIF data
        output = BytesIO()
        image.save(output, format=target_format, quality=95, optimize=True)
        
        logger.info(
            "Image re-encoded successfully",
            original_size=len(file_content),
            new_size=len(output.getvalue()),
            format=target_format
        )
        
        return output.getvalue()
        
    except Exception as e:
        logger.error("Error re-encoding image", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid image file")


def validate_and_process_image(file: UploadFile) -> Tuple[bytes, str]:
    """Validate and process uploaded image file."""
    # Read file content
    file_content = file.file.read()
    file.file.seek(0)  # Reset file pointer
    
    # Validate file size
    is_valid_size, size_error = validate_file_size(file_content)
    if not is_valid_size:
        raise HTTPException(status_code=400, detail=size_error)
    
    # Validate file type
    is_valid_type, detected_type = validate_file_type(file_content, file.filename)
    if not is_valid_type:
        raise HTTPException(status_code=400, detail=detected_type)
    
    # Re-encode image to safe format
    if detected_type == "image/jpeg":
        processed_content = reencode_image(file_content, "JPEG")
        return processed_content, "image/jpeg"
    elif detected_type == "image/png":
        # Convert PNG to JPEG for consistency and smaller size
        processed_content = reencode_image(file_content, "JPEG")
        return processed_content, "image/jpeg"
    elif detected_type == "image/webp":
        # Convert WebP to JPEG
        processed_content = reencode_image(file_content, "JPEG")
        return processed_content, "image/jpeg"
    else:
        # Fallback to JPEG
        processed_content = reencode_image(file_content, "JPEG")
        return processed_content, "image/jpeg"


def validate_dataset_size(image_count: int) -> bool:
    """Validate dataset size doesn't exceed limits."""
    if image_count > settings.MAX_IMAGES_PER_DATASET:
        raise HTTPException(
            status_code=400, 
            detail=f"Dataset exceeds maximum of {settings.MAX_IMAGES_PER_DATASET} images"
        )
    return True
