import struct
import json
import os
import sys
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.signal import savgol_filter

# ==========================================
# 1. VMD 解析模块
# ==========================================

class VmdMotion:
    def __init__(self):
        self.signature = ""
        self.model_name = ""
        self.version = 0
        self.motion_frames = [] 

    @staticmethod
    def load(filepath):
        motion = VmdMotion()
        with open(filepath, 'rb') as f:
            data = f.read()
        
        ptr = 0
        
        # Header
        motion.signature = data[ptr:ptr+30].decode('ascii', errors='ignore').strip('\x00')
        ptr += 30
        
        if "Vocaloid Motion Data 0002" in motion.signature:
            motion.version = 2
        else:
            motion.version = 1

        motion.model_name = data[ptr:ptr+20].split(b'\x00')[0].decode('shift-jis', errors='replace')
        ptr += 20
        
        total_frames = struct.unpack('I', data[ptr:ptr+4])[0]
        ptr += 4
        
        print(f"Parsed VMD: {filepath}")
        print(f"Frames: {total_frames}")

        for _ in range(total_frames):
            bone_name_bytes = data[ptr:ptr+15]
            bone_name = bone_name_bytes.split(b'\x00')[0].decode('shift-jis', errors='replace')
            
            # Frame: Index(I), Pos(3f), Rot(4f), Interpolation(64b)
            frame_data = struct.unpack('<I7f', data[ptr+15:ptr+15+4+28])
            
            frame_index = frame_data[0]
            pos = [frame_data[1], frame_data[2], frame_data[3]]
            rot = [frame_data[4], frame_data[5], frame_data[6], frame_data[7]] # x, y, z, w
            
            motion.motion_frames.append({
                'bone': bone_name,
                'frame': frame_index,
                'pos': pos,
                'rot': rot
            })
            
            ptr += 111
            
        return motion

# ==========================================
# 2. 平滑算法
# ==========================================

def unwrap_euler_angles(euler_angles):
    """
    处理角度突变 (-180 <-> 180)
    """
    # 确保输入是二维数组 (N, 3)
    if euler_angles.ndim == 1:
        euler_angles = euler_angles[np.newaxis, :]

    unwrapped_angles = euler_angles.copy()

    for i in range(unwrapped_angles.shape[0]-1):
        for j in range(unwrapped_angles.shape[1]):
            diff = unwrapped_angles[i+1, j] - unwrapped_angles[i, j]
            if diff > 180:
                unwrapped_angles[i+1:, j] -= 360
            elif diff < -180:
                unwrapped_angles[i+1:, j] += 360

    return unwrapped_angles

def apply_smoothing(data, window_length=5, polyorder=2):
    """
    使用 Savitzky-Golay 滤波器平滑数据
    :param data: 输入数据 (N, D) 或 (N,)
    :param window_length: 窗口长度 (必须是奇数)
    :param polyorder: 多项式阶数
    """
    if window_length <= polyorder:
        return data
    
    if len(data) < window_length:
        return data

    # 确保窗口长度是奇数
    if window_length % 2 == 0:
        window_length += 1

    try:
        return savgol_filter(data, window_length, polyorder, axis=0)
    except Exception as e:
        print(f"Smoothing failed: {e}")
        return data

# ==========================================
# 3. 自定义骨骼映射 (V8 Update)
# ==========================================

# 字段说明:
# invert: True/False 或 ['x', 'y', 'z'] 列表
# src_axis: 'x', 'y', 'z' (仅 Bend)
# swap_yz: True/False (仅 Rot) - 交换 Y 和 Z 通道的数值映射

BONE_MAP = {
    # --- 根/位移 ---
    "センター": {"target": "root", "type": "root", "invert": False},
    "全ての親": {"target": "root", "type": "root", "invert": False},
    
    # --- 身体 ---
    "下半身":   {"target": "body", "type": "rot",  "invert": True}, 
    "腰":       {"target": "body", "type": "rot",  "invert": True}, 
    "上半身":   {"target": "body", "type": "bend", "invert": True}, 
    "上半身2":  {"target": "body", "type": "rot",  "invert": True}, 
    "首":       {"target": "head", "type": "rot",  "invert": True}, 
    "頭":       {"target": "head", "type": "rot",  "invert": True}, 
    
    # --- 手臂 (Rot) ---
    # 左手臂: ROT_X 也要取负数 -> ['x', 'z']
    "左腕":     {"target": "left_arm", "type": "rot", "invert": ['x', 'z']}, 
    
    # 右手臂: 
    # 1. "ROT_Y、ROT_Z互相反了" -> swap_yz=True
    # 2. "ROT_X、ROT_Y、ROT_Z都要再取负数" (V7) -> invert=True
    # 3. "ROT_Y、ROT_Z再取一次负" (V8) -> Y, Z 负负得正 -> 只有 X 反转
    "右腕":     {"target": "right_arm", "type": "rot", "invert": ['x'], "swap_yz": True}, 
    
    # --- 手肘 (Bend) ---
    "左ひじ":   {"target": "left_arm", "type": "bend", "invert": False, "src_axis": "z"},
    "右ひじ":   {"target": "right_arm", "type": "bend", "invert": True, "src_axis": "z"},
    
    # --- 腿 (Rot) ---
    "左足":     {"target": "left_leg", "type": "rot", "invert": True}, 
    "左足D":    {"target": "left_leg", "type": "rot", "invert": True},
    "右足":     {"target": "right_leg", "type": "rot", "invert": True},
    "右足D":    {"target": "right_leg", "type": "rot", "invert": True},
    
    # --- 膝盖 (Bend) ---
    "左ひざ":   {"target": "left_leg", "type": "bend", "invert": True}, 
    "右ひざ":   {"target": "right_leg", "type": "bend", "invert": True}, 
}

