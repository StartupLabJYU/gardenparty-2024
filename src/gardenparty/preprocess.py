"""
Module to preprocess images of documents.

This module contains functions to preprocess images of documents, including detecting the document border, deskewing the
image, and cropping the image to remove whitespace. 

Ideally the document border detection would be performed using javascript in the frontend, but for now we will use
OpenCV in the backend.

https://github.com/adityaguptai/Document-Boundary-Detection?tab=readme-ov-file
https://pyimagesearch.com/2014/09/01/build-kick-ass-mobile-document-scanner-just-5-minutes/
https://www.dynamsoft.com/codepool/web-document-scanner-with-opencvjs.html
"""

import logging
import cv2
import numpy as np

from typing import Tuple

logger = logging.getLogger(__name__)

def preprocess_image(image_path) -> Tuple[np.ndarray, np.ndarray]:
    # Load the image
    image = cv2.imread(image_path)
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return image, blurred

# def detect_edges(blurred) -> np.ndarray:
#     """ Perform edge detection """
#     edged = cv2.Canny(blurred, 75, 200)
#     # Dilate the edges
#     dilated = cv2.dilate(edged, None, iterations=2)
#     # Save the result
#     cv2.imwrite('edged.jpg', dilated)
#     return dilated

def find_document_contours(blurred):
    """
    Try to detect edges using Canny. If that fails, use binary thresholding.
    """

    try:
        # First, try Canny edge detection
        edged = cv2.Canny(blurred, 75, 200)
        # Dilate the edges to close gaps
        dilated = cv2.dilate(edged, None, iterations=2)
        contour = _find_document_contours(dilated)
        return contour
    except ValueError as e:
        logger.warning("Edge detection failed. Trying binary thresholding.")

        # If edge detection fails, fallback to binary thresholding
        _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
        dilated_thresh = cv2.dilate(thresh, None, iterations=2)

        # Try finding a contour with at least 4 points in the thresholded image
        contour = _find_document_contours(dilated_thresh)
        return contour


def _find_document_contours(edged) -> np.ndarray:
    """ Find the contour of the document in the image """
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    # Sort contours by area and get the largest one
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    for contour in contours:
        # Approximate the contour to a polygon
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        if len(approx) >= 4:
            return approx
    raise ValueError("No suitable contour found with 4 or more points.")


def get_document_perspective(image, contour) -> np.ndarray:
    # Get the points from the contour
    points = np.array([point[0] for point in contour], dtype='float32')
    
    # Use a heuristic to get the largest 4 points that form a quadrilateral
    if len(points) > 4:
        # Convex hull to get the outermost points
        hull = cv2.convexHull(points)
        # Sort points in the order of top-left, top-right, bottom-right, bottom-left
        rect = cv2.boxPoints(cv2.minAreaRect(hull))
        rect = np.array(sorted(rect, key=lambda x: (x[1], x[0])), dtype='float32')
    else:
        # Directly use the points if exactly 4
        rect = points

    # Define the points for the perspective transformation (top-down view)
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype='float32')
    
    # Compute the perspective transform matrix and apply it
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped


def trim_whitespace(image) -> np.ndarray:
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Get the bounding box of the largest contour
    x, y, w, h = cv2.boundingRect(contours[0])
    # Crop the image
    cropped_image = image[y:y+h, x:x+w]
    return cropped_image


def enhance_contrast(image) -> np.ndarray:
    # Improve contrast using CLAHE (adaptive histogram equalization)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to the L-channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l)
    
    # Merge the CLAHE-enhanced L-channel back with A and B channels
    enhanced = cv2.merge((l_clahe, a, b))
    enhanced_image = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    return enhanced_image


def scale_and_crop(image, max_size=1024, aspect_ratio_max=2.5):
    # Get the current dimensions of the image
    height, width = image.shape[:2]
    
    # Calculate the aspect ratio of the image
    aspect_ratio = width / height
    
    # Crop the image if the aspect ratio exceeds the maximum allowed ratio (2.5:1)
    if aspect_ratio > aspect_ratio_max:
        # Image is too wide, crop width
        new_width = int(height * aspect_ratio_max)
        x_offset = (width - new_width) // 2
        image = image[:, x_offset:x_offset + new_width]
    
    # Resize the image so that the longest side is max_size (1024 pixels)
    height, width = image.shape[:2]
    longest_side = max(width, height)
    scale_factor = max_size / longest_side
    
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    scaled_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    return scaled_image


def autocrop(image_path, output_path) -> None:
    image, blurred = preprocess_image(image_path)

    cropped = trim_whitespace(image)
    contrasted = enhance_contrast(cropped)

    # Crop to ensure aspect ratio
    cropped_image = scale_and_crop(contrasted)

    if not cv2.imwrite(output_path, cropped_image):
        raise ValueError(f"Failed to save image to {output_path}")

    logger.info(f"Processed image saved as {output_path}")
    return output_path


def autocrop_and_straighten(image_path, output_path) -> None:
    image, blurred = preprocess_image(image_path)
    #edged = detect_edges(blurred)
    contour = find_document_contours(blurred)
    warped_image = get_document_perspective(image, contour)
    
    cropped = trim_whitespace(warped_image)
    contrasted = enhance_contrast(cropped)

    # Crop to ensure aspect ratio
    cropped_image = scale_and_crop(contrasted)

    # Save the result
    if not cv2.imwrite(output_path, cropped_image):
        raise ValueError(f"Failed to save image to {output_path}")

    logger.info(f"Processed image saved as {output_path}")
    return output_path


def save_image_as(source: str, target: str) -> None:
    image = cv2.imread(source)
    cv2.imwrite(target, image)
    print(f"Image saved as {target}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    autocrop_and_straighten('instance/img_2106.jpg', 'instance/preprocessed_img_2106.jpg')
