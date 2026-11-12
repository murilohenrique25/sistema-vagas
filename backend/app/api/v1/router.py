"""API v1 router with versioned prefix /v1/."""

from fastapi import APIRouter

from app.api.v1.routes import account, admin, ai, applications, auth, companies, jobs, notifications, oauth, payments, reports, resumes, scheduler

v1_router = APIRouter(prefix="/v1")


@v1_router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for the v1 API."""
    return {"status": "healthy", "version": "1"}


# Include auth routes
v1_router.include_router(auth.router)
v1_router.include_router(account.router)

# Include OAuth routes
v1_router.include_router(oauth.router)

# Include resume routes
v1_router.include_router(resumes.router)
v1_router.include_router(companies.router)

# Include jobs routes
v1_router.include_router(jobs.router)
v1_router.include_router(reports.router)

# Include scheduler routes (for cron-triggered tasks)
v1_router.include_router(scheduler.router)

# Include application routes
v1_router.include_router(applications.router)

# Include payment routes
v1_router.include_router(payments.router)

# Include notification routes
v1_router.include_router(notifications.router)

# Include AI routes
v1_router.include_router(ai.router)

# Include admin routes
v1_router.include_router(admin.router)

# Future route inclusions will be added here as modules are implemented:
