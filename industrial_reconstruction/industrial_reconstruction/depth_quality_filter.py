"""
Depth Quality Filter Module

This module provides functions to assess depth image quality and confidence
for filtering frames before integration into TSDF reconstruction.
"""

import numpy as np
import cv2
from typing import Tuple, Optional


def calculate_depth_coverage(depth_image: np.ndarray) -> float:
    """
    Calculate the percentage of valid depth pixels in the image.
    
    Args:
        depth_image: Depth image (uint16 or float)
    
    Returns:
        Coverage ratio (0.0 to 1.0)
    """
    if depth_image.size == 0:
        return 0.0
    
    valid_pixels = np.sum(depth_image > 0)
    total_pixels = depth_image.size
    return valid_pixels / total_pixels if total_pixels > 0 else 0.0


def calculate_depth_smoothness(depth_image: np.ndarray) -> float:
    """
    Calculate depth smoothness score based on local variance.
    Lower variance indicates smoother, more consistent depth.
    
    Args:
        depth_image: Depth image (uint16 or float)
    
    Returns:
        Smoothness score (0.0 to 1.0, higher is better)
    """
    valid_mask = depth_image > 0
    if np.sum(valid_mask) == 0:
        return 0.0
    
    valid_depth = depth_image[valid_mask]
    if len(valid_depth) < 2:
        return 0.0
    
    # Calculate coefficient of variation (std/mean)
    depth_mean = np.mean(valid_depth)
    depth_std = np.std(valid_depth)
    
    if depth_mean == 0:
        return 0.0
    
    cv = depth_std / depth_mean
    # Convert to smoothness score (lower CV = higher smoothness)
    smoothness = 1.0 / (1.0 + cv)
    
    return min(1.0, max(0.0, smoothness))


