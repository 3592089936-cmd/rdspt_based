param(
    [string]$EnvName = "dair311"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/5] Upgrade pip tooling in conda env $EnvName"
conda run -n $EnvName python -m pip install --upgrade pip setuptools wheel
conda run -n $EnvName python -m pip install "numpy<2"

Write-Host "[2/5] Install CUDA-enabled PyTorch for Python 3.11"
conda run -n $EnvName python -m pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu121

Write-Host "[3/5] Install OpenMMLab package manager"
conda run -n $EnvName python -m pip install -U openmim

Write-Host "[4/5] Install MM stack"
conda run -n $EnvName mim install mmengine==0.10.5
conda run -n $EnvName mim install "mmcv==2.1.0"
conda run -n $EnvName mim install "mmdet==3.3.0"
conda run -n $EnvName mim install "mmdet3d==1.4.0"

Write-Host "[5/5] Install DAIR-side helpers"
conda run -n $EnvName python -m pip install python-lzf pillow matplotlib pyquaternion shapely opencv-python pyyaml

Write-Host "Verification:"
conda run -n $EnvName python -c "import torch, mmengine, mmcv, mmdet, mmdet3d; print('torch', torch.__version__); print('cuda', torch.cuda.is_available(), torch.version.cuda); print('mmengine', mmengine.__version__); print('mmcv', mmcv.__version__); print('mmdet', mmdet.__version__); print('mmdet3d', mmdet3d.__version__)"
