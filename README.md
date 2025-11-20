# VMD2Mi - VMD 动作转换工具

感觉不太可用，会乱抽抽，动作好像也不太对

这是一个用于将 MMD (MikuMikuDance) 的动作数据文件 (`.vmd`) 转换为 Mine-imator 可用的关键帧数据 (`.miframes`) 的 Python 工具。

本项目包含两个主要脚本：
1. `vmd2miframes.py`: 核心转换工具，支持骨骼映射、坐标转换和平滑处理。
2. `vmd_converter.py`: 通用 VMD 解析工具，将 VMD 转换为易读的 JSON 格式。

## ✨ 功能特性

- **VMD 解析**: 支持 VMD 格式版本 1 和 2。
- **智能骨骼映射**: 内置标准 MMD 骨骼到 Mine-imator 人物模型的映射配置（支持身体、头部、四肢等）。
- **坐标系转换**: 自动处理 MMD 左手坐标系到 Mine-imator 坐标系的转换，包括轴向反转和旋转修正。
- **动作平滑**: 集成 **Savitzky-Golay 滤波器**，有效去除动作抖动，使动画更流畅。
- **角度修复**: 自动处理欧拉角万向节死锁和 ±180 度跳变问题。
- **高度可配置**: 支持自定义骨骼映射规则（反转轴、交换轴等）。

## 🛠️ 环境要求

需要 Python 3.x 环境，并安装以下依赖库：

```bash
pip install numpy scipy
```

## 🚀 使用方法

### 1. 动作转换 (VMD -> MiFrames)

主要使用 `vmd2miframes.py` 脚本。

**基本用法:**

默认情况下，脚本会查找当前目录下的 `dance.vmd` 并生成 `dance_custom_v8.miframes`。

```bash
python vmd2miframes.py
```

**代码调用:**

你也可以在 Python 代码中导入并调用转换函数：

```python
from vmd2miframes import convert_vmd_to_miframes

convert_vmd_to_miframes(
    vmd_path="path/to/your.vmd",
    output_path="output.miframes",
    fps=30,             # 帧率
    scale_factor=0.1,   # 缩放比例 (MMD单位 -> MI单位)
    smooth_window=15    # 平滑窗口大小 (越大越平滑，但细节越少)
)
```

### 2. 通用格式转换 (VMD -> JSON)

如果你只需要解析 VMD 文件内容，可以使用 `vmd_converter.py`。

```bash
python vmd_converter.py
```

这将把 `dance.vmd` 转换为 `animation.json`，包含详细的骨骼、表情、相机和灯光数据。

## ⚙️ 配置说明

### 骨骼映射 (BONE_MAP)

在 `vmd2miframes.py` 中，`BONE_MAP` 字典定义了 MMD 骨骼如何映射到目标模型部分。

配置项说明：
- `target`: 目标模型部位名称 (如 `body`, `head`, `left_arm`).
- `type`: 映射类型 (`rot` 旋转, `bend` 弯曲, `root` 根坐标).
- `invert`: 是否反转数值 (True/False 或指定轴列表 `['x', 'z']`).
- `swap_yz`: 是否交换 Y 和 Z 轴 (用于修复某些轴向错位).
- `src_axis`: 指定源轴 (仅用于 `bend` 类型).

## 📂 文件结构

- `vmd2miframes.py`: 主转换程序 (VMD -> MiFrames).
- `vmd_converter.py`: VMD 解析与 JSON 导出工具.
- `test_smoothing.py`: 平滑算法测试脚本.
- `dance.vmd`: 示例动作文件.
- `template.miframes`: MiFrames 模板文件.

## 📝 注意事项

- 转换后的 `.miframes` 文件可以直接导入 Mine-imator 中使用。
- 如果发现动作鬼畜或方向错误，请检查 `BONE_MAP` 中的 `invert` 和 `swap_yz` 设置。
- 平滑参数 `smooth_window` 建议设置为奇数，通常 5-15 之间效果较好。