def calculate_depth_edge_quality(depth_image: np.ndarray) -> float:
    """
    Calculate depth edge quality - detects if edges are sharp and well-defined.
    Good depth images should have sharp edges at object boundaries.
    
    Args:
        depth_image: Depth image (uint16 or float)
    
    Returns:
        Edge quality score (0.0 to 1.0, higher is better)
    """
    if depth_image.size == 0:
        return 0.0
    
    valid_mask = depth_image > 0
    if np.sum(valid_mask) < 100:  # Need minimum pixels
        return 0.0
    
    # Calculate depth gradient (Sobel operator)
    depth_float = depth_image.astype(np.float32)
    sobel_x = cv2.Sobel(depth_float, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(depth_float, cv2.CV_32F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
    
    # Mask to valid regions only
    gradient_magnitude[~valid_mask] = 0
    
    # Normalize gradient magnitude
    max_gradient = np.percentile(gradient_magnitude[valid_mask], 95) if np.any(valid_mask) else 1.0
    if max_gradient > 0:
        gradient_magnitude = gradient_magnitude / max_gradient
    
    # Good edges should have moderate gradient magnitude (not too noisy, not too flat)
    # This is a heuristic - adjust based on your needs
    edge_score = np.mean(gradient_magnitude[valid_mask]) if np.any(valid_mask) else 0.0
    
    return min(1.0, max(0.0, edge_score))


def calculate_depth_noise_level(depth_image: np.ndarray, window_size: int = 5) -> float:
    """
    Estimate noise level in depth image by calculating local variance.
    Lower noise = higher quality.
    
    Args:
        depth_image: Depth image (uint16 or float)
        window_size: Size of local window for variance calculation
    
    Returns:
        Noise level score (0.0 to 1.0, higher is better - less noise)
    """
    if depth_image.size == 0:
        return 0.0
    
    valid_mask = depth_image > 0
    if np.sum(valid_mask) < 100:
        return 0.0
    
    # Calculate local variance using Laplacian
    depth_float = depth_image.astype(np.float32)
    laplacian = cv2.Laplacian(depth_float, cv2.CV_32F, ksize=window_size)
    laplacian[~valid_mask] = 0
    
    # Variance of Laplacian indicates noise level
    noise_variance = np.var(laplacian[valid_mask]) if np.any(valid_mask) else 0.0
    
    # Convert to quality score (lower variance = less noise = better)
    # Normalize based on typical noise levels (adjust threshold as needed)
    noise_threshold = 1000.0  # Adjust based on your depth scale
    noise_score = 1.0 / (1.0 + noise_variance / noise_threshold)
    
    return min(1.0, max(0.0, noise_score))


def calculate_depth_quality_score(
    depth_image: np.ndarray,
    coverage_weight: float = 0.4,
    smoothness_weight: float = 0.3,
    edge_weight: float = 0.2,
    noise_weight: float = 0.1
) -> Tuple[float, dict]:
    """
    Calculate overall depth quality score combining multiple metrics.
    
    Args:
        depth_image: Depth image (uint16 or float)
        coverage_weight: Weight for coverage metric (default 0.4)
        smoothness_weight: Weight for smoothness metric (default 0.3)
        edge_weight: Weight for edge quality metric (default 0.2)
        noise_weight: Weight for noise level metric (default 0.1)
    
    Returns:
        Tuple of (quality_score, metrics_dict)
        - quality_score: Overall quality (0.0 to 1.0)
        - metrics_dict: Dictionary with individual metric scores
    """
    if depth_image.size == 0:
        return 0.0, {
            'coverage': 0.0,
            'smoothness': 0.0,
            'edge_quality': 0.0,
            'noise_level': 0.0
        }
    
    # Normalize weights
    total_weight = coverage_weight + smoothness_weight + edge_weight + noise_weight
    if total_weight > 0:
        coverage_weight /= total_weight
        smoothness_weight /= total_weight
        edge_weight /= total_weight
        noise_weight /= total_weight
    
    # Calculate individual metrics
    coverage = calculate_depth_coverage(depth_image)
    smoothness = calculate_depth_smoothness(depth_image)
    edge_quality = calculate_depth_edge_quality(depth_image)
    noise_level = calculate_depth_noise_level(depth_image)
    
    # Weighted combination
    quality_score = (
        coverage_weight * coverage +
        smoothness_weight * smoothness +
        edge_weight * edge_quality +
        noise_weight * noise_level
    )
    
    metrics = {
        'coverage': coverage,
        'smoothness': smoothness,
        'edge_quality': edge_quality,
        'noise_level': noise_level
    }
    
    return min(1.0, max(0.0, quality_score)), metrics


def is_depth_frame_acceptable(
    depth_image: np.ndarray,
    min_quality_threshold: float = 0.5,
    min_coverage: float = 0.3,
    min_smoothness: float = 0.4
) -> Tuple[bool, float, dict]:
    """
    Check if a depth frame meets quality criteria for reconstruction.
    
    Args:
        depth_image: Depth image (uint16 or float)
        min_quality_threshold: Minimum overall quality score (0.0 to 1.0)
        min_coverage: Minimum coverage ratio (0.0 to 1.0)
        min_smoothness: Minimum smoothness score (0.0 to 1.0)
    
    Returns:
        Tuple of (is_acceptable, quality_score, metrics_dict)
    """
    quality_score, metrics = calculate_depth_quality_score(depth_image)
    
    # Check individual criteria
    meets_quality = quality_score >= min_quality_threshold
    meets_coverage = metrics['coverage'] >= min_coverage
    meets_smoothness = metrics['smoothness'] >= min_smoothness
    
    is_acceptable = meets_quality and meets_coverage and meets_smoothness
    
    return is_acceptable, quality_score, metrics


def calculate_color_depth_alignment(
    depth_image: np.ndarray,
    color_image: np.ndarray,
    depth_scale: float = 1000.0
) -> float:
    """
    Calculate alignment quality between depth and color images.
    Good alignment helps with RGBD reconstruction quality.
    
    Args:
        depth_image: Depth image (uint16)
        color_image: Color image (BGR)
        depth_scale: Scale factor for depth values
    
    Returns:
        Alignment quality score (0.0 to 1.0)
    """
    if depth_image.size == 0 or color_image.size == 0:
        return 0.0
    
    # Check if images have compatible dimensions
    if depth_image.shape[:2] != color_image.shape[:2]:
        return 0.0
    
    # This is a simplified check - in practice, you'd want to verify
    # that edges in color image align with depth discontinuities
    # For now, we'll just check that both images are valid
    depth_valid = np.sum(depth_image > 0) > 0
    color_valid = np.sum(color_image > 0) > 0
    
    if depth_valid and color_valid:
        return 1.0
    else:
        return 0.0

