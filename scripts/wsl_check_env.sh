source ~/miniconda3/etc/profile.d/conda.sh
conda activate dots_tts
python -c "import pytest; print('pytest', pytest.__version__)" 2>&1
python -c "import soundfile; print('soundfile', soundfile.__version__)" 2>&1
python -c "import librosa; print('librosa', librosa.__version__)" 2>&1
python -c "import numpy; print('numpy', numpy.__version__)" 2>&1
