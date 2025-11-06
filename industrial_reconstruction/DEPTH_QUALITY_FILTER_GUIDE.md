# Depth Quality/Confidence Filtering Guide

This guide explains how to use depth quality filtering to improve industrial reconstruction accuracy by only using high-quality, accurate frames.

## Overview

The depth quality filter assesses each frame before integration into the TSDF reconstruction. Frames that don't meet quality thresholds are rejected, improving overall mesh quality and reducing artifacts.

## Quality Metrics

The filter evaluates frames based on multiple criteria:

### 1. **Coverage** (Weight: 40%)
- Percentage of valid depth pixels in the image
- Higher coverage = more complete depth data
- **Threshold**: Minimum 30% valid pixels (default)

### 2. **Smoothness** (Weight: 30%)
- Consistency of depth values (low variance)
- Smooth surfaces indicate reliable depth measurements
- **Threshold**: Minimum smoothness score of 0.4 (default)

### 3. **Edge Quality** (Weight: 20%)
- Sharpness of depth discontinuities at object boundaries
- Well-defined edges indicate accurate depth sensing
- Helps distinguish between objects and noise

### 4. **Noise Level** (Weight: 10%)
- Estimated noise in depth measurements
- Lower noise = more reliable depth data
- Based on local variance analysis

## Configuration

### Basic Setup

Enable quality filtering in your launch file:

```xml
<node pkg="industrial_reconstruction" exec="industrial_reconstruction" name="industrial_reconstruction">
  <!-- ... other parameters ... -->
  
  <!-- Enable quality filtering -->
  <param name="enable_quality_filter" value="true"/>
  <param name="min_quality_threshold" value="0.5"/>
  <param name="min_coverage" value="0.3"/>
  <param name="min_smoothness" value="0.4"/>
  <param name="log_rejected_frames" value="true"/>
</node>
```

### Parameter Descriptions

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_quality_filter` | bool | `true` | Enable/disable quality-based frame filtering |
| `min_quality_threshold` | float | `0.5` | Minimum overall quality score (0.0-1.0) |
| `min_coverage` | float | `0.3` | Minimum valid depth pixel coverage (0.0-1.0) |
| `min_smoothness` | float | `0.4` | Minimum smoothness score (0.0-1.0) |
| `log_rejected_frames` | bool | `true` | Log frames rejected due to quality issues |

### Quality Threshold Recommendations

#### Conservative (High Quality Only)
```xml
<param name="min_quality_threshold" value="0.7"/>
<param name="min_coverage" value="0.5"/>
<param name="min_smoothness" value="0.6"/>
```
- **Use when**: You need maximum accuracy, can tolerate lower frame rates
- **Result**: Only very high-quality frames accepted, slower reconstruction

#### Balanced (Recommended)
```xml
<param name="min_quality_threshold" value="0.5"/>
<param name="min_coverage" value="0.3"/>
<param name="min_smoothness" value="0.4"/>
```
- **Use when**: Good balance between quality and speed
- **Result**: Good quality frames accepted, reasonable reconstruction speed

#### Aggressive (More Frames)
```xml
<param name="min_quality_threshold" value="0.3"/>
<param name="min_coverage" value="0.2"/>
<param name="min_smoothness" value="0.3"/>
```
- **Use when**: You need faster reconstruction, can tolerate some lower-quality frames
- **Result**: More frames accepted, faster reconstruction, potentially more artifacts

#### Disabled
```xml
<param name="enable_quality_filter" value="false"/>
```
- **Use when**: You want maximum frame rate, will handle quality issues in post-processing
- **Result**: All frames accepted (original behavior)

## Understanding Quality Scores

### Coverage Score
- **0.0**: No valid depth pixels
- **0.3**: 30% of pixels have valid depth (minimum recommended)
- **0.5**: 50% of pixels have valid depth (good)
- **0.8+**: 80%+ coverage (excellent)

### Smoothness Score
- **0.0**: Very noisy, inconsistent depth (high variance)
- **0.4**: Moderate smoothness (minimum recommended)
- **0.6**: Good smoothness, consistent depth
- **0.8+**: Very smooth, highly consistent depth

### Overall Quality Score
- **0.0-0.3**: Poor quality, likely rejected
- **0.3-0.5**: Acceptable quality (with relaxed thresholds)
- **0.5-0.7**: Good quality (balanced threshold)
- **0.7-1.0**: Excellent quality

## Monitoring Filter Performance

### During Reconstruction

Check the logs for quality filter statistics:

```bash
# View reconstruction logs
ros2 topic echo /rosout | grep "Quality filter"
```

You'll see messages like:
```
[INFO] Frame rejected: quality=0.42, coverage=0.25, smoothness=0.35
[INFO] Quality filter statistics: Total=1000, Accepted=750, Rejected=250 (25.0%)
```

### After Reconstruction

The reconstruction service returns statistics when stopping:
- Total frames received
- Frames accepted
- Frames rejected
- Rejection rate percentage

## Troubleshooting

### Problem: Too Many Frames Rejected

**Symptoms**: High rejection rate (>50%), slow reconstruction

**Solutions**:
1. **Lower thresholds**:
   ```xml
   <param name="min_quality_threshold" value="0.4"/>
   <param name="min_coverage" value="0.25"/>
   ```

2. **Check camera settings**:
   - Ensure proper lighting
   - Adjust camera exposure/gain
   - Check if camera is too close/far from object
   - Verify depth filters are enabled

3. **Check camera motion**:
   - Ensure smooth, slow camera movement
   - Avoid rapid movements that cause motion blur

### Problem: Poor Quality Frames Still Accepted

**Symptoms**: Mesh has artifacts, holes, or noise

**Solutions**:
1. **Increase thresholds**:
   ```xml
   <param name="min_quality_threshold" value="0.6"/>
   <param name="min_coverage" value="0.4"/>
   <param name="min_smoothness" value="0.5"/>
   ```

2. **Enable additional depth filters**:
   - Enable temporal filtering
   - Enable spatial filtering
   - Enable noise removal filters

3. **Adjust camera settings**:
   - Increase laser power (if applicable)
   - Optimize exposure settings
   - Improve lighting conditions

### Problem: No Quality Filter Messages

**Symptoms**: No log messages about quality filtering

**Solutions**:
1. **Check if filter is enabled**:
   ```bash
   ros2 param get /industrial_reconstruction enable_quality_filter
   ```

2. **Enable logging**:
   ```xml
   <param name="log_rejected_frames" value="true"/>
   ```

3. **Check ROS2 log level**:
   ```bash
   ros2 run rqt_logger_level rqt_logger_level
   ```

## Integration with Behavior Tree

You can add quality monitoring to your behavior tree:

```xml
<BehaviorTree ID="scan_with_quality_check">
  <Sequence>
    <StartReconstructionService name="Start Reconstruction" service_name="start_reconstruction"/>
    <FollowJointTrajectoryAction name="Execute Scan Motion" trajectory="{process}"/>
    <StopReconstructionService name="Stop Reconstruction" service_name="stop_reconstruction"/>
    <!-- Quality statistics will be logged automatically -->
  </Sequence>