# ==========================================
# 4. 主转换逻辑
# ==========================================

def convert_vmd_to_miframes(vmd_path, output_path, fps=30, scale_factor=0.1, smooth_window=15):
    try:
        vmd = VmdMotion.load(vmd_path)
    except Exception as e:
        print(f"Error loading VMD: {e}")
        return

    miframes_data = {
        "format": 34,
        "created_in": "2.0.0",
        "is_model": True,
        "tempo": fps,
        "length": 0,
        "keyframes": [],
        "templates": [],
        "timelines": [],
        "resources": []
    }

    bone_frames = {}
    for f in vmd.motion_frames:
        name = f['bone']
        if name in BONE_MAP:
            if name not in bone_frames:
                bone_frames[name] = []
            bone_frames[name].append(f)

    max_frame_idx = 0
    
    # 中间存储字典
    merged_keyframes = {}

    for bone_name, frames in bone_frames.items():
        frames.sort(key=lambda x: x['frame'])
        
        mapping = BONE_MAP[bone_name]
        target_part = mapping['target']
        map_type = mapping['type']
        invert_config = mapping['invert']
        src_axis = mapping.get('src_axis', 'x') 
        swap_yz = mapping.get('swap_yz', False)

        quats = np.array([f['rot'] for f in frames])
        positions = np.array([f['pos'] for f in frames])
        frame_indices = [f['frame'] for f in frames]
        
        if len(frame_indices) > 0:
            max_frame_idx = max(max_frame_idx, max(frame_indices))

        # 1. 转换四元数到欧拉角
        r = Rotation.from_quat(quats)
        euler_yxz = r.as_euler('YXZ', degrees=True)
        
        # 2. 解包角度 (处理 360 度跳变)
        euler_unwrapped = unwrap_euler_angles(euler_yxz)
        
        # 3. 平滑处理 (Savitzky-Golay)
        euler_smooth = apply_smoothing(euler_unwrapped, window_length=smooth_window)
        
        # 如果需要，也可以平滑位置
        pos_smooth = apply_smoothing(positions, window_length=smooth_window)

        for i, idx in enumerate(frame_indices):
            e_y, e_x, e_z = euler_smooth[i]

            # --- 坐标系基础变换 ---
            # 默认: X=e_x, Y=e_z(MMD Z), Z=e_y(MMD Y)
            val_rot_x = e_x
            val_rot_y = e_z 
            val_rot_z = e_y 

            # 特殊修正: 交换 Y 和 Z 轴 (如果 swap_yz=True)
            if swap_yz:
                val_rot_y, val_rot_z = val_rot_z, val_rot_y

            new_values = {}
            
            def should_invert_axis(axis_name):
                if isinstance(invert_config, bool):
                    return invert_config
                if isinstance(invert_config, list):
                    return axis_name in invert_config
                return False

            if map_type == "rot":
                vx = -val_rot_x if should_invert_axis('x') else val_rot_x
                vy = -val_rot_y if should_invert_axis('y') else val_rot_y
                vz = -val_rot_z if should_invert_axis('z') else val_rot_z
                
                new_values["ROT_X"] = float(vx)
                new_values["ROT_Y"] = float(vy)
                new_values["ROT_Z"] = float(vz)
            
            elif map_type == "bend":
                bend_val = 0.0
                if src_axis == 'x': bend_val = val_rot_x
                elif src_axis == 'y': bend_val = val_rot_y
                elif src_axis == 'z': bend_val = val_rot_z
                
                do_invert_bend = False
                if isinstance(invert_config, bool):
                    do_invert_bend = invert_config
                elif isinstance(invert_config, list) and len(invert_config) > 0:
                    do_invert_bend = True

                if do_invert_bend:
                    bend_val = -bend_val
                
                new_values["BEND_ANGLE_X"] = float(bend_val)

            elif map_type == "root":
                px, py, pz = pos_smooth[i]
                new_values["POS_X"] = float(-px * scale_factor)
                new_values["POS_Y"] = float(py * scale_factor)
                new_values["POS_Z"] = float(-pz * scale_factor)
                new_values["ROT_Z"] = float(val_rot_z)

            # --- 合并逻辑 ---
            key = (idx, target_part)
            if key not in merged_keyframes:
                merged_keyframes[key] = {}
            merged_keyframes[key].update(new_values)

    # --- 生成最终列表 ---
    miframes_data["length"] = max_frame_idx + 1
    
    # 按 (position, part_name) 排序
    sorted_items = sorted(merged_keyframes.items(), key=lambda item: item[0][0])

    for (pos, part), vals in sorted_items:
        kf_entry = {"position": pos}
        
        if part != "root":
            kf_entry["part_name"] = part
            
        kf_entry["values"] = vals
        
        miframes_data["keyframes"].append(kf_entry)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(miframes_data, f, indent=4)

    print(f"Conversion complete (V8 - Right Arm YZ Re-inverted). Saved to {output_path}")

if __name__ == "__main__":
    input_file = "VMD2mi/dance.vmd"
    output_file = "VMD2mi/dance_custom_v8.miframes"
    
    if not os.path.exists(input_file) and os.path.exists("dance.vmd"):
        input_file = "dance.vmd"
        output_file = "dance_custom_v8.miframes"

    if os.path.exists(input_file):
        convert_vmd_to_miframes(input_file, output_file, scale_factor=0.1, smooth_window=15)
    else:
        print(f"Input file {input_file} not found.")