import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'evaluate'))

from evaluate_extraction import evaluate as evaluate_extraction  # noqa: E402
from evaluate_retrieval import evaluate as evaluate_retrieval  # noqa: E402
from evaluate_review import evaluate as evaluate_review  # noqa: E402


def test_extraction_evaluator_flags_hallucinated_entity():
    cases = [{'ground_truth': {'company_name': 'A', 'products': [], 'equipment': [], 'raw_materials': [], 'environmental_facilities': []},
              'prediction': {'company_name': 'A', 'products': [{'name': '不存在产品'}], 'equipment': [], 'raw_materials': [], 'environmental_facilities': []}}]
    assert evaluate_extraction(cases)['unsupported_extracted_fact_count'] == 1


def test_retrieval_evaluator_tracks_wrong_jurisdiction():
    result = evaluate_retrieval([{'expected_document_ids': [1], 'result_document_ids': [1], 'expected_jurisdiction': '江苏', 'returned_metadata': [{'jurisdiction': '浙江'}]}])
    assert result['recall_at_5'] == 1
    assert result['wrong_jurisdiction_count'] == 1


def test_review_evaluator_tracks_critical_recall():
    result = evaluate_review([{'expected_issues': [{'id': 'x', 'severity': 'critical'}], 'detected_issues': [{'id': 'x', 'severity': 'critical'}]}])
    assert result['critical_recall'] == 1

