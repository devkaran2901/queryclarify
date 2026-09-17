import json
import os
import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.api_schemas import QueryRequest
from app.services.orchestrator import orchestrator
from app.services.sql_generator import sql_generator
from app.services.sql_validator import sql_validator
from app.services.query_executor import query_executor
from evaluation.metrics import calculate_binary_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evaluate")


def run_evaluation():
    dataset_path = Path(__file__).parent / "dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    logger.info(f"Running evaluation benchmark on {len(dataset)} items...")

    baseline_valid_sql = 0
    baseline_exec_success = 0
    
    qc_valid_sql = 0
    qc_exec_success = 0
    qc_clarifications_requested = 0
    qc_clarification_turns = []

    y_true_ambiguous = []
    y_pred_ambiguous = []

    for item in dataset:
        q_id = item["id"]
        question = item["question"]
        is_ambiguous_gt = item["ambiguous"]

        # -------------------------------------------------------------
        # 1. BASELINE PIPELINE (No Ambiguity Check, Direct Text-to-SQL)
        # -------------------------------------------------------------
        sql_res_base = sql_generator.generate(question=question)
        is_valid_b, clean_sql_b, _, _ = sql_validator.validate_and_sanitize(sql_res_base.sql)
        if is_valid_b:
            baseline_valid_sql += 1
            exec_ok_b, _, _, _, _, _ = query_executor.execute(clean_sql_b)
            if exec_ok_b:
                baseline_exec_success += 1

        # -------------------------------------------------------------
        # 2. QUERYCLARIFY PIPELINE (Ambiguity-Aware)
        # -------------------------------------------------------------
        # Turn 1
        req1 = QueryRequest(question=question)
        res1 = orchestrator.process_query(req1)
        
        is_pred_ambiguous = (res1.status == "clarification_required")
        y_true_ambiguous.append(is_ambiguous_gt)
        y_pred_ambiguous.append(is_pred_ambiguous)

        if is_pred_ambiguous:
            qc_clarifications_requested += 1
            turns = 2
            # Simulate user selecting first offered clarification option
            selected_opt_id = res1.clarification_options[0].id if res1.clarification_options else "highest_revenue"
            req2 = QueryRequest(
                session_id=res1.session_id,
                question=question,
                selected_option=selected_opt_id
            )
            res2 = orchestrator.process_query(req2)
            final_res = res2
        else:
            turns = 1
            final_res = res1

        qc_clarification_turns.append(turns)

        if final_res.status == "completed":
            qc_valid_sql += 1
            qc_exec_success += 1

    # Calculate metrics
    ambiguity_metrics = calculate_binary_metrics(y_true_ambiguous, y_pred_ambiguous)
    avg_turns = round(sum(qc_clarification_turns) / len(qc_clarification_turns), 2)

    total_q = len(dataset)
    b_sql_acc = round((baseline_valid_sql / total_q) * 100, 2)
    b_exec_acc = round((baseline_exec_success / total_q) * 100, 2)

    qc_sql_acc = round((qc_valid_sql / total_q) * 100, 2)
    qc_exec_acc = round((qc_exec_success / total_q) * 100, 2)

    report = {
        "total_questions": total_q,
        "baseline": {
            "sql_validity_pct": b_sql_acc,
            "execution_accuracy_pct": b_exec_acc
        },
        "queryclarify": {
            "sql_validity_pct": qc_sql_acc,
            "execution_accuracy_pct": qc_exec_acc,
            "clarifications_requested": qc_clarifications_requested,
            "avg_clarification_turns": avg_turns
        },
        "ambiguity_detection": ambiguity_metrics
    }

    # Save results
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    with open(results_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 50)
    print("QUERYCLARIFY EVALUATION BENCHMARK REPORT")
    print("=" * 50)
    print(f"Total Dataset Questions: {total_q}")
    print("\nBASELINE (Direct Text-to-SQL):")
    print(f"  - SQL Validity:       {b_sql_acc}%")
    print(f"  - Execution Accuracy: {b_exec_acc}%")
    print("\nQUERYCLARIFY (Ambiguity-Aware):")
    print(f"  - SQL Validity:       {qc_sql_acc}%")
    print(f"  - Execution Accuracy: {qc_exec_acc}%")
    print(f"  - Avg Clarification Turns: {avg_turns}")
    print("\nAMBIGUITY DETECTION PERFORMANCE:")
    print(f"  - Precision: {ambiguity_metrics['precision']}%")
    print(f"  - Recall:    {ambiguity_metrics['recall']}%")
    print(f"  - F1 Score:  {ambiguity_metrics['f1']}%")
    print(f"  - Accuracy:  {ambiguity_metrics['accuracy']}%")
    print("=" * 50 + "\n")

    return report


if __name__ == "__main__":
    run_evaluation()
