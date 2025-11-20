import json
import math
import struct
from functools import reduce
from typing import Dict, List, Tuple, Union, Any

class Vmd:
    def __init__(self):
        self.vision = 0
        self.model_name = ""
        self.bone_keyframe_number = 0
        self.bone_keyframe_record = []
        self.morph_keyframe_number = 0
        self.morph_keyframe_record = []
        self.camera_keyframe_number = 0
        self.camera_keyframe_record = []
        self.light_keyframe_number = 0
        self.light_keyframe_record = []
        self.dict = {}

    @staticmethod
    def from_file(filename: str, model_name_encode: str = "shift-JIS") -> 'Vmd':
        try:
            with open(filename, "rb") as f:
                # 读取文件内容（兼容大文件）
                array = bytearray()
                while chunk := f.read(8192):
                    array.extend(chunk)
        except FileNotFoundError:
            raise FileNotFoundError(f"文件未找到: {filename}")
        except Exception as e:
            raise Exception(f"读取文件时出错: {str(e)}")

        vmd = Vmd()
        header = array[:30].decode("ascii", errors="ignore").strip("\x00")
        
        # 检测VMD版本
        if header.startswith("Vocaloid Motion Data file"):
            vmd.vision = 1
        elif header.startswith("Vocaloid Motion Data 0002"):
            vmd.vision = 2
        else:
            raise ValueError(f"未知的VMD版本: {header}")

        # 解析模型名称
        name_end = 30 + 10 * vmd.vision
        vmd.model_name = array[30:name_end].split(b'\x00')[0].decode(model_name_encode, errors="replace")
        
        # 骨骼关键帧数量
        bone_offset = 30 + 10 * vmd.vision
        vmd.bone_keyframe_number = struct.unpack('<I', array[bone_offset:bone_offset+4])[0]
        current_index = bone_offset + 4

        # 解析骨骼关键帧
        for _ in range(vmd.bone_keyframe_number):
            if current_index + 111 > len(array):
                break
                
            frame = {
                "BoneName": array[current_index:current_index+15].split(b'\x00')[0].decode("shift-JIS", errors="replace"),
                "FrameTime": struct.unpack('<I', array[current_index+15:current_index+19])[0],
                "Position": {
                    "x": struct.unpack('<f', array[current_index+19:current_index+23])[0],
                    "y": struct.unpack('<f', array[current_index+23:current_index+27])[0],
                    "z": struct.unpack('<f', array[current_index+27:current_index+31])[0]
                },
                "Rotation": {
                    "x": struct.unpack('<f', array[current_index+31:current_index+35])[0],
                    "y": struct.unpack('<f', array[current_index+35:current_index+39])[0],
                    "z": struct.unpack('<f', array[current_index+39:current_index+43])[0],
                    "w": struct.unpack('<f', array[current_index+43:current_index+47])[0]
                }
            }
            vmd.bone_keyframe_record.append(frame)
            current_index += 111

        # 表情关键帧数量
        if current_index + 4 > len(array):
            return vmd
            
        vmd.morph_keyframe_number = struct.unpack('<I', array[current_index:current_index+4])[0]
        current_index += 4

        # 解析表情关键帧
        for _ in range(vmd.morph_keyframe_number):
            if current_index + 23 > len(array):
                break
                
            vmd.morph_keyframe_record.append({
                'MorphName': array[current_index:current_index+15].split(b'\x00')[0].decode("shift-JIS", errors="replace"),
                'FrameTime': struct.unpack('<I', array[current_index+15:current_index+19])[0],
                'Weight': struct.unpack('<f', array[current_index+19:current_index+23])[0]
            })
            current_index += 23

        # 相机关键帧数量
        if current_index + 4 > len(array):
            return vmd
            
        vmd.camera_keyframe_number = struct.unpack('<I', array[current_index:current_index+4])[0]
        current_index += 4

        # 解析相机关键帧
        for _ in range(vmd.camera_keyframe_number):
            if current_index + 61 > len(array):
                break
                
            try:
                view_angle = struct.unpack('<I', array[current_index+56:current_index+60])[0]
                ortho_flag = array[current_index+60]
            except Exception:
                # 兼容旧版本VMD
                view_angle = 30
                ortho_flag = 0
                
            vmd.camera_keyframe_record.append({
                'FrameTime': struct.unpack('<I', array[current_index:current_index+4])[0],
                'Distance': struct.unpack('<f', array[current_index+4:current_index+8])[0],
                "Position": {
                    "x": struct.unpack('<f', array[current_index+8:current_index+12])[0],
                    "y": struct.unpack('<f', array[current_index+12:current_index+16])[0],
                    "z": struct.unpack('<f', array[current_index+16:current_index+20])[0]
                },
                "Rotation": {
                    "x": struct.unpack('<f', array[current_index+20:current_index+24])[0],
                    "y": struct.unpack('<f', array[current_index+24:current_index+28])[0],
                    "z": struct.unpack('<f', array[current_index+28:current_index+32])[0]
                },
                "ViewAngle": view_angle,
                "Orthographic": ortho_flag
            })
            current_index += 61

        # 灯光关键帧数量
        if current_index + 4 > len(array):
            return vmd
            
        vmd.light_keyframe_number = struct.unpack('<I', array[current_index:current_index+4])[0]
        current_index += 4

        # 解析灯光关键帧
        for _ in range(vmd.light_keyframe_number):
            if current_index + 28 > len(array):
                break
                
            vmd.light_keyframe_record.append({
                'FrameTime': struct.unpack('<I', array[current_index:current_index+4])[0],
                'Color': {
                    'r': struct.unpack('<f', array[current_index+4:current_index+8])[0],
                    'g': struct.unpack('<f', array[current_index+8:current_index+12])[0],
                    'b': struct.unpack('<f', array[current_index+12:current_index+16])[0]
                },
                'Direction': {
                    "x": struct.unpack('<f', array[current_index+16:current_index+20])[0],
                    "y": struct.unpack('<f', array[current_index+20:current_index+24])[0],
                    "z": struct.unpack('<f', array[current_index+24:current_index+28])[0]
                }
            })
            current_index += 28

        # 创建字典表示
        vmd.dict = {
            'Vision': vmd.vision,
            'ModelName': vmd.model_name,
            'BoneKeyFrameNumber': vmd.bone_keyframe_number,
            'BoneKeyFrameRecord': vmd.bone_keyframe_record,
            'MorphKeyFrameNumber': vmd.morph_keyframe_number,
            'MorphKeyFrameRecord': vmd.morph_keyframe_record,
            'CameraKeyFrameNumber': vmd.camera_keyframe_number,
            'CameraKeyFrameRecord': vmd.camera_keyframe_record,
            'LightKeyFrameNumber': vmd.light_keyframe_number,
            'LightKeyFrameRecord': vmd.light_keyframe_record
        }

        return vmd

    def convert_quaternions_to_euler(self) -> None:
        """将所有骨骼关键帧的四元数转换为YXZ欧拉角（角度制）"""
        for frame in self.bone_keyframe_record:
            quat = frame["Rotation"]
            # 转换为YXZ欧拉角（角度）
            euler = self.quaternion_to_yxz_euler(
                quat["x"], quat["y"], quat["z"], quat["w"]
            )
            frame["RotationEuler"] = {
                "y": euler[0],  # Yaw (Y-axis)
                "x": euler[1],  # Pitch (X-axis)
                "z": euler[2]   # Roll (Z-axis)
            }
            # 移除原始四元数（可选）
            # del frame["Rotation"]

    @staticmethod
    def quaternion_to_yxz_euler(x: float, y: float, z: float, w: float) -> Tuple[float, float, float]:
        """
        将四元数转换为YXZ欧拉角（角度制）
        公式来源：Three.js (MIT License)
        """
        # 万向节死锁阈值
        GIMBAL_LOCK_THRESHOLD = 0.99999
        
        # 计算中间值
        sqw = w * w
        sqx = x * x
        sqy = y * y
        sqz = z * z
        
        # Y轴旋转 (Yaw)
        y_angle = math.degrees(math.atan2(2 * (w * y + z * x), sqw - sqx - sqy + sqz))
        
        # X轴旋转 (Pitch) - 需要检查万向节死锁
        sin_pitch = 2 * (w * x - y * z)
        sin_pitch = max(min(sin_pitch, 1.0), -1.0)  # 限制在[-1,1]范围内
        
        if abs(sin_pitch) >= GIMBAL_LOCK_THRESHOLD:
            # 万向节死锁情况
            x_angle = math.degrees(math.copysign(math.pi / 2, sin_pitch))
            z_angle = 0.0
        else:
            x_angle = math.degrees(math.asin(sin_pitch))
            # Z轴旋转 (Roll)
            z_angle = math.degrees(math.atan2(2 * (w * z + x * y), sqw - sqx + sqy - sqz))
        
        # 规范化角度到[-180, 180]范围
        y_angle = (y_angle + 180) % 360 - 180
        x_angle = (x_angle + 180) % 360 - 180
        z_angle = (z_angle + 180) % 360 - 180
        
        return (round(y_angle, 4), round(x_angle, 4), round(z_angle, 4))

    def to_anim_json(self) -> Dict[str, Any]:
        """
        转换为动画JSON格式
        结构:
        {
            "metadata": { ... },
            "bone_animations": [
                {
                    "bone_name": "string",
                    "keyframes": [
                        {
                            "frame": int,
                            "position": [x, y, z],
                            "rotation_euler": [y_angle, x_angle, z_angle],
                            "rotation_quaternion": [x, y, z, w]  # 可选
                        },
                        ...
                    ]
                },
                ...
            ]
        }
        """
        # 按骨骼名称分组关键帧
        bone_groups = {}
        for frame in self.bone_keyframe_record:
            bone_name = frame["BoneName"]
            if bone_name not in bone_groups:
                bone_groups[bone_name] = []
            
            pos = frame["Position"]
            rot_q = frame["Rotation"]
            rot_e = frame["RotationEuler"]
            
            bone_groups[bone_name].append({
                "frame": frame["FrameTime"],
                "position": [round(pos["x"], 4), round(pos["y"], 4), round(pos["z"], 4)],
                "rotation_euler": [round(rot_e["y"], 4), round(rot_e["x"], 4), round(rot_e["z"], 4)],
                "rotation_quaternion": [round(rot_q["x"], 4), round(rot_q["y"], 4), round(rot_q["z"], 4), round(rot_q["w"], 4)]
            })
        
        # 创建骨骼动画数组
        bone_animations = []
        for bone_name, keyframes in bone_groups.items():
            # 按帧时间排序
            keyframes.sort(key=lambda x: x["frame"])
            bone_animations.append({
                "bone_name": bone_name,
                "keyframes": keyframes
            })
        
        # 创建元数据
        metadata = {
            "vmd_version": self.vision,
            "model_name": self.model_name,
            "total_frames": max(
                (kf["FrameTime"] for kf in self.bone_keyframe_record), 
                default=0
            ) + 1,
            "bone_count": len(bone_groups),
            "total_bone_keyframes": self.bone_keyframe_number,
            "generated_by": "VMD2JSON Converter"
        }
        
        return {
            "metadata": metadata,
            "bone_animations": bone_animations
        }

