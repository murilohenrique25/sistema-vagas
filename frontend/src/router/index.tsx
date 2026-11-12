import { createBrowserRouter } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { CircularProgress, Box } from '@mui/material';
import MainLayout from '../layouts/MainLayout';
import ProtectedRoute from './ProtectedRoute';
import AdminRoute from './AdminRoute';
import RouteErrorPage from '../components/RouteErrorPage';

// Lazy-loaded pages
const Home = lazy(() => import('../pages/Home'));
const Login = lazy(() => import('../pages/Login'));
const Register = lazy(() => import('../pages/Register'));
const ForgotPassword = lazy(() => import('../pages/ForgotPassword'));
const ResetPassword = lazy(() => import('../pages/ResetPassword'));
const VerifyEmail = lazy(() => import('../pages/VerifyEmail'));
const PrivacyPolicy = lazy(() => import('../pages/Legal').then(m => ({ default: m.PrivacyPolicy })));
const TermsOfUse = lazy(() => import('../pages/Legal').then(m => ({ default: m.TermsOfUse })));
const CookiePolicy = lazy(() => import('../pages/Legal').then(m => ({ default: m.CookiePolicy })));
const Dashboard = lazy(() => import('../pages/Dashboard'));
const Jobs = lazy(() => import('../pages/Jobs'));
const ResumeCreate = lazy(() => import('../pages/resume/ResumeCreate'));
const CompanyProfile = lazy(() => import('../pages/company/CompanyProfile'));
const NotFound = lazy(() => import('../pages/NotFound'));
const Wallet = lazy(() => import('../pages/Wallet'));
const AccountSettings = lazy(() => import('../pages/AccountSettings'));

// Lazy-loaded admin pages
const AdminDashboard = lazy(() => import('../pages/admin/AdminDashboard'));
const AdminUsers = lazy(() => import('../pages/admin/AdminUsers'));
const AdminFinancials = lazy(() => import('../pages/admin/AdminFinancials'));
const AdminAuditLog = lazy(() => import('../pages/admin/AdminAuditLog'));
const AdminPaymentSettings = lazy(() => import('../pages/admin/AdminPaymentSettings'));
const AdminSecurity = lazy(() => import('../pages/admin/AdminSecurity'));
const AdminJobReports = lazy(() => import('../pages/admin/AdminJobReports'));

// Lazy-loaded job pages
const JobDetail = lazy(() =>
    import('../pages/jobs/JobDetail').then((m) => ({ default: m.default }))
);
const JobForm = lazy(() =>
    import('../pages/jobs/JobForm').then((m) => ({ default: m.default }))
);
const EmployerJobsPanel = lazy(() =>
    import('../pages/jobs/EmployerJobsPanel').then((m) => ({ default: m.default }))
);

// Lazy-loaded application pages
const CandidateApplications = lazy(() =>
    import('../pages/applications/CandidateApplications').then((m) => ({ default: m.default }))
);
const EmployerApplicationsPanel = lazy(() =>
    import('../pages/applications/EmployerApplicationsPanel').then((m) => ({ default: m.default }))
);

// Lazy-loaded AI pages
const CandidateAnalysis = lazy(() =>
    import('../pages/ai/CandidateAnalysis').then((m) => ({ default: m.default }))
);
const JobCompatibility = lazy(() =>
    import('../pages/ai/JobCompatibility').then((m) => ({ default: m.default }))
);

// Lazy-loaded notification pages
const NotificationCenter = lazy(() =>
    import('../pages/notifications/NotificationCenter').then((m) => ({ default: m.default }))
);

