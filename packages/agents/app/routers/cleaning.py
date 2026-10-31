from fastapi import APIRouter

from orchestrator.cleaning import scan

from ..models import AnomalyOut, CleaningReport, CleaningScanRequest

router = APIRouter(prefix="/cleaning", tags=["cleaning"])


@router.post("/scan", response_model=CleaningReport)
def scan_data(body: CleaningScanRequest):
    anomalies = scan(body.headers, body.rows)
    return CleaningReport(
        row_count=len(body.rows),
        anomaly_count=len(anomalies),
        anomalies=[AnomalyOut(**a.__dict__) for a in anomalies],
    )
