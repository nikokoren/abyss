"""Small, inspectable preference ranker on verified pretrained image features."""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

FEATURE_SPACE = 'resnet18-imagenet1k-v1+quality-v1'
FEATURE_COUNT = 518
WEIGHTS_URL = 'https://download.pytorch.org/models/resnet18-f37072fd.pth'
WEIGHTS_PREFIX = 'f37072fd'
WEIGHTS_SHA256 = 'f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec'
log = logging.getLogger(__name__)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def vector(value):
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (FEATURE_COUNT,) or not np.isfinite(result).all() or np.max(np.abs(result)) > 10:
        raise ValueError('Invalid image feature vector')
    return result


class ImageEncoder:
    """CPU ResNet18 appearance embeddings; no captioning or subject detector."""
    def __init__(self):
        import torch
        from torchvision.models import resnet18, ResNet18_Weights
        torch.set_num_threads(2)
        self.torch = torch
        if 'TORCH_HOME' not in os.environ:
            torch.hub.set_dir(str(Path('output/vision-cache').resolve()))
        path = Path(torch.hub.get_dir()) / 'checkpoints' / Path(WEIGHTS_URL).name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            torch.hub.download_url_to_file(WEIGHTS_URL, str(path), hash_prefix=WEIGHTS_SHA256, progress=False)
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        if checksum != WEIGHTS_SHA256:
            raise ValueError('Pretrained encoder checksum failed; cached weights were not used')
        network = resnet18(weights=None)
        network.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
        self.model = torch.nn.Sequential(*list(network.children())[:-1]).eval()
        self.transform = ResNet18_Weights.IMAGENET1K_V1.transforms()
        self.provenance = {'feature_space': FEATURE_SPACE, 'architecture': 'ResNet18',
                           'weights_url': WEIGHTS_URL, 'weights_sha256': checksum, 'device': 'cpu'}

    def encode(self, image, metrics):
        with self.torch.inference_mode():
            output = self.model(self.transform(image.convert('RGB')).unsqueeze(0)).flatten().numpy().astype(float)
        norm = np.linalg.norm(output)
        if norm:
            output /= norm
        head = [1, metrics['brightness'], metrics['contrast'], metrics['sharpness'], metrics['clipped'], metrics['base_score']]
        result = np.concatenate((head, output))
        return [round(float(v), 7) for v in vector(result)]


def load_model(path):
    if not path or not Path(path).exists():
        return None
    try:
        data = json.loads(Path(path).read_text())
        if data.get('schema_version') != 1 or data.get('feature_space') != FEATURE_SPACE:
            raise ValueError('Incompatible preference model')
        if data.get('status') != 'ready':
            return None
        weights = np.asarray(data['weights'], dtype=float)
        if weights.shape != (FEATURE_COUNT,) or not np.isfinite(weights).all() or np.max(np.abs(weights)) > 1000:
            raise ValueError('Invalid preference weights')
        if data.get('comparisons', 0) < 8 or data.get('pairwise_comparisons', 0) < 4:
            raise ValueError('Preference model has insufficient feedback')
        if not isinstance(data.get('model_id'), str) or len(data['model_id']) != 64:
            raise ValueError('Invalid model identity')
        identity = digest({k: data[k] for k in ('feature_space', 'reviewer', 'dataset_hash', 'weights')})
        if identity != data['model_id']:
            raise ValueError('Preference model identity/checksum mismatch')
        return data
    except (ValueError, KeyError, TypeError, OSError) as exc:
        log.warning('Preference model unavailable; using quality scoring: %s', exc)
        return None


def rank(metrics, features, model):
    if not model or features is None:
        return {'selection_score': metrics['score'], 'preference_score': None, 'preference_weight': 0}
    values = vector(features)
    value = float(np.dot(values, np.asarray(model['weights'])))
    probability = float(1 / (1 + np.exp(-np.clip(value, -30, 30))))
    weight = min(.45, .45 * model['comparisons'] / 30)
    from .imaging import similarity
    repeat = max((similarity(metrics['fingerprint'], h) for h in model.get('repetitive_hashes', [])), default=0)
    repeat_penalty = .15 * max(0, (repeat - .85) / .15)
    score = (1 - weight) * metrics['score'] + weight * probability - repeat_penalty
    return {'selection_score': round(float(score), 7), 'preference_score': round(probability, 7),
            'preference_weight': round(weight, 4), 'manual_repeat_penalty': round(repeat_penalty, 4)}


