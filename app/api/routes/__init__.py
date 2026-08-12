"""Router raíz de /api — toda ruta bajo este prefijo exige sesión autorizada (FR-001, T008)."""

from fastapi import APIRouter, Depends

from app.auth.session import get_current_user

api_router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])

from app.api.routes.candidate_documents import router as candidate_documents_router  # noqa: E402
from app.api.routes.mailbox_accounts import router as mailbox_accounts_router  # noqa: E402
from app.api.routes.providers import router as providers_router  # noqa: E402
from app.api.routes.reconciliations import router as reconciliations_router  # noqa: E402
from app.api.routes.sync_runs import mailbox_sync_router, sync_runs_router  # noqa: E402

api_router.include_router(mailbox_accounts_router)
api_router.include_router(mailbox_sync_router)
api_router.include_router(sync_runs_router)
api_router.include_router(candidate_documents_router)
api_router.include_router(providers_router)
api_router.include_router(reconciliations_router)