function PageLoader() {
    return (
        <Box
            sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '50vh',
            }}
        >
            <CircularProgress />
        </Box>
    );
}

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
    return <Suspense fallback={<PageLoader />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
    {
        path: '/',
        element: <MainLayout />,
        errorElement: <RouteErrorPage />,
        children: [
            {
                index: true,
                element: (
                    <SuspenseWrapper>
                        <Home />
                    </SuspenseWrapper>
                ),
            },
            {
                path: 'login',
                element: (
                    <SuspenseWrapper>
                        <Login />
                    </SuspenseWrapper>
                ),
            },
            {
                path: 'register',
                element: (
                    <SuspenseWrapper>
                        <Register />
                    </SuspenseWrapper>
                ),
            },
            {
                path: 'forgot-password',
                element: <SuspenseWrapper><ForgotPassword /></SuspenseWrapper>,
            },
            {
                path: 'reset-password',
                element: <SuspenseWrapper><ResetPassword /></SuspenseWrapper>,
            },
            {
                path: 'verify-email',
                element: <SuspenseWrapper><VerifyEmail /></SuspenseWrapper>,
            },
            { path: 'privacy', element: <SuspenseWrapper><PrivacyPolicy /></SuspenseWrapper> },
            { path: 'terms', element: <SuspenseWrapper><TermsOfUse /></SuspenseWrapper> },
            { path: 'cookies', element: <SuspenseWrapper><CookiePolicy /></SuspenseWrapper> },
            {
                path: 'jobs',
                element: (
                    <SuspenseWrapper>
                        <Jobs />
                    </SuspenseWrapper>
                ),
            },
            {
                path: 'jobs/:jobId',
                element: (
                    <SuspenseWrapper>
                        <JobDetail />
                    </SuspenseWrapper>
                ),
            },
            // Protected routes
            {
                element: <ProtectedRoute />,
                children: [
                    {
                        path: 'dashboard',
                        element: (
                            <SuspenseWrapper>
                                <Dashboard />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/employer',
                        element: (
                            <SuspenseWrapper>
                                <Dashboard />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/employer/jobs',
                        element: (
                            <SuspenseWrapper>
                                <EmployerJobsPanel />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/employer/jobs/new',
                        element: (
                            <SuspenseWrapper>
                                <JobForm />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/employer/jobs/:jobId/edit',
                        element: (
                            <SuspenseWrapper>
                                <JobForm />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/employer/jobs/:jobId/applications',
                        element: (
                            <SuspenseWrapper>
                                <EmployerApplicationsPanel />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/candidate',
                        element: (
                            <SuspenseWrapper>
                                <Dashboard />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/candidate/applications',
                        element: (
                            <SuspenseWrapper>
                                <CandidateApplications />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'resume',
                        element: (
                            <SuspenseWrapper>
                                <ResumeCreate />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'resume/create',
                        element: (
                            <SuspenseWrapper>
                                <ResumeCreate />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/wallet',
                        element: <SuspenseWrapper><Wallet /></SuspenseWrapper>,
                    },
                    {
                        path: 'dashboard/account',
                        element: <SuspenseWrapper><AccountSettings /></SuspenseWrapper>,
                    },
                    {
                        path: 'dashboard/employer/company',
                        element: (
                            <SuspenseWrapper>
                                <CompanyProfile />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/employer/ai/analyze',
                        element: (
                            <SuspenseWrapper>
                                <CandidateAnalysis />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/candidate/ai/compatibility',
                        element: (
                            <SuspenseWrapper>
                                <JobCompatibility />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'dashboard/notifications',
                        element: (
                            <SuspenseWrapper>
                                <NotificationCenter />
                            </SuspenseWrapper>
                        ),
                    },
                ],
            },
            // Admin routes (requires admin role)
            {
                element: <AdminRoute />,
                children: [
                    {
                        path: 'admin',
                        element: (
                            <SuspenseWrapper>
                                <AdminDashboard />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'admin/users',
                        element: (
                            <SuspenseWrapper>
                                <AdminUsers />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'admin/financials',
                        element: (
                            <SuspenseWrapper>
                                <AdminFinancials />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'admin/audit-logs',
                        element: (
                            <SuspenseWrapper>
                                <AdminAuditLog />
                            </SuspenseWrapper>
                        ),
                    },
                    {
                        path: 'admin/payments',
                        element: (
                            <SuspenseWrapper>
                                <AdminPaymentSettings />
                            </SuspenseWrapper>
                        ),
                    },
                    { path: 'admin/security', element: <SuspenseWrapper><AdminSecurity /></SuspenseWrapper> },
                    { path: 'admin/reports', element: <SuspenseWrapper><AdminJobReports /></SuspenseWrapper> },
                ],
            },
            {
                path: '*',
                element: (
                    <SuspenseWrapper>
                        <NotFound />
                    </SuspenseWrapper>
                ),
            },
        ],
    },
]);
