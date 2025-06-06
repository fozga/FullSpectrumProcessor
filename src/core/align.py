"""
Image alignment utilities for the RGB Channel Processor.

Cross-references:
    - handlers.channels: Uses align_images for channel alignment.
"""

import cv2
import numpy as np

class AlignmentError(Exception):
    """
    Exception raised when image alignment fails due to insufficient feature matches or transformation errors.

    Cross-references:
        - align_images
    """
    pass

def align_images(original_images):
    """
    Aligns green and blue channels to the red channel using ORB feature matching
    and affine transformation.

    Args:
        original_images (list of numpy.ndarray): List of three grayscale images (R, G, B), each as a 2D numpy array.

    Returns:
        list of numpy.ndarray: List of aligned images [R, G, B].

    Raises:
        AlignmentError: If alignment fails due to insufficient matches or transformation errors.

    Cross-references:
        - handlers.channels.load_channel
    """
    
    # Start with copies of the originals
    aligned = [img.copy() for img in original_images]

    # ORB detector with increased features for better matching
    orb = cv2.ORB_create(1000) # 1000 features balances performance/accuracy
    keypoints = []
    descriptors = []

    # Detect features for all channels
    for img in original_images:
        kp, des = orb.detectAndCompute(img, None)
        keypoints.append(kp)
        descriptors.append(des)

    # Align G (1) and B (2) to R (0)
    for i in range(1, 3):
        if (descriptors[0] is not None and descriptors[i] is not None and
            descriptors[0].size > 0 and descriptors[i].size > 0):

            # Brute-force matching with Hamming distance
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(descriptors[0], descriptors[i])

            MIN_MATCHES = 50  # Minimum matches for reliable alignment
            if len(matches) < MIN_MATCHES:
                raise AlignmentError(f"Insufficient matches ({len(matches)}/{MIN_MATCHES})")                
            # Convert match points to numpy arrays
            src_pts = np.float32([keypoints[0][m.queryIdx].pt for m in matches]).reshape(-1,1,2)
            dst_pts = np.float32([keypoints[i][m.trainIdx].pt for m in matches]).reshape(-1,1,2)

            # Estimate partial affine transform (rotation, translation, scaling)
            M, _ = cv2.estimateAffinePartial2D(dst_pts, src_pts)
            if M is None:
                raise AlignmentError(f"Failed to estimate transformation for channel {i}")
            else:
                # Apply transformation using reference channel dimensions
                aligned[i] = cv2.warpAffine(
                    original_images[i], M,
                    (original_images[0].shape[1], original_images[0].shape[0])
                )
    return aligned