def convert_vmd_to_json(vmd_path: str, json_path: str, encoding: str = "shift-JIS") -> None:
    """
    转换VMD文件为JSON动画文件
    
    参数:
    vmd_path: VMD文件路径
    json_path: 输出JSON文件路径
    encoding: 模型名称编码 (默认: shift-JIS)
    """
    try:
        # 解析VMD文件
        vmd = Vmd.from_file(vmd_path, model_name_encode=encoding)
        
        # 转换四元数到欧拉角
        vmd.convert_quaternions_to_euler()
        
        # 生成动画JSON
        anim_data = vmd.to_anim_json()
        
        # 保存为JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(anim_data, f, ensure_ascii=False, indent=2)
        
        print(f"转换成功! 输出文件: {json_path}")
        print(f"模型名称: {anim_data['metadata']['model_name']}")
        print(f"骨骼数量: {anim_data['metadata']['bone_count']}")
        print(f"总帧数: {anim_data['metadata']['total_frames']}")
        print(f"骨骼关键帧总数: {anim_data['metadata']['total_bone_keyframes']}")
        
    except Exception as e:
        print(f"转换失败: {str(e)}")
        raise

if __name__ == "__main__":
    # 配置参数
    VMD_FILE = "dance.vmd"        # 输入VMD文件
    OUTPUT_JSON = "animation.json" # 输出JSON文件
    ENCODING = "shift-JIS"        # 模型名称编码 (中文模型可尝试"gbk"或"utf-8")
    
    # 执行转换
    convert_vmd_to_json(VMD_FILE, OUTPUT_JSON, ENCODING)