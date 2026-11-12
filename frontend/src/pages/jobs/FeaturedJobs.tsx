/**
 * Featured Jobs section - displays up to 10 highlighted jobs.
 * Requirements: 5.6
 */
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
    Box,
    Typography,
    Card,
    CardContent,
    CardActions,
    Button,
    Chip,
    Skeleton,
} from '@mui/material';
import StarIcon from '@mui/icons-material/Star';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import WorkIcon from '@mui/icons-material/Work';
import { getFeaturedJobs } from '../../services/jobService';
import { MODALITY_LABELS, CONTRACT_TYPE_LABELS } from '../../types/job';

export default function FeaturedJobs() {
    const navigate = useNavigate();

    const { data: jobs, isLoading } = useQuery({
        queryKey: ['featured-jobs'],
        queryFn: getFeaturedJobs,
    });

    if (isLoading) {
        return (
            <Box sx={{ mt: 4 }}>
                <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <StarIcon color="warning" /> Vagas em Destaque
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, overflowX: 'auto', pb: 2 }}>
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} variant="rectangular" width={300} height={180} sx={{ borderRadius: 1, flexShrink: 0 }} />
                    ))}
                </Box>
            </Box>
        );
    }

    if (!jobs || jobs.length === 0) {
        return null;
    }

    return (
        <Box sx={{ mt: 4 }}>
            <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <StarIcon color="warning" /> Vagas em Destaque
            </Typography>
            <Box
                sx={{
                    display: 'flex',
                    gap: 2,
                    overflowX: 'auto',
                    pb: 2,
                    '&::-webkit-scrollbar': { height: 6 },
                    '&::-webkit-scrollbar-thumb': { borderRadius: 3, bgcolor: 'grey.300' },
                }}
            >
                {jobs.map((job) => (
                    <Card
                        key={job.id}
                        variant="outlined"
                        sx={{
                            minWidth: 280,
                            maxWidth: 320,
                            flexShrink: 0,
                            borderLeft: '4px solid #f9a825',
                        }}
                    >
                        <CardContent>
                            <Typography variant="subtitle1" component="h3" noWrap sx={{ fontWeight: 'bold' }}>
                                {job.title}
                            </Typography>
                            {job.company_name && (
                                <Typography variant="body2" color="text.secondary" noWrap>
                                    {job.company_name}
                                </Typography>
                            )}
                            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
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
                            </Box>
                        </CardContent>
                        <CardActions>
                            <Button size="small" onClick={() => navigate(`/jobs/${job.id}`)}>
                                Ver detalhes
                            </Button>
                        </CardActions>
                    </Card>
                ))}
            </Box>
        </Box>
    );
}
