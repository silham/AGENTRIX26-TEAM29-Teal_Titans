"""Owner: M5. Form-assist API endpoints.

Routes (all protected by M1's get_current_user):
  POST /forms/explain    explain confusing form fields in plain language
  POST /forms/validate   validate a citizen's filled-in form data
  GET  /forms/_ping      health probe
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.jwt import CurrentUser, get_current_user
from app.graph.nodes.form import explain_fields, validate_form
from app.schemas.document import (
    FieldExplanation,
    FormExplainRequest,
    FormExplainResponse,
    FormFieldIssue,
    FormValidateRequest,
    FormValidateResponse,
)

router = APIRouter(prefix="/forms", tags=["forms"])


# ---------------------------------------------------------------------------
# Health probe
# ---------------------------------------------------------------------------


@router.get("/_ping")
def ping(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"ok": True, "owner": "M5"}


# ---------------------------------------------------------------------------
# POST /forms/explain
# ---------------------------------------------------------------------------


@router.post("/explain", response_model=FormExplainResponse)
def form_explain(
    req: FormExplainRequest,
    user: CurrentUser = Depends(get_current_user),
) -> FormExplainResponse:
    """
    Ask the Form Assistant to explain one or more fields of a Sri Lankan
    government form in plain language (English, Sinhala, or Tamil).
    """
    if not req.fields:
        raise HTTPException(status_code=422, detail="At least one field must be specified.")

    raw_explanations = explain_fields(
        form_name=req.form_name,
        fields=req.fields,
        language=req.language,
    )

    explanations = [
        FieldExplanation(
            field=item.get("field", ""),
            explanation=item.get("explanation", ""),
            example=item.get("example"),
        )
        for item in raw_explanations
    ]

    return FormExplainResponse(form_name=req.form_name, explanations=explanations)


# ---------------------------------------------------------------------------
# POST /forms/validate
# ---------------------------------------------------------------------------


@router.post("/validate", response_model=FormValidateResponse)
def form_validate(
    req: FormValidateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> FormValidateResponse:
    """
    Validate a citizen's filled-in form data.
    Returns per-field issues and a plain-language summary.
    """
    if not req.filled_data:
        raise HTTPException(status_code=422, detail="filled_data must not be empty.")

    result = validate_form(
        form_name=req.form_name,
        filled_data=req.filled_data,
        language=req.language,
    )

    raw_issues = result.get("issues", [])
    field_issues = [
        FormFieldIssue(
            field=issue.get("field", ""),
            issue=issue.get("issue", ""),
            suggestion=issue.get("suggestion"),
        )
        for issue in raw_issues
    ]

    return FormValidateResponse(
        form_name=req.form_name,
        is_valid=bool(result.get("is_valid", False)),
        issues=field_issues,
        summary=result.get("summary", ""),
    )