</BehaviorTree>
```

## Advanced Usage

### Custom Quality Thresholds Per Scan Phase

You could modify the reconstruction node to accept different thresholds based on scan phase:

```python
# In your custom node or service
if scan_phase == "approach":
    min_quality = 0.3  # Lower threshold during approach
elif scan_phase == "scan":
    min_quality = 0.6  # Higher threshold during active scanning
elif scan_phase == "departure":
    min_quality = 0.3  # Lower threshold during departure
```

### Dynamic Threshold Adjustment

Adjust thresholds based on reconstruction progress:

```python
# If rejection rate is too high, lower thresholds
if rejection_rate > 0.5:
    min_quality_threshold *= 0.9  # Reduce by 10%
```

## Performance Impact

### Computation Overhead
- Quality assessment adds ~5-10ms per frame
- Minimal impact for typical scanning rates (10-30 FPS)

### Memory Impact
- No additional memory overhead
- Quality metrics are calculated on-the-fly

### Frame Rate Impact
- Depends on rejection rate
- If 25% frames rejected, effective frame rate reduced by 25%
- But mesh quality improves significantly

## Best Practices

1. **Start with balanced thresholds** (0.5, 0.3, 0.4)
2. **Monitor rejection rates** during first few scans
3. **Adjust thresholds** based on your specific setup
4. **Enable logging** during initial setup to understand filter behavior
5. **Use higher thresholds** for critical parts requiring high accuracy
6. **Use lower thresholds** for fast scanning or rough parts

## Example Configurations

### High-Accuracy Scanning (Small Parts)
```xml
<param name="enable_quality_filter" value="true"/>
<param name="min_quality_threshold" value="0.7"/>
<param name="min_coverage" value="0.5"/>
<param name="min_smoothness" value="0.6"/>
```

### Fast Scanning (Large Parts)
```xml
<param name="enable_quality_filter" value="true"/>
<param name="min_quality_threshold" value="0.4"/>
<param name="min_coverage" value="0.25"/>
<param name="min_smoothness" value="0.35"/>
```

### Production Use (Balanced)
```xml
<param name="enable_quality_filter" value="true"/>
<param name="min_quality_threshold" value="0.5"/>
<param name="min_coverage" value="0.3"/>
<param name="min_smoothness" value="0.4"/>
```

## Summary

Quality filtering helps ensure only accurate, high-quality frames are used for reconstruction:

- ✅ **Improves mesh quality** by rejecting poor frames
- ✅ **Reduces artifacts** and noise in final mesh
- ✅ **Configurable thresholds** for different use cases
- ✅ **Minimal performance impact**
- ✅ **Detailed logging** for monitoring and debugging

Start with the **balanced** configuration and adjust based on your specific needs!

