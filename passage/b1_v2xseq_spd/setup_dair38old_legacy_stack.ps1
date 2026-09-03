$ErrorActionPreference = "Stop"

$wheelRoot = "D:\Dproject_coop3d\_legacy_wheels"
$python = "D:\anaconda\envs\dair38old\python.exe"

& $python -m pip install --no-index --find-links "$wheelRoot" `
    "torch==1.10.1+cu113" `
    "torchvision==0.11.2+cu113" `
    "mmcv-full==1.4.0" `
    "mmdet==2.14.0" `
    "mmsegmentation==0.14.1" `
    openmim

& $python -m pip install --no-index --find-links "$wheelRoot" `
    "numpy<1.20.0" `
    "networkx<2.3" `
    "numba==0.48.0" `
    "trimesh>=2.35.39,<2.35.40" `
    lyft_dataset_sdk `
    nuscenes-devkit `
    plyfile `
    scikit-image `
    tensorboard

& $python -m pip install --no-build-isolation "mmdet3d==0.17.1"

& $python -c "import torch, mmcv, mmdet, mmseg, mmdet3d; print('torch', torch.__version__); print('cuda', torch.cuda.is_available()); print('mmcv', mmcv.__version__); print('mmdet', mmdet.__version__); print('mmseg', mmseg.__version__); print('mmdet3d', mmdet3d.__version__)"