def _fit(rows):
    x = np.asarray(rows, dtype=float)
    weights = np.zeros(FEATURE_COUNT)
    if not len(x):
        return weights
    # Pairwise logistic loss, with zero-utility anchors for explicit rejections.
    for _ in range(500):
        probability = 1 / (1 + np.exp(-np.clip(x @ weights, -30, 30)))
        gradient = x.T @ (probability - 1) / len(x) + .025 * weights
        weights -= .8 * gradient
    return weights


def train(documents, reviewer):
    latest, frames = {}, {}
    for document in documents:
        if document.get('reviewer') != reviewer:
            continue
        if document.get('feature_space') != FEATURE_SPACE:
            raise ValueError('Feedback feature space mismatch')
        for key, frame in document['frames'].items():
            vector(frame['features'])
            if key in frames:
                if not np.allclose(vector(frames[key]['features']), vector(frame['features']), atol=1e-5, rtol=1e-5):
                    raise ValueError('Conflicting features for the same reviewed image')
            else:
                frames[key] = frame
        order = (document['updated_at'], document['issue_number'])
        for comparison in document['comparisons']:
            key = comparison['key']
            if key not in latest or order > latest[key][0]:
                latest[key] = (order, comparison)
    comparisons = [v[1] for _, v in sorted(latest.items())]
    rows, row_groups, pairwise, repetitive = [], [], [], []
    parent = {}

    def find(key):
        parent.setdefault(key, key)
        if parent[key] != key:
            parent[key] = find(parent[key])
        return parent[key]

    for comparison in comparisons:
        a, b = frames[comparison['a']], frames[comparison['b']]
        ra, rb = a['recording_url'], b['recording_url']
        parent[find(ra)] = find(rb)
    for comparison in comparisons:
        a, b = frames[comparison['a']], frames[comparison['b']]
        group = find(a['recording_url'])
        xa, xb = vector(a['features']), vector(b['features'])
        choice = comparison['choice']
        if choice in ('a', 'b'):
            winner, loser = (a, b) if choice == 'a' else (b, a)
            difference = vector(winner['features']) - vector(loser['features'])
            rows.append(difference); row_groups.append(group)
            pairwise.append((difference, group, winner['quality_score'] - loser['quality_score']))
        elif choice == 'neither':
            rows.extend((-xa, -xb)); row_groups.extend((group, group))
        else:
            raise ValueError('Unknown feedback choice')
        for frame_id in comparison.get('repetitive', []):
            if frame_id not in (comparison['a'], comparison['b']):
                raise ValueError('Repetitive flag outside the reviewed pair')
            frame = frames[frame_id]
            rows.append(-vector(frame['features'])); row_groups.append(group)
            repetitive.append(frame['fingerprint'])
    evaluation = {'status': 'unavailable', 'reason': 'Need at least three independent recording groups and held-out choices'}
    groups = sorted(set(row_groups), key=lambda g: digest(g))
    if len(groups) >= 3 and len(pairwise) >= 15:
        held = set(groups[:max(1, len(groups) // 5)])
        train_rows = [x for x, group in zip(rows, row_groups) if group not in held]
        test_rows = [(x, baseline) for x, group, baseline in pairwise if group in held]
        if train_rows and len(test_rows) >= 3:
            held_weights = _fit(train_rows)
            accuracy = lambda values: sum(1 if v > 0 else .5 if v == 0 else 0 for v in values) / len(values)
            evaluation = {'status': 'measured', 'split': 'held_out_connected_recording_groups',
                          'test_comparisons': len(test_rows),
                          'accuracy': accuracy([float(x @ held_weights) for x, _ in test_rows]),
                          'quality_baseline_accuracy': accuracy([q for _, q in test_rows])}
    weights = [round(float(v), 8) for v in _fit(rows)]
    semantic = [{'a': c['a'], 'b': c['b'], 'choice': c['choice'], 'repetitive': c.get('repetitive', [])} for c in comparisons]
    model = {'schema_version': 1, 'feature_space': FEATURE_SPACE, 'reviewer': reviewer,
             'trained_at': datetime.now(timezone.utc).isoformat(),
             'status': 'ready' if len(comparisons) >= 8 and len(pairwise) >= 4 else 'needs_more_feedback',
             'comparisons': len(comparisons), 'pairwise_comparisons': len(pairwise),
             'neither_comparisons': sum(c['choice'] == 'neither' for c in comparisons),
             'dataset_hash': digest(semantic), 'weights': weights,
             'repetitive_hashes': list(dict.fromkeys(repetitive))[-48:], 'evaluation': evaluation,
             'note': 'Appearance preference ranker, not a semantic subject detector; unmeasured evaluation is provisional.'}
    model['model_id'] = digest({k: model[k] for k in ('feature_space', 'reviewer', 'dataset_hash', 'weights')})
    return model
