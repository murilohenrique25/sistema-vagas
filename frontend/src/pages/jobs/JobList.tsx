/**
 * Public job listing page with filters, search, and pagination.
 * Requirements: 5.1, 5.2, 5.3, 5.6
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
    Box,
    Container,
    Typography,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Button,
    Card,
    CardContent,
    CardActions,
    Chip,
    Pagination,
    Grid,
    InputAdornment,
    Alert,
    Skeleton,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import WorkIcon from '@mui/icons-material/Work';
import StarIcon from '@mui/icons-material/Star';
import { getJobs } from '../../services/jobService';
import type { JobModality, ContractType, JobFilters } from '../../types/job';
import { MODALITY_LABELS, CONTRACT_TYPE_LABELS } from '../../types/job';
import { formatBRL } from '../../utils/currency';

export default function JobList() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();

    const [search, setSearch] = useState(searchParams.get('search') || '');
    const [modality, setModality] = useState<JobModality | ''>(
        (searchParams.get('modality') as JobModality) || ''
    );
    const [contractType, setContractType] = useState<ContractType | ''>(
        (searchParams.get('contract_type') as ContractType) || ''
    );
    const [salaryMin, setSalaryMin] = useState(searchParams.get('salary_min') || '');
    const [salaryMax, setSalaryMax] = useState(searchParams.get('salary_max') || '');
    const [sortBy, setSortBy] = useState<'date' | 'salary' | 'relevance'>(
        (searchParams.get('sort_by') as 'date' | 'salary' | 'relevance') || 'date'
    );
    const [page, setPage] = useState(Number(searchParams.get('page')) || 1);

    const filters: JobFilters = {
        search: search.length >= 2 ? search : undefined,
        modality: modality || undefined,
        contract_type: contractType || undefined,
        salary_min: salaryMin ? Number(salaryMin) : undefined,
        salary_max: salaryMax ? Number(salaryMax) : undefined,
        sort_by: sortBy,
        page,
        page_size: 20,
    };

    const { data, isLoading, isError } = useQuery({
        queryKey: ['jobs', filters],
        queryFn: () => getJobs(filters),
    });

    function handleSearch() {
        setPage(1);
        const params: Record<string, string> = {};
        if (search) params.search = search;
        if (modality) params.modality = modality;
        if (contractType) params.contract_type = contractType;
        if (salaryMin) params.salary_min = salaryMin;
        if (salaryMax) params.salary_max = salaryMax;
        if (sortBy !== 'date') params.sort_by = sortBy;
        setSearchParams(params);
    }

    function handleClearFilters() {
        setSearch('');
        setModality('');
        setContractType('');
        setSalaryMin('');
        setSalaryMax('');
        setSortBy('date');
        setPage(1);
        setSearchParams({});
    }

    function handlePageChange(_: React.ChangeEvent<unknown>, value: number) {
        setPage(value);
        const params = Object.fromEntries(searchParams.entries());
        params.page = String(value);
        setSearchParams(params);
    }

    function formatSalary(min: number | string | null, max: number | string | null): string {
        if (!min && !max) return 'A combinar';
        const fmt = (v: number | string) => formatBRL(v);
        if (min && max) return `${fmt(min)} - ${fmt(max)}`;
        if (min) return `A partir de ${fmt(min)}`;
        return `Até ${fmt(max!)}`;
    }

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Typography variant="h4" component="h1" gutterBottom>
                Vagas Disponíveis
            </Typography>

            {/* Search and Filters */}
            <Box sx={{ mb: 4 }}>
                <Grid container spacing={2} sx={{ alignItems: 'center' }}>
                    <Grid size={{ xs: 12, md: 4 }}>
                        <TextField
                            fullWidth
                            placeholder="Buscar vagas (mín. 2 caracteres)"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                            slotProps={{
                                input: {
                                    startAdornment: (
                                        <InputAdornment position="start">
                                            <SearchIcon />
                                        </InputAdornment>
                                    ),
                                },
                            }}
                            size="small"
                        />
                    </Grid>
                    <Grid size={{ xs: 6, md: 2 }}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Modalidade</InputLabel>
                            <Select
                                value={modality}
                                label="Modalidade"
                                onChange={(e) => setModality(e.target.value as JobModality | '')}
                            >
                                <MenuItem value="">Todas</MenuItem>
                                {Object.entries(MODALITY_LABELS).map(([key, label]) => (
                                    <MenuItem key={key} value={key}>
                                        {label}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid size={{ xs: 6, md: 2 }}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Regime</InputLabel>
                            <Select
                                value={contractType}
                                label="Regime"
                                onChange={(e) =>
                                    setContractType(e.target.value as ContractType | '')
                                }
                            >
                                <MenuItem value="">Todos</MenuItem>
                                {Object.entries(CONTRACT_TYPE_LABELS).map(([key, label]) => (
                                    <MenuItem key={key} value={key}>
                                        {label}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid size={{ xs: 6, md: 2 }}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Ordenar</InputLabel>
                            <Select
                                value={sortBy}
                                label="Ordenar"
                                onChange={(e) =>
                                    setSortBy(e.target.value as 'date' | 'salary' | 'relevance')
                                }
                            >
                                <MenuItem value="date">Data</MenuItem>
                                <MenuItem value="salary">Salário</MenuItem>
                                <MenuItem value="relevance">Relevância</MenuItem>
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid size={{ xs: 6, md: 2 }}>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button variant="contained" onClick={handleSearch} size="small">
                                Buscar
                            </Button>
                            <Button variant="outlined" onClick={handleClearFilters} size="small">
                                Limpar
                            </Button>
                        </Box>
                    </Grid>
                </Grid>

                {/* Salary range filters */}
                <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid size={{ xs: 6, md: 2 }}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Salário mín."
                            type="number"
                            value={salaryMin}
                            onChange={(e) => setSalaryMin(e.target.value)}
                        />
                    </Grid>
                    <Grid size={{ xs: 6, md: 2 }}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Salário máx."
                            type="number"
                            value={salaryMax}
                            onChange={(e) => setSalaryMax(e.target.value)}
                        />
                    </Grid>
                </Grid>
            </Box>

            {/* Results count */}
            {data && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {data.total} vaga{data.total !== 1 ? 's' : ''} encontrada{data.total !== 1 ? 's' : ''}
                </Typography>
            )}

            {/* Loading state */}
            {isLoading && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} variant="rectangular" height={150} sx={{ borderRadius: 1 }} />
                    ))}
                </Box>
            )}

            {/* Error state */}
            {isError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    Erro ao carregar vagas. Tente novamente mais tarde.
                </Alert>
            )}

            {/* No results */}
            {data && (data.items?.length ?? 0) === 0 && (
                <Alert severity="info">
                    Nenhuma vaga encontrada. Tente remover filtros ou alterar os termos de busca.
                </Alert>
            )}

            {/* Job cards */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {(data?.items ?? []).map((job) => (
                    <Card
                        key={job.id}
                        variant="outlined"
                        sx={{
                            borderLeft: job.is_highlighted ? '4px solid #f9a825' : undefined,
                            position: 'relative',
                        }}
                    >
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                {job.is_highlighted && (
                                    <Chip
                                        icon={<StarIcon />}
                                        label="Destaque"
                                        color="warning"
                                        size="small"
                                    />
                                )}
                                <Typography variant="h6" component="h2">
                                    {job.title}
                                </Typography>
                            </Box>
                            {job.company_name && (
                                <Typography variant="body2" color="text.secondary" gutterBottom>
                                    {job.company_name}
                                </Typography>
                            )}
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                                {job.location && (
                                    <Chip
                                        icon={<LocationOnIcon />}
                                        label={job.location}
                                        size="small"
                                        variant="outlined"
                                    />
                                )}
                                <Chip
                                    icon={<WorkIcon />}
                                    label={MODALITY_LABELS[job.modality]}
                                    size="small"
                                    variant="outlined"
                                />
                                <Chip
                                    label={CONTRACT_TYPE_LABELS[job.contract_type]}
                                    size="small"
                                    variant="outlined"
                                />
                                <Chip
                                    label={formatSalary(job.salary_min, job.salary_max)}
                                    size="small"
                                    color="primary"
                                    variant="outlined"
                                />
                            </Box>
                            {job.deadline && (
                                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                                    Prazo: {new Date(job.deadline).toLocaleDateString('pt-BR')}
                                </Typography>
                            )}
                        </CardContent>
                        <CardActions>
                            <Button size="small" onClick={() => navigate(`/jobs/${job.id}`)}>
                                Ver detalhes
                            </Button>
                        </CardActions>
                    </Card>
                ))}
            </Box>

            {/* Pagination */}
            {data && data.total_pages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                    <Pagination
                        count={data.total_pages}
                        page={page}
                        onChange={handlePageChange}
                        color="primary"
                    />
                </Box>
            )}
        </Container>
    );
}
