from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.schemas import (
    ErrorResponse,
    HealthResponse,
    PaginatedTransactions,
    SummaryResponse,
    TransactionResponse,
)
from src.api.services import ResultsService
from src.ai.schemas import InvestigationResponse
from src.ai.service import InvestigationService


router = APIRouter()


def get_service() -> ResultsService:
    return ResultsService()


def get_investigation_service() -> InvestigationService:
    return InvestigationService()


def _safe_service_call(call):
    try:
        return call()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/health", response_model=HealthResponse)
def health(service: ResultsService = Depends(get_service)):
    records = _safe_service_call(lambda: len(service.load()))
    return {"status": "healthy", "service": "finance-reconciliation-api", "records_available": records}


@router.get("/summary", response_model=SummaryResponse, responses={503: {"model": ErrorResponse}})
def summary(service: ResultsService = Depends(get_service)):
    return _safe_service_call(service.summary)


@router.get("/transactions", response_model=PaginatedTransactions, responses={503: {"model": ErrorResponse}})
def transactions(
    final_status: str | None = None,
    exception_type: str | None = None,
    risk_level: str | None = None,
    ml_prediction: int | None = Query(default=None, ge=0, le=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = "risk_score",
    descending: bool = True,
    service: ResultsService = Depends(get_service),
):
    items, total = _safe_service_call(lambda: service.query(
        final_status=final_status,
        exception_type=exception_type,
        risk_level=risk_level,
        ml_prediction=ml_prediction,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        descending=descending,
    ))
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": ceil(total / page_size) if total else 0}


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse, responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
def transaction(transaction_id: str, service: ResultsService = Depends(get_service)):
    if not transaction_id.strip():
        raise HTTPException(status_code=422, detail="transaction_id must not be empty.")
    result = _safe_service_call(lambda: service.get_transaction(transaction_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return result


@router.post("/transactions/{transaction_id}/investigate", response_model=InvestigationResponse, responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
def investigate_transaction(
    transaction_id: str,
    service: InvestigationService = Depends(get_investigation_service),
):
    if not transaction_id.strip():
        raise HTTPException(status_code=422, detail="transaction_id must not be empty.")
    result = _safe_service_call(lambda: service.investigate(transaction_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return result


@router.get("/exceptions", response_model=PaginatedTransactions, responses={503: {"model": ErrorResponse}})
def exceptions(
    exception_type: str | None = None,
    risk_level: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    descending: bool = True,
    service: ResultsService = Depends(get_service),
):
    items, total = _safe_service_call(lambda: service.query(
        exception_type=exception_type,
        risk_level=risk_level,
        page=page,
        page_size=page_size,
        exceptions_only=True,
        descending=descending,
    ))
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": ceil(total / page_size) if total else 0}