"""Self-service company profile routes for authenticated employers."""

from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.database import get_session
from app.models.company import Company
from app.core.config import settings
from app.schemas.company import CnpjLookupResponse, CompanyResponse, CompanyUpsert, normalize_and_validate_cnpj


router = APIRouter(prefix="/companies", tags=["companies"])


async def _lookup_cnpj(cnpj: str) -> CnpjLookupResponse:
    try:
        digits = normalize_and_validate_cnpj(cnpj)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        async with httpx.AsyncClient(timeout=settings.cnpj_lookup_timeout_seconds) as client:
            response = await client.get(f"{settings.cnpj_lookup_url.rstrip('/')}/{digits}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Consulta cadastral temporariamente indisponível") from exc
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado na base consultada")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Não foi possível consultar a situação do CNPJ")
    raw = response.json()
    address_parts = [raw.get("descricao_tipo_de_logradouro"), raw.get("logradouro"), raw.get("numero"), raw.get("complemento"), raw.get("bairro"), raw.get("cep")]
    return CnpjLookupResponse(
        cnpj=digits,
        legal_name=raw.get("razao_social") or "",
        name=raw.get("nome_fantasia") or raw.get("razao_social") or "",
        status=(raw.get("descricao_situacao_cadastral") or "NÃO INFORMADA").upper(),
        industry=raw.get("cnae_fiscal_descricao"),
        phone=raw.get("ddd_telefone_1"),
        city=raw.get("municipio"),
        state=raw.get("uf"),
        address=", ".join(str(part).strip() for part in address_parts if part),
    )


def _require_employer(user: CurrentUser) -> None:
    if user.role != "employer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas empregadores podem gerenciar empresas")


@router.get("/cnpj/{cnpj}", response_model=CnpjLookupResponse)
async def lookup_cnpj(cnpj: str, user: CurrentUser = Depends(get_current_user)) -> CnpjLookupResponse:
    _require_employer(user)
    return await _lookup_cnpj(cnpj)


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CompanyResponse:
    _require_employer(user)
    company = (await session.execute(select(Company).where(Company.owner_id == user.id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa ainda não cadastrada")
    return CompanyResponse.model_validate(company)


@router.put("/me", response_model=CompanyResponse)
async def upsert_my_company(
    data: CompanyUpsert,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CompanyResponse:
    _require_employer(user)
    company = (await session.execute(select(Company).where(Company.owner_id == user.id))).scalar_one_or_none()
    values = data.model_dump()
    # The external source enriches the record and blocks a known non-active CNPJ.
    # Temporary provider failure does not prevent the employer from saving data.
    lookup: CnpjLookupResponse | None = None
    try:
        lookup = await _lookup_cnpj(data.cnpj)
    except HTTPException as exc:
        if exc.status_code in (400, 404):
            raise
    if lookup and lookup.status != "ATIVA":
        raise HTTPException(status_code=400, detail=f"CNPJ com situação cadastral {lookup.status}; é necessário estar ATIVA")
    if lookup:
        values.update(cnpj_status=lookup.status, cnpj_checked_at=datetime.now(timezone.utc), cnpj_source=lookup.source)
    if company:
        for key, value in values.items():
            setattr(company, key, value)
        company.updated_at = datetime.now(timezone.utc)
    else:
        company = Company(owner_id=user.id, **values)
        session.add(company)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CNPJ já cadastrado") from exc
    await session.refresh(company)
    return CompanyResponse.model_validate(company)
