import numpy as np
import matplotlib.pyplot as plt
from vmd2miframes import apply_smoothing, unwrap_euler_angles

def test_smoothing():
    # 1. Generate dummy noisy data (sine wave + noise)
    x = np.linspace(0, 4 * np.pi, 100)
    true_signal = np.sin(x) * 50
    noise = np.random.normal(0, 5, 100)
    noisy_signal = true_signal + noise
    
    # Reshape for function compatibility (N, 1)
    data = noisy_signal[:, np.newaxis]
    
    # 2. Apply smoothing
    smoothed_data = apply_smoothing(data, window_length=15, polyorder=2)
    
    # 3. Calculate variance of derivative (roughness)
    diff_noisy = np.diff(data, axis=0)
    diff_smooth = np.diff(smoothed_data, axis=0)
    
    var_noisy = np.var(diff_noisy)
    var_smooth = np.var(diff_smooth)
    
    print(f"Variance of derivative (Noisy): {var_noisy:.4f}")
    print(f"Variance of derivative (Smoothed): {var_smooth:.4f}")
    
    if var_smooth < var_noisy:
        print("SUCCESS: Smoothing reduced signal jitter.")
    else:
        print("FAILURE: Smoothing did not reduce jitter.")

    # 4. Test Angle Unwrapping
    # Create a sequence that jumps from 170 to -170 (340 degree jump, should be wrapped)
    angles = np.array([[170], [175], [-175], [-170]])
    unwrapped = unwrap_euler_angles(angles)
    
    print("\nAngle Unwrapping Test:")
    print("Original:", angles.flatten())
    print("Unwrapped:", unwrapped.flatten())
    
    # Check if the jump is removed (difference should be small, around 5-10 degrees)
    diffs = np.diff(unwrapped, axis=0)
    if np.all(np.abs(diffs) < 180):
        print("SUCCESS: Angles successfully unwrapped.")
    else:
        print("FAILURE: Angle unwrapping failed.")

if __name__ == "__main__":
    test_smoothing()
