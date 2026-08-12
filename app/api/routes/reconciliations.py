"""Endpoints de contracts/api.md para la conciliación bancaria (User Story 1 y 3)."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth.session import get_current_user
from app.models import bank_movement as bank_movement_model
from app.models import bank_statement as bank_statement_model
from app.models import candidate_document as candidate_document_model
from app.models import reconciliation_candidate as reconciliation_candidate_model
from app.services.reconciliation_service import ExtractoInvalidoError, procesar_extracto

router = APIRouter(prefix="/reconciliations", tags=["reconciliations"])


class ReconciliationSummary(BaseModel):
    id: int
    fecha_inicio: str
    fecha_fin: str
    total_movimientos: int
    conciliadas: int
    no_encontradas: int
    pendientes_revision: int


class MovementRef(BaseModel):
    movimiento_id: int
    fecha: str
    importe: float
    concepto: str


class ReconciledInvoiceRef(BaseModel):
    documento_id: int
    movimiento_id: int


class UnresolvedInvoiceRef(BaseModel):
    documento_id: int


class PendingInvoiceRef(BaseModel):
    documento_id: int
    candidatos: list[MovementRef]


class ReconciliationDetail(BaseModel):
    id: int
    fecha_inicio: str
    fecha_fin: str
    aportado_por: str
    fecha_aporte: str
    total_movimientos: int
    facturas_conciliadas: list[ReconciledInvoiceRef]
    facturas_no_encontradas: list[UnresolvedInvoiceRef]
    facturas_pendientes_revision: list[PendingInvoiceRef]
    movimientos_pendientes_de_justificar: list[MovementRef]


def _to_movement_ref(movimiento) -> MovementRef:
    return MovementRef(
        movimiento_id=movimiento.id,
        fecha=movimiento.fecha,
        importe=movimiento.importe,
        concepto=movimiento.concepto,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ReconciliationSummary)
async def create_reconciliation(
    extracto: UploadFile = File(...),  # noqa: B008 - patrón estándar de FastAPI
    persona_autorizada: str = Depends(get_current_user),
) -> ReconciliationSummary:
    contenido = await extracto.read()
    try:
        resultado = procesar_extracto(contenido, persona_autorizada)
    except ExtractoInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    statement = resultado["extracto"]
    return ReconciliationSummary(
        id=statement.id,
        fecha_inicio=statement.fecha_inicio,
        fecha_fin=statement.fecha_fin,
        total_movimientos=statement.total_movimientos,
        conciliadas=resultado["conciliadas"],
        no_encontradas=resultado["no_encontradas"],
        pendientes_revision=resultado["pendientes_revision"],
    )


@router.get("/{reconciliation_id}", response_model=ReconciliationDetail)
def get_reconciliation(
    reconciliation_id: int, _persona_autorizada: str = Depends(get_current_user)
) -> ReconciliationDetail:
    statement = bank_statement_model.get_by_id(reconciliation_id)
    if statement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conciliación no encontrada"
        )

    conciliadas = candidate_document_model.list_by_extracto(reconciliation_id, "CONCILIADA")
    no_encontradas = candidate_document_model.list_by_extracto(
        reconciliation_id, "NO ENCONTRADA EN EXTRACTO"
    )
    pendientes = candidate_document_model.list_by_extracto(
        reconciliation_id, "PENDIENTE REVISIÓN CONCILIACIÓN"
    )

    pendientes_refs = []
    for doc in pendientes:
        candidatos = reconciliation_candidate_model.list_for_documento(doc.id)
        movimientos = [bank_movement_model.get_by_id(c.movimiento_id) for c in candidatos]
        pendientes_refs.append(
            PendingInvoiceRef(
                documento_id=doc.id,
                candidatos=[_to_movement_ref(m) for m in movimientos if m is not None],
            )
        )

    pendientes_de_justificar = bank_movement_model.find_pendientes_de_justificar(reconciliation_id)

    return ReconciliationDetail(
        id=statement.id,
        fecha_inicio=statement.fecha_inicio,
        fecha_fin=statement.fecha_fin,
        aportado_por=statement.aportado_por,
        fecha_aporte=statement.fecha_aporte,
        total_movimientos=statement.total_movimientos,
        facturas_conciliadas=[
            ReconciledInvoiceRef(documento_id=doc.id, movimiento_id=doc.movimiento_bancario_id)
            for doc in conciliadas
        ],
        facturas_no_encontradas=[
            UnresolvedInvoiceRef(documento_id=doc.id) for doc in no_encontradas
        ],
        facturas_pendientes_revision=pendientes_refs,
        movimientos_pendientes_de_justificar=[
            _to_movement_ref(m) for m in pendientes_de_justificar
        ],
    )
