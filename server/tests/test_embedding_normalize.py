"""embedding_service 純邏輯：維度正規化 + cosine。不打外部 API。"""
import numpy as np

from app.services.embedding_service import EmbeddingService, _normalize_to_512


def test_normalize_pads_short_vector():
    out = _normalize_to_512([1.0, 2.0, 3.0])
    assert len(out) == 512
    assert out[3:] == [0.0] * 509  # 補零


def test_normalize_truncates_long_vector():
    out = _normalize_to_512([0.5] * 768)  # bge-base 768 維
    assert len(out) == 512


def test_normalize_output_is_unit_vector():
    for vec in ([1.0, 2.0, 3.0], [0.5] * 768, list(range(1, 513))):
        out = _normalize_to_512([float(x) for x in vec])
        assert abs(np.linalg.norm(out) - 1.0) < 1e-5


def test_normalize_zero_vector_no_crash():
    out = _normalize_to_512([0.0] * 512)
    assert len(out) == 512
    assert np.linalg.norm(out) == 0.0


def test_cosine_similarity():
    a = [1.0, 0.0, 0.0]
    assert abs(EmbeddingService.cosine_similarity(a, a) - 1.0) < 1e-9
    assert abs(EmbeddingService.cosine_similarity(a, [0.0, 1.0, 0.0])) < 1e-9
    # 零向量不能除以零
    assert EmbeddingService.cosine_similarity(a, [0.0, 0.0, 0.0]) == 0.0
