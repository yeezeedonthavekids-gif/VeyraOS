# Hardware video decoding (VA-API) through NVDEC on NVIDIA GPUs.
# Only set when the NVIDIA driver is actually loaded.
if [ -e /proc/driver/nvidia/version ] && [ -e /usr/lib/dri/nvidia_drv_video.so ]; then
    export LIBVA_DRIVER_NAME=nvidia
    export NVD_BACKEND=direct
fi
