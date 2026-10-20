#!/usr/bin/env bash
# Awaaz Pehchaan (who is talking): installs sherpa-onnx into Hoola core's venv and downloads the two free
# speaker-recognition models (CPU only, ~70 MB). Run once on the VPS:
#   bash ~/santosh_app/server/deploy/setup_voiceid.sh && pm2 restart santosh --update-env
#
# Models (both free for commercial use):
#   CAM++ (3D-Speaker, Apache-2.0)  https://github.com/modelscope/3D-Speaker
#   TitaNet-small (NVIDIA NeMo, CC-BY-4.0)  https://catalog.ngc.nvidia.com/orgs/nvidia/teams/nemo/models/titanet_small
set -euo pipefail
CORE="${CORE:-$HOME/apps/santosh-core}"
DIR="${VOICEID_MODELS_DIR:-$CORE/data/voiceid_models}"
REL="https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models"
"$CORE/.venv/bin/pip" install -q "sherpa-onnx>=1.12" "numpy>=1.24"
mkdir -p "$DIR"
for f in 3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx nemo_en_titanet_small.onnx; do
  if [ ! -s "$DIR/$f" ]; then
    echo "downloading $f"
    curl -fsSL -o "$DIR/$f.part" "$REL/$f" && mv "$DIR/$f.part" "$DIR/$f"
  fi
done
"$CORE/.venv/bin/python" - "$DIR" <<'PY'
import sys, sherpa_onnx, numpy as np
for f in ("3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx", "nemo_en_titanet_small.onnx"):
    ex = sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=f"{sys.argv[1]}/{f}", num_threads=2))
    s = ex.create_stream(); s.accept_waveform(16000, np.zeros(16000 * 2, dtype=np.float32)); s.input_finished()
    print("OK", f, "dim", len(ex.compute(s)))
PY
echo "Awaaz Pehchaan ready. Models in $DIR (VOICEID_MODELS_DIR, default ./data/voiceid_models from $CORE)."
